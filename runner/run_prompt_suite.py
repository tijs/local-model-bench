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
import re
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
    ttft_measurable = True
    if args.config:
        config_hash, config_path = snapshot_config(args.config)
        config_yaml = yaml.safe_load(Path(args.config).read_text())
        # bench_local_proxy.py buffers the whole upstream response into ONE
        # SSE chunk (see its _send_stream()), so for any proxied config
        # "ttft_seconds" structurally equals total generation time, not a
        # real time-to-first-token — confirmed live (adversarial review
        # finding H6). Flagged in the log row rather than left to look like
        # every other model's real TTFT in the same leaderboard column.
        ttft_measurable = not (config_yaml.get("orchestration") or {}).get("needs_proxy")
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
            result_path_rel = None
            parsed = {}
            try:
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
                    # Wall-clock bound added (3rd adversarial review, low
                    # finding): this subprocess.run() had no timeout= at
                    # all, so a run_prompt.py that hung for any reason
                    # run_prompt.py's own per-call --timeout doesn't cover
                    # (a genuine bug, a hung child process it spawns)
                    # would block this ENTIRE task×trial loop forever, with
                    # no recovery short of manual intervention — this
                    # suite's own theoretical ceiling is already
                    # max_turns * timeout_seconds (each turn's own client-
                    # side timeout, per call_backend_streaming), so bound
                    # the subprocess to comfortably above that instead of
                    # not bounding it at all. TimeoutExpired is a normal
                    # Exception subclass, so this is already caught by the
                    # try/except around this whole block (finding CR3-13)
                    # and recorded as a harness_error row, same as any
                    # other crash.
                    run = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout * max_turns + 60)
                    result_path.write_text(run.stdout)

                    # Full result (messages, tool_calls, final_text — everything
                    # run_prompt.py actually produced) persisted durably, not
                    # just inside the TemporaryDirectory that's deleted when
                    # this `with` block exits — found by a second independent
                    # adversarial review (finding H-4): the coding suite got
                    # durable transcripts on 2026-08-20 specifically because an
                    # un-investigable result was too costly to leave unverified;
                    # the prompt suites (sanity/hermes_ops) never got the same
                    # treatment, so none of this session's FOUR grading-logic
                    # changes (C2, M4, L4, L5) could ever be checked against
                    # what a model actually said — the answers were already gone.
                    result_dir = REPO / "results" / "prompt_results" / args.suite / task["id"]
                    result_dir.mkdir(parents=True, exist_ok=True)
                    model_slug = re.sub(r"[^A-Za-z0-9._-]+", "_", args.model)
                    trial_suffix = f"_trial{trial}" if args.trials > 1 else ""
                    durable_result_path = result_dir / f"{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}_{model_slug}{trial_suffix}.json"
                    durable_result_path.write_text(run.stdout or "{}")
                    result_path_rel = str(durable_result_path.relative_to(REPO))

                    # run_prompt.py crashing uncaught (e.g. a read timeout that
                    # wasn't a caught exception type — see run_prompt.py's own
                    # fix for this, finding M3) used to leave stdout empty;
                    # grade_prompt.py would then ALSO crash trying to json.loads
                    # an empty result file, and `grade.returncode == 0` being
                    # False produced an indistinguishable "pass: false,
                    # run_error: null" row — no different from a genuine graded
                    # model failure. Detect this BEFORE grading and tag it
                    # explicitly instead. NOTE: run_prompt.py's own returncode is
                    # NOT the right signal here — it legitimately exits 1 (with
                    # perfectly valid, parseable JSON) whenever it reports a real
                    # run_error (e.g. "exceeded max_turns"), so returncode alone
                    # can't distinguish that from an actual crash. Only a failure
                    # to parse stdout as JSON at all means the process died
                    # before reaching its own final print/exit.
                    harness_crashed = False
                    try:
                        parsed = json.loads(run.stdout)
                    except json.JSONDecodeError:
                        harness_crashed = True

                    if harness_crashed:
                        passed = False
                        grade_output = "HARNESS ERROR (not a graded model result): " + (
                            run.stderr.strip()[-1000:] or "run_prompt.py produced no parseable output"
                        )
                    else:
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
                        grade_output = grade.stdout.strip()
            except Exception as exc:
                # A crash ANYWHERE above (a missing tools_file, a malformed
                # check dict, an OSError writing the durable result) used to
                # propagate straight out of main() and abort the WHOLE
                # task×trial loop — this file got the "write each row
                # immediately" half of run_fixture_suite.py's H-3 fix but
                # never the try/except half, so it never actually survived
                # a mid-loop crash. Found by a third independent
                # adversarial review (finding CR3-13); confirmed live with
                # a task pointing at a nonexistent tools_file: the whole
                # process died with an uncaught traceback and ZERO rows
                # were logged, including for a second, perfectly valid task
                # that never even got a chance to run. Record this trial as
                # a harness error and move on, same pattern as
                # run_fixture_suite.py's own except branch.
                passed, harness_crashed = False, True
                grade_output = f"HARNESS ERROR: {type(exc).__name__}: {exc}"

            row = {
                "suite": args.suite,
                "task_id": task["id"],
                "task_type": task.get("type"),
                "model": args.model,
                "backend": args.backend,
                "quant": args.quant,
                "config_path": config_path,
                "config_hash": config_hash,
                "harness_error": harness_crashed,
                "result_path": result_path_rel,
                "runner_git_sha": git_sha(),
                "trial": trial,
                "pass": passed,
                "grade_output": grade_output,
                "prompt_tokens": parsed.get("prompt_tokens"),
                "completion_tokens": parsed.get("completion_tokens"),
                "tokens_per_second": parsed.get("tokens_per_second"),
                "ttft_seconds": parsed.get("ttft_seconds"),
                "wall_seconds": parsed.get("wall_seconds"),
                "total_cost_usd": parsed.get("total_cost_usd"),
                "run_error": parsed.get("error"),
                "usage_estimated": parsed.get("usage_estimated", False),
                "ttft_measurable": ttft_measurable,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }
            rows.append(row)
            # Written immediately, not batched (adversarial review
            # finding H-3, same fix as run_fixture_suite.py) — a
            # multi-task/multi-trial run used to lose every
            # already-completed row if anything crashed later in the
            # loop.
            with open(log_path, "a") as f:
                f.write(json.dumps(row) + "\n")
                f.flush()
            trial_label = f" (trial {trial}/{args.trials})" if args.trials > 1 else ""
            print(f"{task['id']}{trial_label}: {'PASS' if passed else 'FAIL'} — {grade_output}")

    if args.summary_out:
        Path(args.summary_out).write_text(json.dumps(rows))

    n_pass = sum(r["pass"] for r in rows)
    print(f"\n{n_pass}/{len(rows)} passed. Appended to {log_path}")


if __name__ == "__main__":
    main()
