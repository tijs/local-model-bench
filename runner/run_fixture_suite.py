#!/usr/bin/env python3
"""
Drives every fixture-based task in tasks/<suite>.yaml against one model, via
the isolated "bench" hermes profile, in a fresh copy of the suite's fixture
per task (copy -> git init -> baseline commit -> hermes works here ->
grade -> discard). Appends one row per task to results/log.jsonl.

Requires PyYAML. Run through the repository's locked uv environment:
  uv run --locked python runner/run_fixture_suite.py ...

Usage:
  run_fixture_suite.py --suite kiem_mini \
      --hermes-provider custom:local-mlx --hermes-model LiquidAI/LFM2.5-2.6B-MLX-bf16 \
      --inference-engine vllm-mlx [--quant Q4_K_M] [--only-task kiem_mini-feature]
"""
import argparse
import contextlib
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

import yaml

from bench_common import INTERACTIVE_BUDGET_SECONDS, REPO, PeakRSSSampler, git_sha, snapshot_config

HERMES_BIN = Path(os.environ.get(
    "BENCH_HERMES_BIN", str(Path.home() / ".hermes/hermes-agent/venv/bin/hermes")
))  # override via env var instead of editing this file (adversarial review finding M8)


# macOS Seatbelt sandbox for the coding agent (improvement plan, M3).
#
# `hermes chat --yolo` auto-approves every tool call, so a model that
# resolves a path wrongly (or maliciously) can write anywhere the user
# can: sibling projects under the repo's parent directory, the benchmark
# checkout itself, Hermes's own state. preserve_tree/preserve_repository
# already REVERT such writes and flag the task as a harness error, but
# they are detect-and-repair, not prevention — and they only cover the
# trees they scan.
#
# Deliberately a DENY-list, not an allow-list. An allow-list profile has
# to enumerate everything cargo/npm/swiftpm/xcodebuild legitimately touch
# (toolchain paths, ~/.cargo, ~/.npm, ~/Library/Caches, Xcode's DEVELOPER_DIR,
# temp dirs, ...); getting one entry wrong makes every coding task fail
# for a reason that has nothing to do with the model, and silently
# corrupts the dataset. A deny-list closes exactly the holes M3 names
# while leaving normal builds untouched.
#
# ~/.hermes is deliberately NOT denied: the sandbox applies to the hermes
# process itself, which legitimately writes its own session store there —
# the same store extract_hermes_session_stats() reads telemetry from.
# That write is the harness's, not the agent's, and the two are
# indistinguishable at this layer.
#
# Set BENCH_SANDBOX=0 to disable (e.g. to reproduce a pre-sandbox result).
# Falls back to running unsandboxed, with a warning, if seatbelt is
# unavailable or its self-test fails, rather than failing the run.
SANDBOX_ENABLED = os.environ.get("BENCH_SANDBOX", "1") != "0"
SANDBOX_EXEC = "/usr/bin/sandbox-exec"


def sandbox_profile(run_dir):
    """Seatbelt (SBPL) profile denying writes outside *run_dir*.

    Rule order matters: in SBPL the LAST matching rule wins, so the
    allow for the disposable run root has to come after every deny that
    contains it.
    """
    run_dir = Path(run_dir).resolve()
    repo = Path(REPO).resolve()
    siblings = repo.parent
    return "\n".join([
        "(version 1)",
        "(allow default)",
        # Sibling checkouts next to this repo — the blast radius M3 names.
        f'(deny file-write* (subpath "{siblings}"))',
        # The benchmark checkout itself: fixtures, checks, tasks, runner.
        f'(deny file-write* (subpath "{repo}"))',
        # Run output the harness itself produces under the repo.
        f'(allow file-write* (subpath "{repo / "results"}"))',
        f'(allow file-write* (subpath "{repo / "runner" / "runs"}"))',
        # The disposable run root: the one place the agent SHOULD write.
        f'(allow file-write* (subpath "{run_dir}"))',
        "",
    ])


def _sandbox_available(profile):
    """True if seatbelt is usable here — verified by actually running a
    trivial command under *profile*, not just by checking the binary
    exists. A profile that fails to compile would otherwise turn every
    coding task into a harness error."""
    if not (SANDBOX_ENABLED and sys.platform == "darwin" and os.path.exists(SANDBOX_EXEC)):
        return False
    try:
        probe = subprocess.run(
            [SANDBOX_EXEC, "-p", profile, "/usr/bin/true"],
            capture_output=True, timeout=20,
        )
    except (subprocess.SubprocessError, OSError):
        return False
    return probe.returncode == 0


def sandbox_wrapped_command(cmd, run_dir):
    """Wrap *cmd* in sandbox-exec when possible; return it unchanged (with
    a warning) otherwise. Returns (argv, sandboxed)."""
    if not SANDBOX_ENABLED:
        return cmd, False
    profile = sandbox_profile(run_dir)
    if not _sandbox_available(profile):
        print(
            "WARNING: seatbelt sandbox unavailable — running the coding agent "
            "unsandboxed. preserve_tree/preserve_repository still revert and flag "
            "any escape, but prevention is off (see M3 in the improvement plan).",
            file=sys.stderr,
        )
        return cmd, False
    return [SANDBOX_EXEC, "-p", profile, *cmd], True


