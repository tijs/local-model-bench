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
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
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
    lifecycle. check_dest is relative to the run dir."""
    src_dir = REPO / "checks" / suite / task_id
    if not src_dir.exists():
        return
    dest_dir = run_dir / check_dest
    dest_dir.mkdir(parents=True, exist_ok=True)
    for item in src_dir.iterdir():
        if item.is_file():
            shutil.copy2(item, dest_dir / item.name)


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
    args = ap.parse_args()

    task_file = REPO / "tasks" / f"{args.suite}.yaml"
    spec = yaml.safe_load(task_file.read_text())
    timeout = spec.get("timeout_seconds", 900)

    config_path = None
    config_hash = None
    if args.config:
        config_path = str(Path(args.config).resolve().relative_to(REPO))
        config_hash = hashlib.sha256(Path(args.config).read_bytes()).hexdigest()[:12]

    log_path = REPO / "results" / "log.jsonl"
    rows = []

    for task in spec["tasks"]:
        if args.only_task and task["id"] != args.only_task:
            continue
        with tempfile.TemporaryDirectory() as td:
            run_dir = Path(td) / "run"
            reset_fixture(args.suite, run_dir)

            stdout, stderr, rc, wall = run_hermes(
                task["prompt"], run_dir, args.hermes_provider, args.hermes_model,
                max_turns=args.max_turns, timeout=timeout,
            )

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
                "quant": args.quant,
                "pass": passed,
                "hermes_exit_code": rc,
                "wall_seconds": round(wall, 1),
                "grade_output": grade_output.strip()[-500:],
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }
            rows.append(row)
            print(f"{task['id']}: {'PASS' if passed else 'FAIL'} ({wall:.0f}s)")

    with open(log_path, "a") as f:
        for row in rows:
            f.write(json.dumps(row) + "\n")

    n_pass = sum(r["pass"] for r in rows)
    print(f"\n{n_pass}/{len(rows)} passed. Appended to {log_path}")


if __name__ == "__main__":
    main()
