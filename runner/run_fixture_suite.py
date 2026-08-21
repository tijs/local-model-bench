#!/usr/bin/env python3
"""
Drives every fixture-based task in tasks/<suite>.yaml against one model, via
the isolated "bench" hermes profile, in a fresh copy of the suite's fixture
per task (copy -> git init -> baseline commit -> hermes works here ->
grade -> discard). Appends one row per task to results/log.jsonl.

Requires PyYAML — run with a python that has it, e.g. cocore's:
  /Users/tijs/.cocore/python/bin/python runner/run_fixture_suite.py ...

Usage:
  run_fixture_suite.py --suite kiem_mini \
      --hermes-provider custom:local-mlx --hermes-model LiquidAI/LFM2.5-2.6B-MLX-bf16 \
      --backend mlx [--quant Q4_K_M] [--only-task kiem_mini-feature]
"""
import argparse
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

from bench_common import REPO, git_sha, snapshot_config

HERMES_BIN = Path(os.environ.get(
    "BENCH_HERMES_BIN", str(Path.home() / ".hermes/hermes-agent/venv/bin/hermes")
))  # override via env var instead of editing this file (adversarial review finding M8)


def run_hermes(prompt, cwd, provider, model, max_turns, timeout):
    cmd = [
        str(HERMES_BIN), "chat", "--profile", "bench", "-q", prompt,
        "--provider", provider, "-m", model, "-Q", "--yolo",
        "--max-turns", str(max_turns),
    ]
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
    ap.add_argument("--backend", required=True, help="mlx | gguf, recorded in the log")
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
    system_prompt_suffix = None
    if args.config:
        config_hash, config_path = snapshot_config(args.config)
        cfg = yaml.safe_load(Path(args.config).read_text())
        orch = cfg.get("orchestration") or {}
        if orch.get("needs_proxy"):
            proxy_port = orch.get("proxy_port", 8015)
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
        if not proxy_port:
            return
        if not wait_for_proxy_idle(proxy_port):
            sys.exit(
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
            ensure_proxy_idle()
            with tempfile.TemporaryDirectory(dir=str(runs_root)) as td:
                run_dir = Path(td) / "run"
                task_start = time.time()
                transcript_rel = None
                harness_error = False
                diff_stat = None
                try:
                    reset_fixture(args.suite, run_dir)

                    prompt = task["prompt"]
                    if system_prompt_suffix:
                        prompt = f"[Operating instruction: {system_prompt_suffix}]\n\n{prompt}"
                    stdout, stderr, rc, wall, timed_out = run_hermes(
                        prompt, run_dir, args.hermes_provider, args.hermes_model,
                        max_turns=args.max_turns, timeout=timeout,
                    )

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
                    "model": args.hermes_model,
                    "backend": args.backend,
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