def run_hermes(prompt, cwd, provider, model, max_turns, timeout):
    cmd = [
        str(HERMES_BIN), "chat", "--profile", "bench", "-q", prompt,
        "--provider", provider, "-m", model, "-Q", "--yolo",
        "--max-turns", str(max_turns),
    ]
    # `--yolo` auto-approves every tool call, so confine the agent's
    # writes to the disposable run root where the platform allows it
    # (improvement plan, M3). The restoration guards stay in place as
    # defense in depth, exactly as the plan asks.
    cmd, _sandboxed = sandbox_wrapped_command(cmd, cwd)
    start = time.time()
    # start_new_session=True + killpg on timeout (adversarial review finding
    # M9): plain subprocess.run(timeout=...) only kills the DIRECT hermes
    # child on TimeoutExpired — any grandchildren it spawned while running
    # (cargo/npm/swift test, a subagent process) are left running, and the
    # in-flight backend request keeps generating, which is exactly the
    # killed-task retry hazard documented elsewhere in this file. Killing
    # the whole process group closes that at the source instead of relying
    # on the caller to notice and wait it out.
    proc = subprocess.Popen(
        cmd, cwd=str(cwd), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, start_new_session=True,
    )
    try:
        stdout, stderr = proc.communicate(timeout=timeout)
        return stdout, stderr, proc.returncode, time.time() - start, False
    except subprocess.TimeoutExpired:
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except ProcessLookupError:
            pass  # already exited between the timeout firing and this kill
        proc.communicate()  # reap the process, avoid a zombie
        # A distinct boolean, not `rc == -1` (adversarial review finding
        # L-2): a real hermes process killed by e.g. SIGHUP also exits with
        # returncode -1 (negative = "terminated by signal N", and SIGHUP is
        # signal 1) — that would have been misreported as "TIMEOUT after
        # {timeout}s" by the caller even when the actual timeout was never
        # reached.
        return "", "TIMEOUT", -1, time.time() - start, True


_SESSION_ID_RE = re.compile(r"^session_id:\s*(\S+)", re.MULTILINE)
_COMPILE_ERROR_RE = re.compile(
    r"error\[E[0-9]+\]|error TS[0-9]+|SyntaxError|error: could not compile"
)

_EMPTY_SESSION_STATS = {
    "hermes_turns": None, "hermes_tool_calls": None,
    "hermes_input_tokens": None, "hermes_output_tokens": None,
    "hermes_reasoning_tokens": None, "hermes_tool_errors": None,
}


def extract_hermes_session_stats(stdout, stderr=""):
    """Pull turn/tool-call/token counts out of hermes's own SQLite session
    store for the just-finished run (methodology review, finding F6): the
    coding suite previously logged only pass/exit-code/wall/diff-stat — no
    performance data from the actual target workload at all, unlike the
    two synthetic prompt suites. `hermes sessions export` (confirmed live
    via `hermes sessions --help`) returns exactly this as structured JSON:
    api_call_count (turns), tool_call_count, input/output/reasoning
    tokens, and the full per-message transcript.

    Searches STDERR first, then stdout (improvement plan, H2): this only
    ever looked at stdout, while current Hermes prints its `session_id:`
    banner on stderr — so every coding row silently logged an empty
    telemetry block (hermes_turns, tool errors and friends all null) even
    when the task itself graded fine. Both streams are checked rather
    than just swapping them, so the extraction keeps working across
    Hermes versions that differ on which stream carries the banner.

    Returns a dict (all values None if the session_id can't be found in
    either stream, or the export itself fails/times out — never raises,
    since this is instrumentation, not something that should turn a
    successfully-graded task into a harness error).
    """
    match = _SESSION_ID_RE.search(stderr or "") or _SESSION_ID_RE.search(stdout or "")
    if not match:
        return dict(_EMPTY_SESSION_STATS)
    session_id = match.group(1)
    try:
        proc = subprocess.run(
            [str(HERMES_BIN), "--profile", "bench", "sessions", "export",
             "--session-id", session_id, "--format", "jsonl", "-"],
            capture_output=True, text=True, timeout=30,
        )
        if proc.returncode != 0 or not proc.stdout.strip():
            return dict(_EMPTY_SESSION_STATS)
        session = json.loads(proc.stdout.strip().splitlines()[0])
    except (subprocess.SubprocessError, json.JSONDecodeError, OSError, IndexError):
        return dict(_EMPTY_SESSION_STATS)

    # Best-effort heuristic, not a fully generic classifier (documented
    # limitation, not silently assumed complete): each tool's own result
    # JSON shape differs (patch uses "success", terminal uses "exit_code"/
    # "error"), so this looks for the couple of conventions actually
    # observed across this repo's own tool set rather than parsing every
    # tool's schema individually. Confirmed live against a real session
    # that a `terminal` call's own exit_code can read 0 even when its
    # output clearly shows a build failure (e.g. piped through something
    # that swallows the real exit status) — exit_code/error/success fields
    # alone are NOT sufficient, so this also scans output text for the
    # same compiler-error markers grade_mutation.sh's own heuristic
    # already uses, as a fallback when the structured fields say "ok."
    tool_errors = 0
    for msg in session.get("messages") or []:
        if msg.get("role") != "tool":
            continue
        content = msg.get("content")
        if not isinstance(content, str):
            continue
        try:
            parsed = json.loads(content)
        except (json.JSONDecodeError, TypeError):
            continue
        if not isinstance(parsed, dict):
            continue
        if parsed.get("success") is False:
            tool_errors += 1
        elif parsed.get("error") not in (None, False):
            tool_errors += 1
        elif isinstance(parsed.get("exit_code"), int) and parsed["exit_code"] != 0:
            tool_errors += 1
        elif isinstance(parsed.get("output"), str) and _COMPILE_ERROR_RE.search(parsed["output"]):
            tool_errors += 1

    return {
        "hermes_turns": session.get("api_call_count"),
        "hermes_tool_calls": session.get("tool_call_count"),
        "hermes_input_tokens": session.get("input_tokens"),
        "hermes_output_tokens": session.get("output_tokens"),
        "hermes_reasoning_tokens": session.get("reasoning_tokens"),
        "hermes_tool_errors": tool_errors,
    }


def isolated_agent_prompt(prompt, run_dir):
    """Anchor agent file tools to the disposable copy, not the source fixture.

    Hermes subprocess cwd is correct, but profile tools/plugins can retain a
    repository workspace root.  An absolute, repeated boundary is therefore
    required in the user prompt as well as in ``Popen(cwd=...)``.
    """
    root = Path(run_dir).resolve()
    return (
        "[BENCHMARK WORKSPACE ISOLATION]\n"
        f"Work ONLY inside this disposable run root: {root}\n"
        f"Resolve every relative project path beneath {root}.\n"
        "Do not edit the source fixture, benchmark repository, or any sibling "
        "checkout. Use absolute paths under the disposable run root whenever a "
        "file tool could otherwise be ambiguous.\n"
        "[END BENCHMARK WORKSPACE ISOLATION]\n\n"
        f"{prompt}"
    )


