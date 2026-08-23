"""Shared helpers for the suite runners (run_prompt_suite.py,
run_fixture_suite.py) — config-content snapshotting and harness-version
tagging, added after an adversarial review (2026-08-21) found:

  - config_hash alone doesn't make a logged row traceable: every config
    file gets edited after being run, so `config_hash` in an old row no
    longer matches the live file at `config_path` — the leaderboard link
    points at settings that demonstrably did not produce that row.
  - runner code (grading logic, max_turns, timeout handling) has changed
    multiple times without any config change, so pre-fix and post-fix runs
    silently share a (model, backend, quant, config_hash) grouping key and
    get averaged together on the leaderboard.

Both are fixed by recording, per row: the exact config content (snapshotted
by its hash, once, under results/configs/) and the runner's own git sha at
run time (so a runner-code change naturally starts a new leaderboard group,
the same way a config change already did).
"""
import hashlib
import subprocess
import threading
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# Added 2026-08-22 (methodology review, finding F5): PASS carried no
# latency signal at all — a task that took 3135s scored identically to
# one that took 4.8s, and 5 hermes_ops rows already exceeded the suite's
# own declared timeout_seconds (1000s) while being logged as ordinary
# passes. Deliberately DISTINCT from timeout_seconds/--timeout, which
# exist to give a slow-but-alive model a fair chance to finish generating
# without being unfairly cut off mid-response (that value was raised
# specifically to stop penalizing large/thinking models — see
# tasks/hermes_ops.yaml's own history). This is the opposite question:
# even a fully correct, uninterrupted answer that takes many minutes
# isn't something a real interactive agentic session would tolerate. 300s
# (5 minutes) is a judgment call, not derived from a spec — documented
# here, in one place, rather than duplicated as a magic number in each
# runner.
INTERACTIVE_BUDGET_SECONDS = 300

# Lowered to 4 tok/s 2026-08-23, by explicit user decision (Tijs): the
# original 10 tok/s bar (set 2026-08-22) was gating out too many otherwise-
# interesting candidates for comparison purposes — deliberately loosened
# to keep more variety in the results rather than narrowing the field this
# early. This is NOT a claim that 4 tok/s is comfortable for real
# interactive use (it likely still isn't) — it's a "still worth collecting
# coding-suite data on" bar, one step above "clearly hopeless." The
# original 10 tok/s reasoning (a practical floor for a model to be worth
# considering as Hermes's backing LLM at all) still applies at the
# leaderboard-interpretation level; this constant just controls when
# run_bench.py stops collecting more data, not what counts as "good enough
# to use." Also replaces an earlier 1.0 tok/s cutoff added right after the
# Qwen3.8-27B MLX pilot (that config's own hermes_ops rows sat at
# 0.15-0.83 tok/s — comfortably below every version of this number, so
# that finding is unaffected). run_bench.py checks this against the MEAN
# tokens_per_second across a config's own full hermes_ops suite run (every
# task, not one probe task) — a single-task probe was tried first but
# rejected: hermes_ops-selection specifically (the smallest-completion
# task) is the most prefill-dominated of the 8 tasks and reads
# systematically low even for genuinely fast models (LiquidAI/LFM2.5-8B-
# A1B-GGUF:Q8_0 reads 9.36 tok/s on that one task alone despite averaging
# 48.2 tok/s across its full hermes_ops run) — gating on it directly would
# have wrongly failed that model. The full-suite mean is also exactly what
# results/LEADERBOARD.md's own "avg tok/s" column already reports, so this
# cutoff means the same thing everywhere in this repo.
MIN_HERMES_OPS_TOKENS_PER_SECOND = 4.0


def _find_listening_pid(port):
    """PID of whatever process is actually listening on *port*, or None.
    Deliberately identity-agnostic about how many shell/uv wrapper layers
    launched it (server_command()'s launch text can be `uv run ... python
    -m vllm_mlx.server` under a shell=True Popen) — the one thing every
    launch style has in common is that exactly one process ends up bound
    to the port, so ask the OS which one that is rather than trying to
    track through the process tree."""
    try:
        out = subprocess.run(
            ["lsof", "-i", f":{port}", "-sTCP:LISTEN", "-t"],
            capture_output=True, text=True, timeout=5,
        ).stdout.strip()
        pids = [p for p in out.splitlines() if p]
        return int(pids[0]) if pids else None
    except (subprocess.SubprocessError, ValueError, OSError):
        return None


