"""Due-gated scratch retention for startup and long-lived housekeeping loops."""

from __future__ import annotations

import json
import logging
import math
import os
import threading
import time
from pathlib import Path

logger = logging.getLogger(__name__)
_LOCK = threading.Lock()
_HOLDER = threading.local()
_INTERVAL = 3600


def read_scratch_policy(home: Path) -> tuple[float, int]:
    import hermes_yaml as yaml
    from hermes_constants import SCRATCH_MAX_IDLE_HOURS, reset_hermes_home_override, set_hermes_home_override
    from hermes_cli.config_effective import load_user_config_effective

    token = set_hermes_home_override(home)
    try:
        config = load_user_config_effective(home / "config.yaml", fail_closed=True)
    except yaml.YAMLError as exc:
        raise ValueError("Could not read scratch policy: invalid config.yaml") from exc
    finally:
        reset_hermes_home_override(token)
    settings = (config or {}).get("scratch", {})
    hours = float(settings.get("max_idle_hours", SCRATCH_MAX_IDLE_HOURS))
    gb = float(settings.get("max_size_gb", 0))
    if not math.isfinite(hours) or hours <= 0 or not math.isfinite(gb) or gb < 0:
        raise ValueError("scratch.max_idle_hours must be positive; max_size_gb must be nonnegative")
    return hours, int(gb * 1_000_000_000)


def _entry_stats(path: Path) -> tuple[int, float]:
    """Apparent bytes and latest write; never follow links outside scratch."""
    size, latest = 0, 0.0
    stack = [path]
    while stack:
        current = stack.pop()
        st = current.lstat()
        size += st.st_size
        # Local Git clones share packs: a live repository freshening a hardlink is not
        # activity in this disposable checkout (same rule as the retention scanner).
        if not (current.is_file() and st.st_nlink > 1):
            latest = max(latest, st.st_mtime)
        if current.is_dir() and not current.is_symlink():
            stack.extend(current.iterdir())
    return size, latest


def _busy_entries(entries: list[Path], *, owned_only: bool = False) -> set[Path]:
    """Capacity eviction must not kill even an unregistered process using a fresh tree."""
    import psutil
    from hermes_constants_scratch import _owned_by_hermes, _registered_live_pids

    busy: set[Path] = set()
    if not entries:
        return busy
    resolved = {p: os.path.realpath(p) for p in entries}
    registered = _registered_live_pids(entries[0].parent.absolute().parent.parent)
    uid = os.getuid() if hasattr(os, "getuid") else None
    for proc in psutil.process_iter():
        try:
            if uid is not None and proc.uids().real != uid:
                continue
            if owned_only and not _owned_by_hermes(proc, registered):
                continue
            paths = []
            for probe in (proc.cwd, proc.exe, lambda: [f.path for f in proc.open_files()]):
                try:
                    value = probe()
                    paths.extend(value if isinstance(value, list) else [value])
                except (psutil.AccessDenied, OSError):
                    # macOS denies descriptor inspection for OS agents such as
                    # UserEventAgent even for the same uid. Their denial must not
                    # disable all cleanup; opaque Hermes-owned workers stay protected.
                    if _owned_by_hermes(proc, registered):
                        return set(entries)
        except psutil.NoSuchProcess:
            continue
        except (psutil.AccessDenied, OSError):
            if _owned_by_hermes(proc, registered):
                return set(entries)
            continue
        for entry, root in resolved.items():
            if any(p == root or p.startswith(root + os.sep) for p in paths if p):
                busy.add(entry)
    return busy


def _size_prune(root: Path, limit: int) -> tuple[int, int]:
    import hermes_constants_scratch as scratch

    skips = {".last_prune", scratch.stuck.STUCK_STATE_NAME, scratch.stuck.STUCK_LOCK_NAME}
    protected = scratch.stuck.load_skips(root)
    entries = [p for p in root.iterdir() if p.name not in skips]
    stats = {}
    for p in entries:
        try:
            stats[p] = _entry_stats(p)
        except OSError:
            logger.warning("Scratch capacity scan could not inspect %s; keeping it", p)
            # Unknown size: do not pretend the budget was met.
            return 0, limit + 1
    total = sum(size for size, _mtime in stats.values())
    removed = 0
    if total <= limit:
        return removed, total
    busy = _busy_entries(entries) | {p for p in entries if p.name in protected}
    for entry in sorted(stats, key=lambda p: (stats[p][1], p.name)):
        if total <= limit:
            break
        if entry in busy or entry in _busy_entries([entry]):
            continue
        # Reuse the existing permission handling, worktree cleanup and last-moment
        # write check, but never reap processes to satisfy a size budget.
        audit = scratch._open_prune_log(root.parent.parent / "logs" / "scratch-prune.log")
        try:
            count = scratch._prune_idle_entries(
                root, 0, frozenset(skips | {p.name for p in entries if p != entry}), audit,
                cutoff=math.nextafter(stats[entry][1], math.inf), reap=False)
        finally:
            if audit is not scratch.logger:
                for handler in audit.handlers:
                    handler.close()
        if count:
            removed += count
            total -= stats[entry][0]
    # Writers may have added files while scanning/deleting; report current usage.
    return removed, sum(_entry_stats(p)[0] for p in root.iterdir() if p.name not in skips)


def maybe_prune_scratch(scratch: Path | None = None) -> dict:
    """Check hourly per home, including on the first live tick; failed runs remain retryable."""
    from hermes_constants import get_scratch_dir
    from hermes_constants_scratch import prune_idle_entries
    from hermes_cli.auth import _file_lock
    from utils import atomic_write_text

    root = scratch if scratch is not None else get_scratch_dir(prune=False)
    home = root.absolute().parent.parent
    status = home / "cache" / "scratch-cleanup.json"
    if not _LOCK.acquire(blocking=False):
        return {"skipped": "busy"}
    try:
        hours, limit = read_scratch_policy(home)
        with _file_lock(home / "cache" / "scratch-cleanup.lock", _HOLDER, 1, "Scratch cleanup busy"):
            try:
                previous = json.loads(status.read_text()) if status.exists() else {}
            except ValueError:
                previous = {}
            now = time.time()
            if (previous.get("max_idle_hours"), previous.get("max_bytes")) == (hours, limit) \
                    and 0 <= now - previous.get("finished_at", 0) < _INTERVAL:
                return {"skipped": "not_due"}
            entries = [p for p in root.iterdir() if p.name != ".last_prune"]
            # Keep existing age-based orphan reaping: only owned workers get an
            # indefinite age exemption. Capacity eviction below protects all live
            # users and never terminates a process to make room.
            busy = _busy_entries(entries, owned_only=True)
            removed = prune_idle_entries(
                root, hours, frozenset({".last_prune"} | {p.name for p in busy}),
                home / "logs" / "scratch-prune.log")
            extra, remaining = _size_prune(root, limit) if limit else (0, None)
            result = {"finished_at": time.time(), "max_idle_hours": hours, "max_bytes": limit,
                      "removed": removed + extra, "remaining_bytes": remaining,
                      "over_budget": bool(limit and remaining > limit), "pid": os.getpid()}
            if result["over_budget"]:
                logger.warning("Scratch remains over its %d-byte budget (%d bytes); active or "
                               "uninspectable entries were kept", limit, remaining)
            atomic_write_text(status, json.dumps(result) + "\n")
            (root / ".last_prune").touch()
            return result
    except (OSError, ValueError, TypeError, AttributeError, TimeoutError) as exc:
        logger.warning("Scratch cleanup deferred: %s", exc)
        return {"skipped": "error"}
    finally:
        _LOCK.release()