@contextlib.contextmanager
def preserve_tree(root, state):
    """Restore a source fixture byte-for-byte if a child agent escapes cwd.

    This is a safety net, not the normal execution path.  ``state['changed']``
    lets the caller classify the run as a harness error instead of crediting a
    model that edited the grading source outside its disposable copy.
    """
    root = Path(root)
    backup_parent = Path(tempfile.mkdtemp(prefix="bench-fixture-guard-"))
    backup = backup_parent / "tree"
    shutil.copytree(root, backup, symlinks=True)
    state["changed"] = False
    try:
        yield
    finally:
        def manifest(path):
            rows = []
            for item in sorted(path.rglob("*")):
                rel = str(item.relative_to(path))
                if item.is_symlink():
                    rows.append((rel, "link", os.readlink(item)))
                elif item.is_file():
                    rows.append((rel, "file", item.read_bytes()))
                elif item.is_dir():
                    rows.append((rel, "dir", b""))
            return rows

        state["changed"] = manifest(root) != manifest(backup)
        if state["changed"]:
            shutil.rmtree(root)
            shutil.copytree(backup, root, symlinks=True)
        shutil.rmtree(backup_parent, ignore_errors=True)


# Benchmark-owned subtrees: everything whose bytes define what a task IS
# and how it is graded. These are the trees an escaping agent must never
# be able to alter, and the only ones this guard reads byte-for-byte.
_PROTECTED_SUBTREES = ("runner", "tasks", "checks", "fixtures", "configs", "docs")

# Never descended into, even at the repo root: `.git` is git's own state
# (and a file, not a directory, inside a worktree), and `results/` is
# intentional run OUTPUT that a task is expected to add to.
_NEVER_SCANNED = {".git", "results"}

# Fallback prune list used only when `git` itself is unavailable, so the
# guard degrades to "slower and slightly broader" rather than to "reads a
# 1.2GB virtualenv again".
_FALLBACK_IGNORED_DIR_NAMES = {
    ".venv", "node_modules", "target", ".build", ".swiftpm", ".deno",
    "__pycache__", "runs", ".dspark-head", ".dflash2-fork", ".omlx-runtime",
}


def _git_ignored_entries(root):
    """Repo-relative paths git considers ignored, or None if git can't
    answer. `--directory` collapses a fully-ignored directory to a single
    entry, so this stays cheap even when the ignored tree is enormous."""
    try:
        out = subprocess.run(
            ["git", "ls-files", "--others", "--ignored", "--exclude-standard", "--directory"],
            cwd=str(root), capture_output=True, text=True, timeout=60, check=True,
        ).stdout
    except (subprocess.SubprocessError, OSError):
        return None
    return {line.rstrip("/") for line in out.splitlines() if line.strip()}


def _repository_entries(root):
    """Return protected repository entries, pruning intentional run outputs.

    SCOPE (narrowed 2026-08-25, improvement plan M2): only the
    benchmark-owned subtrees above, plus every repo-root FILE, plus the
    NAMES of every repo-root directory (so a brand-new top-level directory
    an agent creates is still detected and removed, without recursing into
    unrelated ones). Anything git reports as ignored is skipped outright.

    Measured on this repo before the change: 31,129 files and 1.2GB read
    in 5.7s — of which 30,957 files were `.venv/` — and that happened
    TWICE per coding task (baseline before, comparison after), on every
    single task, forever. `.venv` cannot be part of what a fixture task
    changes, and reading it proved nothing.

    The narrowing preserves the previous ad-hoc prunes for the same
    reasons they were added: runner/.dspark-head and runner/.dflash2-fork
    (found live 2026-08-23) are gitignored from-source llama.cpp build
    checkouts — tens of thousands of unrelated files including large
    binary pack files — whose scanning root-caused a recurring
    `HARNESS ERROR: PermissionError` that had wrongly looked like a model-
    or task-specific flake, hit twice on two completely different models
    before being traced back to this scan rather than to anything about
    the model being tested. They are now covered by the general
    git-ignored rule instead of by name.

    NOTE (unchanged, and still important): preserve_repository(REPO, ...)
    below guards these trees — including this file — during every task's
    execution window and reverts anything that changed, including an edit
    made by the operator mid-task, not just a model's own tool use. Never
    edit this file (or anything else under a protected subtree) while a
    coding-suite task is in flight.
    """
    root = Path(root)
    ignored = _git_ignored_entries(root)
    entries = {".": ("dir", None)}

    def _is_ignored(rel):
        if ignored is not None:
            return rel in ignored
        return Path(rel).name in _FALLBACK_IGNORED_DIR_NAMES

    def _record(path, rel):
        if path.is_symlink():
            entries[rel] = ("link", os.readlink(path))
        elif path.is_file():
            entries[rel] = ("file", path.read_bytes())

    # Repo root: every file's bytes, and every directory's NAME (so a new
    # top-level directory is an added entry the restore logic removes),
    # but no recursion outside the protected subtrees.
    for child in sorted(root.iterdir()):
        rel = child.name
        if rel in _NEVER_SCANNED or _is_ignored(rel):
            continue
        if child.is_dir() and not child.is_symlink():
            entries[rel] = ("dir", None)
        else:
            _record(child, rel)

    for subtree in _PROTECTED_SUBTREES:
        base = root / subtree
        if not base.is_dir():
            continue
        for current, dirs, files in os.walk(base):
            current_path = Path(current)
            rel_dir = str(current_path.relative_to(root))
            dirs[:] = sorted(
                d for d in dirs
                if d not in _NEVER_SCANNED
                and not _is_ignored(str((current_path / d).relative_to(root)))
            )
            entries[rel_dir] = ("dir", None)
            for name in sorted(files):
                path = current_path / name
                rel = str(path.relative_to(root))
                if _is_ignored(rel):
                    continue
                _record(path, rel)
    return entries


