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
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

import yaml

from bench_common import REPO, git_sha, snapshot_config

HERMES_BIN = Path.home() / ".hermes/hermes-agent/venv/bin/hermes"


def run_hermes(prompt, cwd, provider, model, max_turns, timeout):
    cmd = [
        str(HERMES_BIN), "chat", "--profile", "bench", "-q", prompt,
        "--provider", provider, "-m", model, "-Q", "--yolo",
        "--max-turns", str(max_turns),
    ]
    start = time.time()
    try:
        proc = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, timeout=timeout)
        return proc.stdout, proc.stderr, proc.returncode, time.time() - start
    except subprocess.TimeoutExpired:
        return "", "TIMEOUT", -1, time.time() - start


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
}


def reset_fixture(suite, run_dir):
    src = REPO / "fixtures" / suite
    shutil.copytree(
        src, run_dir,
        ignore=shutil.ignore_patterns(*_STALE_BUILD_CACHE_DIRS),
    )
    subprocess.run(["git", "init", "-q"], cwd=run_dir, check=True)
    subprocess.run(["git", "add", "-A"], cwd=run_dir, check=True)
    subprocess.run(
        ["git", "-c", "user.email=bench@local", "-c", "user.name=bench", "commit", "-q", "-m", "baseline"],
        cwd=run_dir, check=True,
    )


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


def grade_command(suite, task, run_dir):
    check = task["check"]
    if "check_dest" in check:
        overlay_check_files(suite, task["id"], run_dir, check["check_dest"])
    cwd = run_dir / check.get("cwd", ".")
    proc = subprocess.run(check["command"], shell=True, cwd=str(cwd), capture_output=True, text=True)
    expect = check.get("expect_exit_code", 0)
    passed = proc.returncode == expect
    return passed, (proc.stdout + proc.stderr)[-2000:]


def grade_mutation(task, run_dir):
    check = task["check"]
    cmd = [str(REPO / "runner" / "grade_mutation.sh"), str(run_dir), check["source_file"], check["test_command"]]
    cmd += [str(REPO / m) for m in check["mutants"]]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    return proc.returncode == 0, proc.stdout[-2000:]


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
    if args.config:
        config_hash, config_path = snapshot_config(args.config)
        cfg = yaml.safe_load(Path(args.config).read_text())
        orch = cfg.get("orchestration") or {}
        if orch.get("needs_proxy"):
            proxy_port = orch.get("proxy_port", 8015)

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
                reset_fixture(args.suite, run_dir)

                stdout, stderr, rc, wall = run_hermes(
                    task["prompt"], run_dir, args.hermes_provider, args.hermes_model,
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

                if rc == -1:
                    passed, grade_output = False, f"TIMEOUT after {timeout}s"
                elif task["check"]["type"] == "mutation":
                    passed, grade_output = grade_mutation(task, run_dir)
                else:
                    passed, grade_output = grade_command(args.suite, task, run_dir)

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
                    "hermes_exit_code": rc,
                    "wall_seconds": round(wall, 1),
                    "grade_output": grade_output.strip()[-500:],
                    "transcript_path": transcript_rel,
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                }
                rows.append(row)
                trial_label = f" (trial {trial}/{args.trials})" if args.trials > 1 else ""
                print(f"{task['id']}{trial_label}: {'PASS' if passed else 'FAIL'} ({wall:.0f}s)")

    with open(log_path, "a") as f:
        for row in rows:
            f.write(json.dumps(row) + "\n")

    n_pass = sum(r["pass"] for r in rows)
    print(f"\n{n_pass}/{len(rows)} passed. Appended to {log_path}")


if __name__ == "__main__":
    main()
