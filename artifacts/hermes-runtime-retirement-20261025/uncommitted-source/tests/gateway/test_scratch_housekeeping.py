"""Long-lived gateways enforce scratch policy without restarting or losing live work."""

import json
import os
import time
import subprocess
import sys
from types import SimpleNamespace

import pytest

from gateway import run
import hermes_constants_scratch_policy as policy


def _file(root, name, data=b"cached", hours=60):
    root.mkdir(parents=True, exist_ok=True)
    path = root / name
    path.write_bytes(data)
    stamp = time.time() - hours * 3600
    os.utime(path, (stamp, stamp))
    return path


@pytest.fixture
def home(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    (home / "config.yaml").write_text("scratch:\n  max_idle_hours: 48\n  max_size_gb: 0\n")
    monkeypatch.setenv("HERMES_HOME", str(home))
    monkeypatch.setattr(policy, "_busy_entries", lambda _entries, **_kwargs: set())
    return home


def test_running_gateway_cleans_again_after_the_next_interval(home, monkeypatch):
    import hermes_constants

    monkeypatch.setattr(hermes_constants, "_scratch_pruned_once", True)
    root = home / "cache" / "scratch"
    old = _file(root, "old")
    fresh = _file(root, "fresh", hours=30)
    second = root / "second"
    stop = SimpleNamespace(ticks=0)

    def wait(timeout=None):
        stop.ticks += 1
        if stop.ticks == 1:
            assert not old.exists() and fresh.exists()
            _file(root, second.name)
            marker = home / "cache" / "scratch-cleanup.json"
            data = json.loads(marker.read_text())
            data["finished_at"] -= 3601
            marker.write_text(json.dumps(data))
        return stop.ticks >= 2

    stop.wait = wait
    stop.is_set = lambda: stop.ticks >= 2
    # Keep the actual gateway chore dispatch/profile wrapper and cleanup I/O;
    # unrelated network, session and provider chores are outside this regression.
    monkeypatch.setattr(run, "_housekeeping_chore",
                        lambda label, fn: fn() if label == "Scratch cleanup tick" else None)
    run._start_gateway_housekeeping(stop, interval=0)
    assert not second.exists() and fresh.exists()
    assert json.loads((home / "cache" / "scratch-cleanup.json").read_text())["max_idle_hours"] == 48


def test_capacity_evicts_oldest_inactive_entry_before_expiry(home):
    (home / "config.yaml").write_text("scratch:\n  max_idle_hours: 48\n  max_size_gb: 0.000000010\n")
    root = home / "cache" / "scratch"
    old = _file(root, "old", b"123456", hours=2)
    fresh = _file(root, "fresh", b"abcdef", hours=1)
    result = policy.maybe_prune_scratch(root)
    assert not old.exists() and fresh.read_bytes() == b"abcdef"
    assert result["remaining_bytes"] == 6 and result["over_budget"] is False
    assert policy.maybe_prune_scratch(root) == {"skipped": "not_due"}


def test_live_work_survives_age_and_capacity_pressure(home, monkeypatch, caplog):
    (home / "config.yaml").write_text("scratch:\n  max_idle_hours: 48\n  max_size_gb: 0.000000010\n")
    root = home / "cache" / "scratch"
    live = _file(root, "live", b"x" * 20)
    monkeypatch.setattr(policy, "_busy_entries", lambda entries, **_kwargs: {live} & set(entries))
    result = policy.maybe_prune_scratch(root)
    assert live.read_bytes() == b"x" * 20
    assert result["over_budget"] is True and result["remaining_bytes"] == 20
    assert "active or uninspectable entries were kept" in caplog.text


def test_invalid_policy_does_not_delete_and_can_be_retried(home):
    root = home / "cache" / "scratch"
    old = _file(root, "old")
    (home / "config.yaml").write_text("scratch:\n  max_idle_hours: -1\n")
    assert policy.maybe_prune_scratch(root) == {"skipped": "error"}
    assert old.exists()
    (home / "config.yaml").write_text("scratch:\n  max_idle_hours: 48\n")
    assert policy.maybe_prune_scratch(root)["removed"] == 1


def test_separate_homes_keep_their_own_retention_and_cadence(home, tmp_path):
    other = tmp_path / "other"
    other.mkdir()
    (other / "config.yaml").write_text("scratch:\n  max_idle_hours: 72\n")
    a = _file(home / "cache" / "scratch", "a")
    b = _file(other / "cache" / "scratch", "b")
    policy.maybe_prune_scratch(a.parent)
    policy.maybe_prune_scratch(b.parent)
    assert not a.exists() and b.exists()


def test_real_live_process_working_directory_is_protected(tmp_path, monkeypatch):
    import psutil
    entry = tmp_path / "active"
    entry.mkdir()
    proc = subprocess.Popen(
        [sys.executable, "-c", "import sys; print('ready', flush=True); sys.stdin.read()"],
        cwd=entry, stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
    try:
        assert proc.stdout.readline().strip() == "ready"
        monkeypatch.setattr(psutil, "process_iter", lambda: [psutil.Process(proc.pid)])
        assert entry in policy._busy_entries([entry])
    finally:
        proc.communicate(input="", timeout=10)


def test_capacity_rescues_an_entry_written_after_selection(home, monkeypatch):
    import hermes_constants_scratch as scratch

    (home / "config.yaml").write_text("scratch:\n  max_idle_hours: 48\n  max_size_gb: 0.000000001\n")
    entry = _file(home / "cache" / "scratch", "changing", hours=1)
    original = scratch._tree_bytes

    def write_before_recheck(path):
        if path == entry:
            path.write_bytes(b"new work")
        return original(path)

    monkeypatch.setattr(scratch, "_tree_bytes", write_before_recheck)
    assert policy.maybe_prune_scratch(entry.parent)["over_budget"] is True
    assert entry.read_bytes() == b"new work"


def test_capacity_never_follows_a_symlink_outside_scratch(home):
    (home / "config.yaml").write_text("scratch:\n  max_idle_hours: 48\n  max_size_gb: 0.000000001\n")
    outside = _file(home, "project-source", b"keep this")
    root = home / "cache" / "scratch"
    root.mkdir(parents=True)
    link = root / "link"
    link.symlink_to(outside)
    result = policy.maybe_prune_scratch(root)
    assert result["over_budget"] is False and not link.is_symlink()
    assert outside.read_bytes() == b"keep this"


def test_opaque_os_process_does_not_disable_cleanup_but_owned_worker_does(tmp_path, monkeypatch):
    import psutil
    import hermes_constants_scratch as scratch

    entry = tmp_path / "cache" / "scratch" / "entry"
    entry.mkdir(parents=True)
    proc = SimpleNamespace(pid=123, uids=lambda: SimpleNamespace(real=os.getuid()),
                           cwd=lambda: str(tmp_path), exe=lambda: "/os/agent", parents=list)

    def denied():
        raise psutil.AccessDenied(proc.pid)

    proc.open_files = denied
    monkeypatch.setattr(psutil, "process_iter", lambda: [proc])
    monkeypatch.setattr(scratch, "_registered_live_pids", lambda _home: set())
    assert policy._busy_entries([entry]) == set()
    monkeypatch.setattr(scratch, "_registered_live_pids", lambda _home: {proc.pid})
    assert policy._busy_entries([entry]) == {entry}