@contextlib.contextmanager
def preserve_repository(root, state):
    """Protect the real benchmark checkout while allowing run/results output."""
    root = Path(root)
    baseline = _repository_entries(root)
    state["changed"] = False
    try:
        yield
    finally:
        current = _repository_entries(root)
        state["changed"] = current != baseline
        if state["changed"]:
            # Remove paths created by the child, deepest first. Intentional
            # results/ and runner/runs/ output is absent from both manifests.
            for rel in sorted(set(current) - set(baseline), key=lambda x: x.count("/"), reverse=True):
                if rel == ".":
                    continue
                path = root / rel
                if path.is_symlink() or path.is_file():
                    path.unlink(missing_ok=True)
                elif path.is_dir():
                    shutil.rmtree(path)

            # Restore every pre-existing file/link byte-for-byte. Recreating all
            # files is simpler and safer than trying to classify each mutation.
            for rel, (kind, payload) in sorted(baseline.items(), key=lambda item: item[0].count("/")):
                if rel == ".":
                    continue
                path = root / rel
                if kind == "dir":
                    path.mkdir(parents=True, exist_ok=True)
                elif kind == "link":
                    path.parent.mkdir(parents=True, exist_ok=True)
                    if path.exists() or path.is_symlink():
                        path.unlink()
                    path.symlink_to(payload)
                else:
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(payload)


# Build-cache directories that must NEVER be copied into a run — discovered
# live 2026-08-20: a stale fixtures/kiem_mini/rust/target/ left over from
# fixture development got copied into every single run by shutil.copytree
# (which doesn't respect .gitignore), and cargo's incremental-build cache
# got confused by the copied stale artifacts, producing a false
# "unresolved import" compile error even when the agent's source edit was
# completely correct — reproduced live on a model that had actually
# implemented the task correctly. Every recorded kiem_mini-feature FAIL
# this session needs re-verification against this fix.
_STALE_BUILD_CACHE_DIRS = {
    "target",       # cargo (Rust) — the one that actually bit us live
    ".build",       # Swift Package Manager — found in the same audit,
                    # same risk, never yet triggered only because no
                    # swift-language task had been run against a model yet
    ".dart_tool", "__pycache__",  # defensive, not yet confirmed present
    "node_modules",  # npm/vitest (hearth_mini) — found 2026-08-21
                     # (adversarial review finding H1): fixtures/hearth_mini/
                     # node_modules/ is gitignored but was present on this
                     # machine from ambient local dev, so every run silently
                     # depended on it — a fresh clone has no node_modules at
                     # all and `npm test` would fail for every model, for a
                     # reason that has nothing to do with the model. `npm
                     # ci` below makes each run self-sufficient instead.
}


def reset_fixture(suite, run_dir):
    src = REPO / "fixtures" / suite
    shutil.copytree(
        src, run_dir,
        ignore=shutil.ignore_patterns(*_STALE_BUILD_CACHE_DIRS),
    )
    # node_modules is never in the copy (excluded above) or the baseline
    # commit (git-ignored before the first `git add`) — installed fresh
    # from the tracked package-lock.json instead, so every run is
    # self-sufficient rather than depending on ambient host state.
    #
    # Every _STALE_BUILD_CACHE_DIRS entry gitignored here, not just
    # node_modules (3rd adversarial review, finding CR3-9): these dirs are
    # excluded from the INITIAL copy so the run starts fresh, but nothing
    # stopped the AGENT'S OWN `cargo test`/`swift test` invocation from
    # creating a brand-new rust/target/ (or .build/) mid-run — since that
    # wasn't gitignored, restore_harness_files()'s `git add -A` staged it
    # in full. Confirmed live: a single `cargo test` in kiem_mini's rust/
    # produced a target/ dir that alone added 356 files (mostly binary
    # build artifacts) to the diff --stat — on every kiem_mini run, not a
    # hypothetical, completely burying whatever the agent actually
    # changed, which is the entire point of M-11's diff-stat feature.
    (run_dir / ".gitignore").write_text(
        ((run_dir / ".gitignore").read_text() + "\n" if (run_dir / ".gitignore").exists() else "")
        + "\n".join(f"{d}/" for d in _STALE_BUILD_CACHE_DIRS) + "\n"
    )
    subprocess.run(["git", "init", "-q"], cwd=run_dir, check=True)
    subprocess.run(["git", "add", "-A"], cwd=run_dir, check=True)
    subprocess.run(
        ["git", "-c", "user.email=bench@local", "-c", "user.name=bench", "commit", "-q", "-m", "baseline"],
        cwd=run_dir, check=True,
    )
    # Tagged (not just committed) so grading can restore/diff against it by
    # name later — "baseline" the commit MESSAGE isn't a resolvable git ref.
    subprocess.run(["git", "tag", "baseline"], cwd=run_dir, check=True)

    if (run_dir / "package-lock.json").exists():
        # `npm ci` (not `npm install`) — deterministic, uses the tracked
        # lockfile exactly, fails loudly instead of silently drifting if
        # the lockfile and package.json ever disagree.
        subprocess.run(["npm", "ci", "--silent"], cwd=run_dir, check=True)


def overlay_check_files(suite, task_id, run_dir, check_dest):
    """Copies the held-out grading file(s) into the run dir — only at grading
    time, after the agent has already finished, matching SCHEMA.md's
    lifecycle. check_dest is relative to the run dir.

    Raises if the checks/ dir is missing or empty, instead of silently
    no-op'ing (adversarial review finding H4): a task whose check spec sets
    `check_dest` is declaring that it NEEDS an overlay to be graded
    correctly — a missing/renamed/typo'd checks/ dir used to mean the
    grading command just ran the fixture's OWN already-passing tests and
    exited 0, a guaranteed false PASS for every model on a task that was
    never actually graded. Returns the copied filenames so the caller can
    record what was actually graded against.
    """
    src_dir = REPO / "checks" / suite / task_id
    if not src_dir.exists():
        raise FileNotFoundError(
            f"checks/{suite}/{task_id}/ does not exist, but this task's check "
            f"spec sets check_dest — grading would silently run only the "
            f"fixture's own pre-existing tests and report a false PASS. "
            f"Fix the path or the task/check spec, don't skip this."
        )
    copied = []
    dest_dir = run_dir / check_dest
    dest_dir.mkdir(parents=True, exist_ok=True)
    for item in src_dir.iterdir():
        if item.is_file():
            shutil.copy2(item, dest_dir / item.name)
            copied.append(item.name)
    if not copied:
        raise FileNotFoundError(
            f"checks/{suite}/{task_id}/ exists but contains no files to overlay "
            f"— same false-PASS risk as a missing directory."
        )
    return copied