def _rss_gb(pid):
    """Current RSS of *pid* in GB, or None if the process/measurement is
    unavailable (e.g. it just exited)."""
    try:
        out = subprocess.run(
            ["ps", "-o", "rss=", "-p", str(pid)],
            capture_output=True, text=True, timeout=5,
        ).stdout.strip()
        return int(out) / (1024 * 1024) if out else None  # ps rss is in KB
    except (subprocess.SubprocessError, ValueError, OSError):
        return None


class PeakRSSSampler:
    """Samples the RSS of whatever process is listening on *port* every
    *interval* seconds in a background thread, tracking the maximum seen.

    Added 2026-08-22 (methodology review, finding F7): the benchmark's
    binding hardware constraint (32GB unified memory) was never actually
    measured anywhere — footprints were argued only in config prose, so
    there was no way to tell "this model genuinely runs at 0.3 tok/s" from
    "this config was swapping." A single snapshot at the end of a task
    wouldn't catch a transient peak mid-generation, so this samples
    continuously for the duration of a task rather than once.

    Usage:
        sampler = PeakRSSSampler(raw_port).start()
        ... run the task ...
        peak_gb = sampler.stop()

    *port* may be None (e.g. a hosted/API config with no local server) —
    start()/stop() degrade to a no-op returning None in that case, rather
    than requiring every call site to check first.
    """

    def __init__(self, port, interval=2.0):
        self.port = port
        self.interval = interval
        self._peak_gb = None
        self._stop_event = threading.Event()
        self._thread = None

    def _loop(self):
        pid = None
        while not self._stop_event.is_set():
            if pid is None:
                pid = _find_listening_pid(self.port)
            if pid is not None:
                rss = _rss_gb(pid)
                if rss is not None:
                    self._peak_gb = max(self._peak_gb or 0.0, rss)
                else:
                    pid = None  # process exited/restarted — re-resolve next tick
            self._stop_event.wait(self.interval)

    def start(self):
        if self.port is not None:
            self._thread = threading.Thread(target=self._loop, daemon=True)
            self._thread.start()
        return self

    def stop(self):
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=self.interval + 2)
        return self._peak_gb


def git_sha():
    """Short git sha of the runner's current state, +dirty if uncommitted
    changes exist. A run graded by uncommitted code is real but should
    never be silently indistinguishable from one graded by a committed,
    reviewable version — the +dirty suffix makes that visible in the log
    and leaderboard instead of just in the committer's memory."""
    try:
        sha = subprocess.run(
            ["git", "rev-parse", "--short=12", "HEAD"],
            cwd=REPO, capture_output=True, text=True, check=True,
        ).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"
    dirty = subprocess.run(
        # fixtures/ added after a second independent adversarial review
        # (finding M-10): the fixture IS the graded artifact — an
        # uncommitted edit to e.g. fixtures/kiem_mini/rust/src/lib.rs
        # changes what the task actually is, and was invisible in
        # runner_git_sha before this fix.
        #
        # configs/ added after a third independent adversarial review
        # (finding CR3-11): snapshot_config() only hashes the single .yaml
        # passed via --config, but configs/<model>/ can contain SIBLING
        # files that materially affect what's actually served and aren't
        # captured by that hash — most consequential,
        # configs/Qwen3.8-27B/chat_template.jinja, which is copied
        # straight into the live HF cache on every MLX launch (see that
        # config's own settings block) and passed directly via
        # --chat-template-file for its GGUF siblings. Confirmed live: an
        # uncommitted edit to that file was completely invisible in
        # runner_git_sha before this fix.
        ["git", "status", "--porcelain", "--", "runner/", "tasks/", "checks/", "fixtures/", "configs/"],
        cwd=REPO, capture_output=True, text=True,
    ).stdout.strip()
    return f"{sha}+dirty" if dirty else sha


def snapshot_config(config_path):
    """Hash *config_path*'s exact current bytes, save a verbatim copy under
    results/configs/<hash>.yaml (first time only — the hash IS the content,
    so a second write would be a no-op), and return (hash, repo-relative
    path string). Every future reader of a log row can recover exactly what
    was run, forever, even after the live config file is edited again."""
    path = Path(config_path).resolve()
    rel = str(path.relative_to(REPO))
    content = path.read_bytes()
    config_hash = hashlib.sha256(content).hexdigest()[:12]
    snap_dir = REPO / "results" / "configs"
    snap_dir.mkdir(parents=True, exist_ok=True)
    snap_path = snap_dir / f"{config_hash}.yaml"
    if not snap_path.exists():
        snap_path.write_bytes(content)
    return config_hash, rel
