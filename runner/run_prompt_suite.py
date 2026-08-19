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

REPO = Path(__file__).resolve().parent.parent


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--suite", required=True)
    ap.add_argument("--base-url", required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--backend", required=True, help="mlx | gguf, recorded in the log")
    ap.add_argument("--quant", default=None, help="quant level, for gguf log rows")
    args = ap.parse_args()

    task_file = REPO / "tasks" / f"{args.suite}.yaml"
    task_spec = yaml.safe_load(task_file.read_text())
    if task_spec.get("runner") != "prompt":
        sys.exit(f"{task_file} is not a prompt-runner suite (runner: {task_spec.get('runner')!r})")

    timeout = task_spec.get("timeout_seconds", 60)
    log_path = REPO / "results" / "log.jsonl"

    rows = []
    for task in task_spec["tasks"]:
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
            spec_path.write_text(json.dumps(prompt_spec))
            check_path.write_text(json.dumps(task["check"]))

            run = subprocess.run(
                [
                    sys.executable,
                    str(REPO / "runner" / "run_prompt.py"),
                    "--base-url", args.base_url,
                    "--model", args.model,
                    "--spec", str(spec_path),
                    "--timeout", str(timeout),
                ],
                capture_output=True,
                text=True,
            )
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
                "pass": passed,
                "grade_output": grade.stdout.strip(),
                "prompt_tokens": parsed.get("prompt_tokens"),
                "completion_tokens": parsed.get("completion_tokens"),
                "tokens_per_second": parsed.get("tokens_per_second"),
                "wall_seconds": parsed.get("wall_seconds"),
                "run_error": parsed.get("error"),
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }
            rows.append(row)
            print(f"{task['id']}: {'PASS' if passed else 'FAIL'} — {grade.stdout.strip()}")

    with open(log_path, "a") as f:
        for row in rows:
            f.write(json.dumps(row) + "\n")

    n_pass = sum(r["pass"] for r in rows)
    print(f"\n{n_pass}/{len(rows)} passed. Appended to {log_path}")


if __name__ == "__main__":
    main()