_HARNESS_MANIFEST_FILES = (
    # Build/dependency manifests and lockfiles across every ecosystem this
    # repo's fixtures use — restored from the baseline commit before
    # grading, regardless of which suite is running (a no-op for files that
    # don't exist in a given fixture). Nothing stopped an agent from
    # editing these to make its own tests pass, or to disable a check
    # (adversarial review finding H5) — e.g. adding a Cargo.toml
    # [[test]] override, or deleting an inconvenient npm test script.
    "Cargo.toml", "Cargo.lock",
    "package.json", "package-lock.json",
    "deno.json", "deno.lock",
    "Package.swift", "Package.resolved",
    "tsconfig.json",
    # ".gitignore" added 2026-08-21 (3rd adversarial review, finding
    # CR3-5): restoring it undoes an agent editing it to HIDE a dangerous
    # file (see _DANGEROUS_NEW_FILES below) from git's normal view. The
    # dangerous-file sweep below no longer actually depends on this for
    # correctness (it now walks the filesystem directly, gitignore or not)
    # but restoring it is still the right thing to do — it's a harness file
    # like any other manifest here, and leaving an agent's tampered version
    # in place would be inconsistent with the rest of this list.
    ".gitignore",
)

# Files that have no legitimate reason to be CREATED FRESH by an agent
# completing a feature/debug/test-writing task in this repo's fixtures, but
# can each independently neuter a check regardless of the source/test files
# themselves being correct — e.g. `.cargo/config.toml` can force every test
# binary to report success (`[target.'cfg(all())'] runner = "true"`),
# `build.rs` runs arbitrary code before the crate even compiles, a
# `vitest.config.ts`/`deno.jsonc` can redirect which files a test command
# actually collects. Found by a second independent adversarial review
# (finding M-13): restore_harness_files() only ever restored TRACKED
# manifest paths (existing at baseline); a brand-new file matching one of
# these names was invisible to that logic entirely (and, before the M-11
# fix, invisible in the recorded diff too). Deleted outright if not present
# at baseline — unlike _HARNESS_MANIFEST_FILES, these aren't "restored" to
# a prior version, since a legitimate fixture has none of them to restore.
_DANGEROUS_NEW_FILES = {
    ".cargo/config.toml", ".cargo/config",
    "build.rs",
    "vitest.config.ts", "vitest.config.js", "vitest.config.mjs",
    "vitest.config.mts", "vitest.config.cts",
    "vitest.workspace.ts", "vitest.workspace.js",
    # "vite.config.*" added 2026-08-21 (3rd adversarial review, finding
    # CR3-4): vite's own config file can redirect test collection exactly
    # like vitest.config.* can (a project using Vitest via `vite.config.ts`
    # + a `test:` block, rather than a separate vitest.config.ts, is a
    # completely normal setup) — the old list only ever covered the
    # vitest-specific filename, missing this equally-capable variant.
    "vite.config.ts", "vite.config.js", "vite.config.mjs",
    "vite.config.mts", "vite.config.cts",
    "deno.jsonc",
}


def restore_harness_files(run_dir, check_dest=None):
    """Restore the grading harness to its baseline state before grading,
    undoing anything the agent did to the files it's graded BY rather than
    the files it was asked to edit (adversarial review finding H5). Returns
    a `git diff --stat` of what the agent actually changed (against the
    now-restored tree, i.e. excluding harness files) for the log row.
    """
    # Diff stat captured BEFORE restoring, so it reflects everything the
    # agent touched (including any harness tampering this is about to
    # revert) — visible in the log even though it gets undone. `git add -A`
    # first — found by a second independent adversarial review (finding
    # M-11): plain `git diff --stat` never lists untracked files at all,
    # so a NEW file the agent created (exactly the deliverable for a
    # *-testwrite task) recorded as "the agent changed nothing". Staging
    # doesn't commit anything and doesn't affect what actually gets graded.
    subprocess.run(["git", "add", "-A"], cwd=run_dir, capture_output=True)
    diff = subprocess.run(
        ["git", "diff", "--stat", "baseline"],
        cwd=run_dir, capture_output=True, text=True,
    ).stdout.strip()

    # Found by a second independent adversarial review (finding H-1): this
    # used to check bare basenames ("Cargo.toml") against run_dir's TOP
    # level only — a no-op for kiem_mini, the only suite this repo has ever
    # actually run against a model, since its Cargo.toml lives at
    # rust/Cargo.toml, not the fixture root (hearth_mini/kipclip_mini are
    # flat, single-root fixtures, so the bug never showed up on those).
    # Confirmed live: an agent-tampered rust/Cargo.toml survived the old
    # restore untouched. Fixed by asking git itself for every baseline path
    # whose basename matches, anywhere in the tree, instead of assuming a
    # fixed depth.
    tracked = subprocess.run(
        ["git", "ls-tree", "-r", "--name-only", "baseline"],
        cwd=run_dir, capture_output=True, text=True,
    ).stdout.splitlines()
    restore_paths = [
        p for p in tracked
        if Path(p).name in _HARNESS_MANIFEST_FILES
    ]
    if check_dest:
        restore_paths.append(check_dest)
    for path in restore_paths:
        subprocess.run(
            ["git", "checkout", "-q", "baseline", "--", path],
            cwd=run_dir, capture_output=True,
        )  # best-effort: silently no-ops for a path baseline never had

    # Delete any brand-new dangerous file (see _DANGEROUS_NEW_FILES above)
    # that didn't exist at baseline — these have no "prior version" to
    # restore to, so checkout can't help; only removal does.
    #
    # Walks the filesystem directly rather than `git ls-files` (3rd
    # adversarial review, finding CR3-5): `git ls-files` only lists TRACKED
    # files, and `git add -A` above silently skips anything matched by
    # .gitignore — so an agent editing .gitignore to exclude its own
    # vitest.config.ts (or any other _DANGEROUS_NEW_FILES entry) made that
    # file invisible to the old sweep entirely, regardless of the
    # .gitignore-restore fix above (this runs BEFORE that restore would
    # even matter, and a fixture with no baseline .gitignore at all has
    # nothing to restore to anyway). Confirmed live: a scratch repo with a
    # baseline package.json, an agent-added .gitignore excluding
    # vitest.config.ts, and a resulting vitest.config.ts survived the old
    # `git ls-files`-based sweep untouched.
    for full_path in run_dir.rglob("*"):
        if not full_path.is_file():
            continue
        rel = full_path.relative_to(run_dir)
        if rel.parts[0] == ".git":
            continue
        p = rel.as_posix()
        name = full_path.name
        is_dangerous = name in _DANGEROUS_NEW_FILES or any(
            p == d or p.endswith("/" + d) for d in _DANGEROUS_NEW_FILES if "/" in d
        )
        if not is_dangerous:
            continue
        at_baseline = subprocess.run(
            ["git", "cat-file", "-e", f"baseline:{p}"],
            cwd=run_dir, capture_output=True,
        ).returncode == 0
        if not at_baseline:
            full_path.unlink(missing_ok=True)
    return diff


