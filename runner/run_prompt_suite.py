#!/usr/bin/env python3
"""
Drives every `runner: prompt` task in a tasks/<suite>.yaml file against one
model backend, grades each, and appends a row per task to results/log.jsonl.

Requires PyYAML — run with a Python that has it, e.g. cocore's:
  /Users/tijs/.cocore/python/bin/python runner/run_prompt_suite.py ...

Usage:
  run_prompt_suite.py --suite sanity --base-url http://127.0.0.1:8013/v1 \
      --model LiquidAI/LFM2.5-2.6B-MLX-bf16 --backend mlx [--quant Q4_K_M]
"""
import argparse
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import yaml

from bench_common import REPO, git_sha, snapshot_config


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--suite", required=True)
    ap.add_argument("--base-url", required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--backend", required=True, help="mlx | gguf, recorded in the log")
    ap.add_argument("--quant", default=None, help="quant level, for gguf log rows")
    ap.add_argument("--config", default=None, help="path to configs/<model>/<backend>.yaml used for this run")
    ap.add_argument("--only-task", default=None, help="run just this one task id (e.g. to rerun a single fixed/flaky task)")
    ap.add_argument("--trials", type=int, default=1,
                     help="run each task N times (default 1) — see run_fixture_suite.py's "
                          "--trials help for why single-trial temperature=0 results aren't "
                          "trustworthy on their own (adversarial review finding C5)")
    ap.add_argument("--summary-out", default=None,
                     help="write this invocation's own rows as JSON here — lets a caller "
                          "(run_bench.py) read exactly what THIS run produced instead of "
                          "reaching into the shared log by position (adversarial review "
                          "finding H3: a crashed/empty subprocess used to make the caller "
                          "silently read the PREVIOUS config's rows instead)")
    args = ap.parse_args()

    task_file = REPO / "tasks" / f"{args.suite}.yaml"
    task_spec = yaml.safe_load(task_file.read_text())
    if task_spec.get("runner") != "prompt":
        sys.exit(f"{task_file} is not a prompt-runner suite (runner: {task_spec.get('runner')!r})")

    timeout = task_spec.get("timeout_seconds", 60)
    max_turns = task_spec.get("max_turns", 6)
    log_path = REPO / "results" / "log.jsonl"

    config_path = config_hash = None
    system_prompt_suffix = None
    api_key_env = None
    if args.config:
        config_hash, config_path = snapshot_config(args.config)
        config_yaml = yaml.safe_load(Path(args.config).read_text())
        # A model-specific operating instruction the model needs to run as
        # intended (e.g. Muse-Glimmer's "Reasoning strength: high" toggle) —
        # NOT a way to hint at task content. This appends to the suite's
        # fixed system prompt, it never replaces or edits it, so the task
        # itself stays identical across models. Cite the source in the
        # config file's settings, same as any other model-specific setting.
        system_prompt_suffix = config_yaml.get("system_prompt_suffix")
        # Only the ENV VAR NAME is read from the config — the actual secret
        # is never written to a config file, never passed as a CLI arg to
        # the subprocess below (would leak via `ps`), and is read directly
        # from this process's own environment by run_prompt.py itself.
        api_key_env = (config_yaml.get("orchestration") or {}).get("api_key_env")

    rows = []
    for task in task_spec["tasks"]:
        if args.only_task and task["id"] != args.only_task:
            continue
        for trial in range(1, args.trials + 1):
            with tempfile.TemporaryDirectory() as td:
                td = Path(td)
                spec_path = td / "spec.json"
                check_path = td / "check.json"
                result_path = td / "result.json"
                prompt_spec = dict(task["prompt_spec"])
                if "system_prompt_file" in prompt_spec:
                    prompt_spec["system_prompt"] = (REPO / prompt_spec.pop("system_prompt_file")).read_text()
                if "tools_file" in prompt_spec:
                    prompt_spec["tools"] = json.loads((REPO / prompt_spec.pop("tools_file")).read_text())
                if system_prompt_suffix:
                    prompt_spec["system_prompt"] = (
                        prompt_spec.get("system_prompt", "") + "\n\n" + system_prompt_suffix
                    )
                spec_path.write_text(json.dumps(prompt_spec))
                check_path.write_text(json.dumps(task["check"]))

                cmd = [
                    sys.executable,
                    str(REPO / "runner" / "run_prompt.py"),
                    "--base-url", args.base_url,
                    "--model", args.model,
                    "--spec", str(spec_path),
                    "--timeout", str(timeout),
                    "--max-turns", str(max_turns),
                ]
                if api_key_env:
                    cmd += ["--api-key-env", api_key_env]
                run = subprocess.run(cmd, capture_output=True, text=True)
                result_path.write_text(run.stdout)

                grade = subprocess.run(
                    [
                        sys.executable,
                        str(REPO / "runner" / "grade_prompt.py"),
                        "--result", str(result_path),
                        "--check", str(check_path),
                    ],
                    capture_output=True,
                    text=True,
                )
                passed = grade.returncode == 0

                try:
                    parsed = json.loads(run.stdout)
                except json.JSONDecodeError:
                    parsed = {}

                row = {
                    "suite": args.suite,
                    "task_id": task["id"],
                    "task_type": task.get("type"),
                    "model": args.model,
                    "backend": args.backend,
                    "quant": args.quant,
                    "config_path": config_path,
                    "config_hash": config_hash,
                    "runner_git_sha": git_sha(),
                    "trial": trial,
                    "pass": passed,
                    "grade_output": grade.stdout.strip(),
                    "prompt_tokens": parsed.get("prompt_tokens"),
                    "completion_tokens": parsed.get("completion_tokens"),
                    "tokens_per_second": parsed.get("tokens_per_second"),
                    "ttft_seconds": parsed.get("ttft_seconds"),
                    "wall_seconds": parsed.get("wall_seconds"),
                    "total_cost_usd": parsed.get("total_cost_usd"),
                    "run_error": parsed.get("error"),
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                }
                rows.append(row)
                trial_label = f" (trial {trial}/{args.trials})" if args.trials > 1 else ""
                print(f"{task['id']}{trial_label}: {'PASS' if passed else 'FAIL'} — {grade.stdout.strip()}")

    with open(log_path, "a") as f:
        for row in rows:
            f.write(json.dumps(row) + "\n")

    if args.summary_out:
        Path(args.summary_out).write_text(json.dumps(rows))

    n_pass = sum(r["pass"] for r in rows)
    print(f"\n{n_pass}/{len(rows)} passed. Appended to {log_path}")


if __name__ == "__main__":
    main()
