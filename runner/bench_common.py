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
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


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