def grade_command(suite, task, run_dir):
    check = task["check"]
    diff_stat = restore_harness_files(run_dir, check.get("check_dest"))
    if "check_dest" in check:
        overlay_check_files(suite, task["id"], run_dir, check["check_dest"])
    cwd = run_dir / check.get("cwd", ".")
    proc = subprocess.run(check["command"], shell=True, cwd=str(cwd), capture_output=True, text=True)
    expect = check.get("expect_exit_code", 0)
    passed = proc.returncode == expect
    output = (proc.stdout + proc.stderr)[-2000:]
    # Returned as its OWN value now, not prepended into `output` (3rd
    # adversarial review, finding CR3-9): the caller truncates grade_output
    # to its last 500 chars for the log row — prepending the diff stat to
    # the FRONT of `output` put it in exactly the position that truncation
    # destroys, while L-3's fix for grade_mutation.sh's compile-failure
    # warning explicitly restated ITS summary at the END specifically
    # because "truncation always keeps the tail". Same bug, opposite end.
    # A dedicated field survives regardless of grade_output's length.
    return passed, output, diff_stat


def grade_mutation(task, run_dir):
    check = task["check"]
    source_file = check["source_file"]

    # agent_test_file/require_kill enforcement added (3rd adversarial
    # review, finding CR3-15): tasks/SCHEMA.md documents both as part of
    # a mutation check's contract, but nothing in this function (or
    # grade_mutation.sh) ever read either field — for THIS repo's three
    # existing testwrite tasks that's harmless by construction (each
    # task's test_command already hardcodes the exact same path as its
    # own agent_test_file, and grade_mutation.sh's kill-rate logic already
    # only implements "require every mutant killed", matching the only
    # value require_kill has ever been set to), but nothing would have
    # caught a FUTURE task author setting either field to something that
    # silently doesn't match reality. Made real instead of decorative:
    if check.get("require_kill", "all") != "all":
        return False, (
            f"task declares require_kill: {check['require_kill']!r}, but "
            f"grade_mutation.sh only ever implements 'require every mutant "
            f"killed' — this value would have been silently ignored."
        ), None
    agent_test_file = check.get("agent_test_file")
    if agent_test_file and not (run_dir / agent_test_file).exists():
        return False, (
            f"agent_test_file {agent_test_file!r} does not exist in the run "
            f"dir — the agent never created its test file at the path this "
            f"task's prompt names, regardless of what test_command reports."
        ), None

    # Restore build manifests/lockfiles before grading, same as
    # grade_command() already did — this call was missing entirely until a
    # second independent adversarial review (finding H-2): mutation-graded
    # test-writing tasks are exactly where an agent is most likely to touch
    # Cargo.toml/package.json/deno.json (adding a dependency for its new
    # test file, or accidentally disabling a lint), and this path had zero
    # protection against that beyond the single-file source_file check
    # below.
    diff_stat = restore_harness_files(run_dir)

    # Test-writing tasks explicitly instruct "Do not modify <source_file>"
    # — the whole point is to grade tests written against the REAL
    # implementation. grade_mutation.sh used to `cp` whatever was
    # currently on disk (i.e. whatever the agent left behind, tampered
    # with or not) and call it "the correct implementation" for both the
    # baseline check and every mutant swap (adversarial review finding
    # H5). Hard-fail here, before any of that, if the agent touched it.
    diff = subprocess.run(
        ["git", "diff", "--name-only", "baseline", "--", source_file],
        cwd=run_dir, capture_output=True, text=True,
    ).stdout.strip()
    if diff:
        return False, (
            f"agent modified {source_file}, which this task's prompt explicitly "
            f"says not to touch — grading a test-writing task against a "
            f"self-modified implementation would prove nothing. Diff:\n"
            + subprocess.run(
                ["git", "diff", "baseline", "--", source_file],
                cwd=run_dir, capture_output=True, text=True,
            ).stdout[-1500:]
        ), diff_stat

    cmd = [str(REPO / "runner" / "grade_mutation.sh"), str(run_dir), source_file,
           check["test_command"], check.get("cwd", ".")]
    cmd += [str(REPO / m) for m in check["mutants"]]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    return proc.returncode == 0, proc.stdout[-2000:], diff_stat


def wait_for_proxy_idle(proxy_port, timeout=60):
    """Block until bench_local_proxy.py's generation queue is genuinely idle.

    Killed-task retry hazard, found live 2026-08-20: killing a
    run_fixture_suite.py subprocess does NOT cancel its already-in-flight
    request server-side (the proxy's queue has no way to abort an
    in-progress urllib call, by design — see bench_local_proxy.py's
    GenerationQueue docstring). A quick retry can then queue behind that
    orphaned request, trip hermes chat's own client-side timeout, and
    produce a spurious FAIL — reproduced live on Qwen3-Coder-30B-A3B MLX.
    /healthz already reports `generation_queue.active` / `.queued`
    (bench_local_proxy.py's Handler.do_GET) — this just waits for both to
    read zero before letting the caller proceed, instead of relying on a
    human remembering to check the proxy log first.
    """
    url = f"http://127.0.0.1:{proxy_port}/healthz"
    start = time.time()
    while time.time() - start < timeout:
        try:
            with urllib.request.urlopen(url, timeout=3) as resp:
                data = json.loads(resp.read())
            queue = data.get("generation_queue", {})
            if queue.get("active", 0) == 0 and queue.get("queued", 0) == 0:
                return True
        except (urllib.error.URLError, TimeoutError, ValueError):
            pass
        time.sleep(1)
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--suite", required=True)
    ap.add_argument("--hermes-provider", required=True)
    ap.add_argument("--hermes-model", required=True)
    ap.add_argument("--log-model", default=None,
                    help="source model ID to record when --hermes-model is a stable served alias")
    ap.add_argument("--inference-engine", required=True, help="llama.cpp | vllm-mlx | omlx | ..., recorded in the log")
    ap.add_argument("--quant", default=None)
    ap.add_argument("--only-task", default=None, help="run just this one task id")
    ap.add_argument("--max-turns", type=int, default=40)
    ap.add_argument("--config", default=None, help="path to configs/<model>/<backend>.yaml used for this run")
    ap.add_argument("--trials", type=int, default=1,
                     help="run each task N times (default 1) — adversarial review "
                          "finding C5: temperature=0 does NOT make MLX/Metal generation "
                          "deterministic across runs (confirmed live: same model/config/"
                          "task flipped pass<->fail across two runs), so a single trial "
                          "is not enough to trust a pass/fail as the model's real behavior")
    args = ap.parse_args()

    task_file = REPO / "tasks" / f"{args.suite}.yaml"
    spec = yaml.safe_load(task_file.read_text())
    timeout = spec.get("timeout_seconds", 900)

    config_path = None
    config_hash = None
    proxy_port = None
    raw_port = None
    system_prompt_suffix = None
    if args.config:
        config_hash, config_path = snapshot_config(args.config)
        cfg = yaml.safe_load(Path(args.config).read_text())
        orch = cfg.get("orchestration") or {}
        if orch.get("needs_proxy"):
            proxy_port = orch.get("proxy_port", 8015)
        raw_port = orch.get("raw_port")  # for PeakRSSSampler — the real
            # server's port, not the proxy's (finding F7); None for a
            # hosted/API config with no local server to sample.
        # Applied to sanity/hermes_ops via run_prompt_suite.py's real
        # system-prompt append, but silently NOT applied here at all until
        # this fix (adversarial review finding H8) — hermes chat's CLI has
        # no equivalent "append to system prompt" flag, so the closest
        # faithful approximation is prepending it to the task prompt itself
        # (the model still reads the operating instruction before starting,
        # just as part of the user turn instead of the system turn). Any
        # config with this set previously had it apply to 2 of 3 suites
        # without that being visible anywhere.
        system_prompt_suffix = cfg.get("system_prompt_suffix")

    def ensure_proxy_idle():
        # Checked before EVERY hermes invocation, not just once before the
        # whole loop (that was the bug: a timeout on task N left an
        # in-flight request that could still collide with task N+1 within
        # the same invocation — the "killed-task retry hazard" wasn't
        # actually fully closed by a single upfront check).
        #
        # Raises a plain RuntimeError, not sys.exit() (3rd adversarial
        # review, finding CR3-... low): this used to be called BEFORE the
        # per-task try/except block even existed positionally, and
        # sys.exit() raises SystemExit — a BaseException, not an
        # Exception subclass, so it would have kept sailing straight past
        # `except Exception` even if it HAD been moved inside. Either gap
        # alone was enough to abort the entire remaining task×trial loop
        # on a single stuck proxy. Confirmed live: a mocked always-stuck
        # wait_for_proxy_idle killed main() outright via SystemExit with
        # ZERO rows written, not even a harness-error row for the first
        # task, and a second task never got a chance to run at all.
        if not proxy_port:
            return
        if not wait_for_proxy_idle(proxy_port):
            raise RuntimeError(
                f"proxy on port {proxy_port} still has an active/queued "
                f"request after 60s — a previous run may have been killed "
                f"without its in-flight request finishing. Check "
                f"/tmp/bench_proxy_{proxy_port}.log before retrying."
            )

    log_path = REPO / "results" / "log.jsonl"
    rows = []

    # Run dirs live under the repo (gitignored), NOT the OS default temp dir.
    # Discovered live 2026-08-20: on macOS, tempfile's default location
    # resolves to /private/var/folders/... — which trips Hermes's own
    # sensitive-system-path write guardrail (tools/file_tools.py's
    # _SENSITIVE_PATH_PREFIXES includes "/private/var/", intended for
    # genuinely sensitive locations, not realizing it also covers macOS's
    # ordinary per-user scratch space). That guardrail has no config-level
    # override, and patching Hermes's own source would change its real
    # daily-driver security behavior, not just this benchmark's — so fixed
    # here instead, entirely within this repo's control.
    runs_root = REPO / "runner" / "runs"
    runs_root.mkdir(parents=True, exist_ok=True)
    for task in spec["tasks"]:
        if args.only_task and task["id"] != args.only_task:
            continue
        for trial in range(1, args.trials + 1):
            with tempfile.TemporaryDirectory(dir=str(runs_root)) as td:
                run_dir = Path(td) / "run"
                task_start = time.time()
                transcript_rel = None
                harness_error = False
                diff_stat = None
                peak_rss_gb = None
                session_stats = dict(_EMPTY_SESSION_STATS)
                try:
                    ensure_proxy_idle()
                    reset_fixture(args.suite, run_dir)

                    prompt = task["prompt"]
                    if system_prompt_suffix:
                        prompt = f"[Operating instruction: {system_prompt_suffix}]\n\n{prompt}"
                    prompt = isolated_agent_prompt(prompt, run_dir)
                    fixture_guard = {}
                    # Sampled continuously for the task's duration, not
                    # snapshotted once at the end (methodology review,
                    # finding F7) — a single end-of-task read would miss a
                    # transient peak mid-generation. Targets the REAL
                    # server's raw_port, not the proxy, since that's the
                    # process actually holding the model weights + KV cache.
                    rss_sampler = PeakRSSSampler(raw_port).start()
                    with preserve_repository(REPO, fixture_guard):
                        stdout, stderr, rc, wall, timed_out = run_hermes(
                            prompt, run_dir, args.hermes_provider, args.hermes_model,
                            max_turns=args.max_turns, timeout=timeout,
                        )
                    peak_rss_gb = rss_sampler.stop()
                    session_stats = extract_hermes_session_stats(stdout, stderr)

                    # Full transcript, saved and committed (not just the last 500
                    # chars of grade_output) — discovered live 2026-08-20 that no
                    # coding-suite run had ever saved its actual transcript
                    # anywhere, which made a genuinely-suspicious result (Luna
                    # failing a task it should have handled easily) impossible to
                    # verify without a slow, manual live rerun. Every PASS/FAIL
                    # this session before this fix was judged on exit code + the
                    # final grade_output only, never the agent's actual behavior.
                    transcript_dir = REPO / "results" / "transcripts" / args.suite / task["id"]
                    transcript_dir.mkdir(parents=True, exist_ok=True)
                    model_slug = re.sub(r"[^A-Za-z0-9._-]+", "_", args.hermes_model)
                    trial_suffix = f"_trial{trial}" if args.trials > 1 else ""
                    transcript_path = transcript_dir / f"{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}_{model_slug}{trial_suffix}.log"
                    transcript_path.write_text(
                        f"$ hermes chat --profile bench --provider {args.hermes_provider} "
                        f"-m {args.hermes_model} --max-turns {args.max_turns}\n\n"
                        f"--- stdout ---\n{stdout}\n\n--- stderr ---\n{stderr}\n"
                    )
                    transcript_rel = str(transcript_path.relative_to(REPO))

                    if timed_out:
                        passed, grade_output = False, f"TIMEOUT after {timeout}s"
                    elif task["check"]["type"] == "mutation":
                        passed, grade_output, diff_stat = grade_mutation(task, run_dir)
                    else:
                        passed, grade_output, diff_stat = grade_command(args.suite, task, run_dir)
                    if fixture_guard["changed"]:
                        passed = False
                        harness_error = True
                        grade_output = (
                            "HARNESS ERROR: agent escaped the disposable run root and edited "
                            "the benchmark checkout; source bytes were restored.\n" + grade_output
                        )
                except Exception as exc:
                    # A crash ANYWHERE above (reset_fixture's `npm ci`
                    # hitting a network blip, overlay_check_files's
                    # FileNotFoundError from the H4 fix, any other bug) used
                    # to propagate straight out of main() and abort the
                    # WHOLE task×trial loop, discarding every row already
                    # written in memory — found by a second independent
                    # adversarial review (finding H-3), made materially
                    # worse by this session's own --trials/--coding-suites
                    # additions turning a single run into potentially hours
                    # of work. Record this task as a harness error and move
                    # on to the next one instead.
                    passed, grade_output = False, f"HARNESS ERROR: {type(exc).__name__}: {exc}"
                    rc, wall = -2, time.time() - task_start
                    harness_error = True

                row = {
                    "suite": args.suite,
                    "task_id": task["id"],
                    "task_type": task.get("type"),
                    "model": args.log_model or args.hermes_model,
                    "inference_engine": args.inference_engine,
                    "config_path": config_path,
                    "config_hash": config_hash,
                    "runner_git_sha": git_sha(),
                    "quant": args.quant,
                    "trial": trial,
                    "pass": passed,
                    # Set only in the `except` branch above (3rd adversarial
                    # review, finding CR3-6): this field was written by
                    # run_prompt_suite.py's own H-3 fix but nothing here
                    # produced the equivalent, so a fixture-suite harness
                    # crash (e.g. `npm ci` hitting a network blip) was
                    # indistinguishable from a genuine model failure to
                    # every downstream consumer (_majority_pass's sanity
                    # gate, build_leaderboard.py's pass-rate/flaky-task
                    # logic) — all of which now check this field.
                    "harness_error": harness_error,
                    "hermes_exit_code": rc,
                    "wall_seconds": round(wall, 1),
                    # A correct answer that took many minutes isn't
                    # something a real interactive session would tolerate,
                    # even though it's fully entitled to the generous
                    # timeout_seconds budget above (methodology review,
                    # finding F5) — see bench_common.py's
                    # INTERACTIVE_BUDGET_SECONDS for why this is a
                    # separate, distinct signal from timeout/pass.
                    "within_budget": wall <= INTERACTIVE_BUDGET_SECONDS,
                    "grade_output": grade_output.strip()[-500:],
                    # Own dedicated field, not prepended into grade_output
                    # (3rd adversarial review, finding CR3-9): grade_output
                    # above is truncated to its LAST 500 chars — M-11's
                    # diff-stat used to be prepended to the FRONT of that
                    # same string, guaranteeing it got cut whenever the
                    # actual command output was long, the exact class of
                    # bug L-3's fix for grade_mutation.sh called out
                    # ("truncation always keeps the tail"). Capped
                    # independently here so it survives regardless of
                    # grade_output's length.
                    "diff_stat": (diff_stat or "").strip()[-1000:] or None,
                    "peak_rss_gb": round(peak_rss_gb, 2) if peak_rss_gb is not None else None,
                    # Pulled from hermes's own SQLite session store
                    # (methodology review, finding F6) — turns/tool-calls/
                    # tokens from the ACTUAL coding workload, not just the
                    # two synthetic prompt suites. See
                    # extract_hermes_session_stats()'s docstring for the
                    # exact mechanism and its documented limitations.
                    **session_stats,
                    "transcript_path": transcript_rel,
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                }
                rows.append(row)
                # Written immediately, not batched until the whole task×trial
                # loop finishes — found by a second independent adversarial
                # review (finding H-3): `--trials`/`--coding-suites` (added
                # this same session) turned a multi-hour, all-tasks run into
                # a single unit that loses EVERY already-completed result if
                # anything later in the loop crashes (a network blip during
                # `npm ci`, a genuine grading exception, a killed process).
                with open(log_path, "a") as f:
                    f.write(json.dumps(row) + "\n")
                    f.flush()
                trial_label = f" (trial {trial}/{args.trials})" if args.trials > 1 else ""
                print(f"{task['id']}{trial_label}: {'PASS' if passed else 'FAIL'} ({wall:.0f}s)")

    n_pass = sum(r["pass"] for r in rows)
    print(f"\n{n_pass}/{len(rows)} passed. Appended to {log_path}")


if __name__ == "__main__":
    main()
