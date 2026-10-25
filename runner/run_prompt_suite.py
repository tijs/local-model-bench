#!/usr/bin/env python3
"""
Drives every `runner: prompt` task in a tasks/<suite>.yaml file against one
model+inference-engine combination, grades each, and appends a row per task
to results/log.jsonl.

Requires PyYAML. Run through the repository's locked uv environment:
  uv run --locked python runner/run_prompt_suite.py ...

Usage:
  run_prompt_suite.py --suite sanity --base-url http://127.0.0.1:8013/v1 \
      --model LiquidAI/LFM2.5-2.6B-MLX-bf16 --inference-engine vllm-mlx [--quant Q4_K_M]
"""
import argparse
import json
import os
import re
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import yaml

from bench_common import (
    INTERACTIVE_BUDGET_SECONDS, REPO, PeakRSSSampler, config_rank_eligible,
    git_sha, snapshot_config,
)

# Shared by the request path (run_prompt.py) and this module's config
# parsing: validates a generation-override mapping and fails loudly on an
# unknown field or wrongly-typed value instead of silently dropping it.
from run_prompt import normalize_generation_overrides

# Hard ceiling on one suite task, used when the suite file doesn't declare
# `task_timeout_seconds` itself. Before the 2026-08-25 timeout/liveness
# redesign the ONLY subprocess bound was derived as
# `timeout_seconds * max_turns + 60` — about 11 HOURS for hermes_ops
# (1000 * 40 + 60) — and that derived ceiling was reached in practice: a
# stalled oMLX stream held a server slot for 11 hours before a human
# noticed and killed it by hand, and several other configs had to be
# killed manually after 2+ hours in the same session. The per-turn
# liveness watchdogs in run_prompt.py catch a stalled stream in minutes;
# this is the backstop for everything they can't see (a hung child
# process, a wedged interpreter), so it deliberately stays generous — 4
# hours is far above the slowest genuine hermes_ops task ever recorded in
# results/log.jsonl (8839.9s ≈ 2.5h, a PASS) but far below 11 hours.
DEFAULT_TASK_TIMEOUT_CAP_SECONDS = 14400

# How long a task-deadline kill waits after SIGTERM before escalating to
# SIGKILL. Long enough for run_prompt.py to unwind and flush whatever it
# has, short enough that a wedged process can't extend the task budget
# meaningfully.
TASK_TIMEOUT_GRACE_SECONDS = 15


def run_with_task_deadline(cmd, timeout, grace=TASK_TIMEOUT_GRACE_SECONDS, **popen_kwargs):
    """Run *cmd* under a hard task deadline, terminating its whole process
    GROUP (not just the direct child) and preserving partial output.

    Returns (stdout, stderr, returncode, timed_out).

    start_new_session=True + killpg mirrors run_fixture_suite.run_hermes()'s
    own M9 fix, for the same reason: plain subprocess.run(timeout=...) only
    kills the direct child, leaving any grandchild it spawned running and
    the in-flight backend request still generating — which is exactly the
    killed-task retry hazard documented in run_fixture_suite.py. Graceful
    SIGTERM first so the child can flush its own partial stdout/stderr,
    then SIGKILL after *grace*.
    """
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
        **popen_kwargs,
    )
    try:
        stdout, stderr = proc.communicate(timeout=timeout)
        return stdout, stderr, proc.returncode, False
    except subprocess.TimeoutExpired:
        pass

    def _signal_group(sig):
        try:
            os.killpg(os.getpgid(proc.pid), sig)
        except (ProcessLookupError, PermissionError):
            pass  # already exited, or never got its own group

    _signal_group(signal.SIGTERM)
    try:
        stdout, stderr = proc.communicate(timeout=grace)
    except subprocess.TimeoutExpired:
        _signal_group(signal.SIGKILL)
        stdout, stderr = proc.communicate()
    # A distinct boolean rather than inferring from returncode (same
    # reasoning as run_fixture_suite.run_hermes()'s L-2 fix): a process
    # killed by an unrelated signal also reports a negative returncode.
    return stdout or "", stderr or "", proc.returncode, True


# Transport-level failure signatures: the request never reached a server, or the
# connection died before any response. Infrastructure, not model behaviour, so
# these must not be graded. An HTTP status (even 500) means a server DID answer
# and is left alone.
_TRANSPORT_FAILURE_MARKERS = (
    "connection refused",
    "connection reset by peer",
    "remote end closed connection",
    "remotedisconnected",
    "connection aborted",
    "failed to establish a new connection",
    "name or service not known",
    "nodename nor servname provided",
)


def _is_transport_failure(error_text):
    """True when `error_text` shows the server was unreachable."""
    if not error_text:
        return False
    text = str(error_text).lower()
    if "http " in text and any(
        f" {code}" in text for code in ("400", "401", "403", "404", "422", "500", "502", "503")
    ):
        return False
    return any(marker in text for marker in _TRANSPORT_FAILURE_MARKERS)


def active_suite_scope(suite):
    if suite not in ("sanity", "model_tools"):
        raise ValueError("application runtime suites are retired; use sanity/model_tools")
    return "model-only-v1"


def main(*, _allow_archived_suites=False):
    ap = argparse.ArgumentParser()
    ap.add_argument("--suite", required=True)
    ap.add_argument("--benchmark-scope", choices=("model-only-v1",), default=None)
    ap.add_argument("--base-url", required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--request-model", default=None,
                    help="endpoint model ID when it differs from the source model recorded in --model")
    ap.add_argument("--inference-engine", required=True, help="llama.cpp | llama.cpp-dflash2 | llama.cpp-dspark | mei | ..., recorded in the log. oMLX and vllm-mlx are retired active lanes (2026-09-04); log rows reading those values remain backward-compatible, they just aren't runnable current engines")
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
    ap.add_argument("--generation-profile", default=None,
                    help="(2026-09-22) name of a generation_profiles entry in --config to "
                         "apply as request-time overrides for THIS suite run — how a run "
                         "selects e.g. the capability/high vs practical/medium lane "
                         "without editing the config. Overrides the config's own "
                         "hermes_ops_generation_profile selector. Fails if the name is "
                         "not declared: profiles are explicit, there is no implicit "
                         "default profile.")
    args = ap.parse_args()

    if not _allow_archived_suites:
        try:
            args.benchmark_scope = active_suite_scope(args.suite)
        except ValueError as exc:
            ap.error(str(exc))

    task_file = REPO / "tasks" / f"{args.suite}.yaml"
    task_spec = yaml.safe_load(task_file.read_text())
    args.benchmark_scope = args.benchmark_scope or task_spec.get("benchmark_scope")
    if args.benchmark_scope and args.suite not in ("sanity", "model_tools"):
        ap.error("model-only scope accepts only sanity/model_tools; application runtime suites are retired")
    if task_spec.get("runner") != "prompt":
        sys.exit(f"{task_file} is not a prompt-runner suite (runner: {task_spec.get('runner')!r})")

    # Five EXPLICIT budgets rather than one number doing three jobs (see
    # tasks/SCHEMA.md's "Timeout and liveness budgets" section):
    #   timeout_seconds                 — total budget for ONE HTTP turn
    #   task_timeout_seconds            — total budget for one suite task
    #   connect_timeout_seconds         — TCP connect + request send + headers
    #   first_progress_timeout_seconds  — headers -> first meaningful event
    #   stream_idle_timeout_seconds     — between two meaningful events
    timeout = task_spec.get("timeout_seconds", 60)
    max_turns = task_spec.get("max_turns", 6)
    connect_timeout = task_spec.get("connect_timeout_seconds")
    first_progress_timeout = task_spec.get("first_progress_timeout_seconds")
    stream_idle_timeout = task_spec.get("stream_idle_timeout_seconds")
    no_response_retries = task_spec.get("no_response_retries")
    retry_delay = task_spec.get("retry_delay_seconds")
    # Default keeps the old derived value for suites that never came close
    # to it (sanity: 60*40+60 = 2460s), but caps it so no suite can
    # silently inherit the ~11-hour ceiling hermes_ops used to have.
    task_timeout = task_spec.get(
        "task_timeout_seconds",
        min(timeout * max_turns + 60, DEFAULT_TASK_TIMEOUT_CAP_SECONDS),
    )
    log_path = REPO / "results" / "log.jsonl"

    config_path = config_hash = None
    rank_eligible = True
    system_prompt_suffix = None
    api_key_env = None
    ttft_measurable = True
    raw_port = None
    hermes_ops_max_tokens = None
    # Resolved request-time generation overrides (2026-09-22): populated
    # ONLY when a named generation profile is actually selected for this
    # run (see the config block below). Empty for every pre-existing config
    # and for every non-hermes_ops suite without an explicit
    # --generation-profile, so the historic deterministic body is untouched.
    hermes_ops_generation = {}
    # Named generation profile selected for this run (None = no profile, the
    # historic temperature=0 lane). Bound here at function scope so a
    # no-config invocation (args.config is None) still records None on its
    # rows; the config block below resolves the actual name when present.
    selected_profile_name = None
    if args.config:
        config_hash, config_path = snapshot_config(args.config)
        config_yaml = yaml.safe_load(Path(args.config).read_text())
        rank_eligible = config_rank_eligible(config_yaml)
        raw_port = (config_yaml.get("orchestration") or {}).get("raw_port")  # for
            # PeakRSSSampler (methodology review, finding F7) — the real
            # server's port, not the proxy's; None for a hosted/API config.
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
        # Per-model override for hermes_ops's one-shot run_prompt.py client,
        # which (unlike the coding suites' real `hermes chat` agentic loop)
        # has no finish_reason=length continuation/retry logic of its own.
        # run_prompt.py's own --max-tokens default (4096) matches hermes's
        # real fitness-profile default, so this is only set for thinking-mode
        # models that need more budget to reason AND answer in one turn.
        hermes_ops_max_tokens = (config_yaml.get("model_max_tokens", task_spec.get("max_tokens", 1024))
                                  if args.benchmark_scope else config_yaml.get("hermes_ops_max_tokens"))
        # Named request-time generation profiles (2026-09-22, task-specific
        # generation settings — infrastructure only; schema + rationale in
        # configs/README.md "generation_profiles"). Each profile is an
        # explicit bundle of per-request sampling/reasoning overrides that
        # run_prompt.py carries on the one-shot prompt-suite client. Every
        # declared profile is validated HERE, before any task launches, so a
        # typo'ed field or wrongly-typed value fails this run loudly instead
        # of being silently dropped from the HTTP payload. Fields are
        # forwarded EXACTLY as declared; a profile that omits
        # reasoning_effort sends NO reasoning_effort at all (we never
        # silently assume a vendor effort — see the user's 2026-09-22 policy
        # note), and the only config key that can size hermes_ops max_tokens
        # remains hermes_ops_max_tokens (no duplicate/conflicting max-token
        # sources).
        generation_profiles = {}
        raw_profiles = config_yaml.get("generation_profiles") or {}
        if not isinstance(raw_profiles, dict):
            raise SystemExit(
                f"config {args.config}: generation_profiles must be a mapping of "
                f"profile-name -> fields, got {type(raw_profiles).__name__}"
            )
        for name, profile in raw_profiles.items():
            if not isinstance(profile, dict):
                raise SystemExit(
                    f"config {args.config}: generation_profiles[{name!r}] must be a "
                    f"mapping of field -> value, got {type(profile).__name__}"
                )
            try:
                generation_profiles[name] = normalize_generation_overrides(profile)
            except ValueError as exc:
                raise SystemExit(
                    f"config {args.config}: generation_profiles[{name!r}]: {exc}"
                ) from exc
        # SELECTION is explicit, never implicit:
        #   - hermes_ops_generation_profile: <name> selects the config-level
        #     default profile for the hermes_ops suite (absent = no overrides,
        #     i.e. old configs keep the historic temperature=0 behavior);
        #   - --generation-profile <name> overrides that for this suite run
        #     (how a run picks e.g. the capability/high vs practical/medium
        #     lane). A name that is not declared fails loudly — there is no
        #     implicit default profile.
        hermes_ops_profile_name = (config_yaml.get("model_tools_generation_profile")
                                   if args.benchmark_scope else config_yaml.get("hermes_ops_generation_profile"))
        if hermes_ops_profile_name is not None and hermes_ops_profile_name not in generation_profiles:
            raise SystemExit(
                f"config {args.config}: hermes_ops_generation_profile "
                f"{hermes_ops_profile_name!r} is not declared in generation_profiles "
                f"(declared: {', '.join(sorted(generation_profiles)) or 'none'}). "
                f"Profiles must be explicit — there is no implicit default profile."
            )
        selected_profile_name = None
        if args.generation_profile:
            selected_profile_name = args.generation_profile
        elif args.suite in ("hermes_ops", "model_tools") and hermes_ops_profile_name is not None:
            selected_profile_name = hermes_ops_profile_name
        if selected_profile_name is not None:
            if selected_profile_name not in generation_profiles:
                raise SystemExit(
                    f"config {args.config}: --generation-profile "
                    f"{selected_profile_name!r} is not declared in generation_profiles "
                    f"(declared: {', '.join(sorted(generation_profiles)) or 'none'}). "
                    f"Profiles must be explicit — there is no implicit default profile."
                )
            hermes_ops_generation = generation_profiles[selected_profile_name]

    rows = []
    for task in task_spec["tasks"]:
        if args.only_task and task["id"] != args.only_task:
            continue
        for trial in range(1, args.trials + 1):
            result_path_rel = None
            partial_output_rel = None
            timeout_phase = None
            parsed = {}
            peak_rss_gb = None
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
                        "--model", args.request_model or args.model,
                        "--spec", str(spec_path),
                        "--timeout", str(timeout),
                        "--max-turns", str(max_turns),
                    ]
                    if api_key_env:
                        cmd += ["--api-key-env", api_key_env]
                    if hermes_ops_max_tokens is not None:
                        cmd += ["--max-tokens", str(hermes_ops_max_tokens)]
                    if not hermes_ops_generation:
                        # Historic deterministic default, preserved
                        # byte-for-byte: with NO generation profile selected,
                        # temperature is explicitly 0 (see run_prompt.py's
                        # --temperature help — the flag is now optional, so
                        # the suite must say 0 out loud to keep the legacy
                        # wire shape). When a profile IS selected,
                        # temperature is forwarded only if the profile
                        # declares it; otherwise it is omitted so the
                        # backend serves its configured/default value and a
                        # profile can never silently fall back to
                        # temperature=0.
                        cmd += ["--temperature", "0"]
                    # Request-time generation overrides (2026-09-22): the
                    # resolved profile's fields become run_prompt.py flags,
                    # which only include them in the HTTP body when set.
                    # hermes_ops_generation stays empty unless a profile was
                    # explicitly selected, so old configs and non-hermes_ops
                    # suites without --generation-profile keep the historic
                    # deterministic body.
                    for key, value in hermes_ops_generation.items():
                        cmd += [f"--{key.replace('_', '-')}", str(value)]
                    if connect_timeout is not None:
                        cmd += ["--connect-timeout", str(connect_timeout)]
                    if first_progress_timeout is not None:
                        cmd += ["--first-progress-timeout", str(first_progress_timeout)]
                    if stream_idle_timeout is not None:
                        cmd += ["--stream-idle-timeout", str(stream_idle_timeout)]
                    if no_response_retries is not None:
                        cmd += ["--no-response-retries", str(no_response_retries)]
                    if retry_delay is not None:
                        cmd += ["--retry-delay", str(retry_delay)]
                    # Bounded by an EXPLICIT task budget, terminated as a
                    # process group, with partial output preserved — see
                    # run_with_task_deadline() and
                    # DEFAULT_TASK_TIMEOUT_CAP_SECONDS. This used to be
                    # `subprocess.run(..., timeout=timeout * max_turns + 60)`,
                    # a derived ~11-hour ceiling for hermes_ops that (a) was
                    # actually reached in practice and (b) killed only the
                    # direct child, leaving grandchildren and the in-flight
                    # backend request alive.
                    # Sampled continuously for the task's duration, not
                    # snapshotted once at the end (methodology review,
                    # finding F7) — a single end-of-task read would miss a
                    # transient peak mid-generation.
                    rss_sampler = PeakRSSSampler(raw_port).start()
                    run_stdout, run_stderr, _rc, task_timed_out = run_with_task_deadline(
                        cmd, timeout=task_timeout,
                    )
                    peak_rss_gb = rss_sampler.stop()
                    result_path.write_text(run_stdout)

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
                    durable_result_path.write_text(run_stdout or "{}")
                    result_path_rel = str(durable_result_path.relative_to(REPO))

                    if task_timed_out:
                        # A task-deadline kill leaves run_prompt.py's stdout
                        # partial or empty (it prints its result JSON only at
                        # the very end), so the ONLY evidence of what the
                        # model/engine was doing is whatever it had already
                        # written. Preserve it next to the durable result
                        # instead of discarding it — the whole reason this
                        # deadline exists is that the observed oMLX stalls
                        # were undiagnosable after the fact.
                        partial_path = durable_result_path.with_name(
                            durable_result_path.stem + "_partial.txt"
                        )
                        partial_path.write_text(
                            f"--- task timed out after {task_timeout}s "
                            f"(process group terminated) ---\n\n"
                            f"--- partial stdout ---\n{run_stdout}\n\n"
                            f"--- stderr ---\n{run_stderr}\n"
                        )
                        partial_output_rel = str(partial_path.relative_to(REPO))

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
                        parsed = json.loads(run_stdout)
                    except json.JSONDecodeError:
                        harness_crashed = True
                    timeout_phase = parsed.get("timeout_phase")

                    if task_timed_out:
                        # Deliberately NOT a harness_error: the harness did
                        # exactly what it was supposed to. A task that burns
                        # its whole budget without producing an answer is a
                        # MODEL/ENGINE failure and belongs in the leaderboard
                        # as one, distinct from an npm-blip-style
                        # infrastructure crash (which stays harness_error and
                        # is excluded from pass-rate maths downstream).
                        passed = False
                        harness_crashed = False
                        timeout_phase = "task_deadline"
                        grade_output = (
                            f"TIMEOUT (model/engine): task exceeded its "
                            f"{task_timeout}s budget and its process group was "
                            f"terminated. Partial output: {partial_output_rel}"
                        )
                    elif _is_transport_failure(parsed.get("error")):
                        # The inference server was UNREACHABLE — no HTTP response
                        # ever arrived, so nothing was graded and the model never
                        # got a chance to answer. run_prompt.py reports this as a
                        # normal `error` string and still exits with parseable
                        # JSON, so the JSONDecodeError check above cannot see it,
                        # and the row landed as an ordinary graded FAIL,
                        # indistinguishable from the model getting the task wrong.
                        #
                        # Found 2026-09-09 after a benchmark chain was killed
                        # mid-run to repoint it at a different build: two
                        # hermes_ops rows were recorded as model failures reading
                        # `<urlopen error [Errno 61] Connection refused>` — the
                        # exact "infrastructure crash" the comment above says
                        # belongs in harness_error and out of the pass-rate maths.
                        # The same happens to any run whose server OOMs, crashes,
                        # or is restarted underneath it.
                        #
                        # Deliberately narrow: only transport-level failures where
                        # no response arrived. An HTTP 4xx/5xx IS a real engine
                        # response (the context-cap rejection, for one) and stays
                        # a graded result.
                        passed = False
                        harness_crashed = True
                        grade_output = (
                            "HARNESS ERROR (server unreachable, not a graded model "
                            f"result): {parsed.get('error')}"
                        )
                    elif harness_crashed:
                        passed = False
                        grade_output = "HARNESS ERROR (not a graded model result): " + (
                            run_stderr.strip()[-1000:] or "run_prompt.py produced no parseable output"
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
                "benchmark_scope": args.benchmark_scope,
                "suite": args.suite,
                "task_id": task["id"],
                "task_type": task.get("type"),
                "model": args.model,
                "inference_engine": args.inference_engine,
                "quant": args.quant,
                "config_path": config_path,
                "config_hash": config_hash,
                "rank_eligible": False if args.benchmark_scope else rank_eligible,
                # Immutable resolved generation-lane metadata (2026-09-22):
                # the named generation_profiles entry selected for THIS row
                # (None = historic no-profile lane), plus the exact fields it
                # resolved to and were forwarded to run_prompt.py as
                # per-request overrides (empty when no profile is selected —
                # the historic temperature=0 lane). The sampler/effort values
                # actually on the wire are additionally recorded per-run in
                # the durable result JSON's `generation` field and surfaced
                # here via `generation` when the result was parseable.
                "generation_profile": selected_profile_name,
                "generation_overrides": (
                    dict(hermes_ops_generation) if hermes_ops_generation else None
                ),
                "harness_error": harness_crashed,
                "result_path": result_path_rel,
                # Which budget ran out, if any: "connect" / "first_progress"
                # / "stream_idle" / "turn_total" come from run_prompt.py's
                # own per-turn watchdogs; "task_deadline" is this file's
                # process-group kill. None for a run that finished (pass or
                # fail) without any timeout. Lets a reader tell a stalled
                # engine from a merely slow model from a dead backend —
                # all three used to be one undifferentiated failure.
                "timeout_phase": timeout_phase,
                "partial_output_path": partial_output_rel,
                "runner_git_sha": git_sha(),
                "trial": trial,
                "pass": passed,
                "grade_output": grade_output,
                "prompt_tokens": parsed.get("prompt_tokens"),
                "completion_tokens": parsed.get("completion_tokens"),
                "tokens_per_second": parsed.get("tokens_per_second"),
                "ttft_seconds": parsed.get("ttft_seconds"),
                # First token to last token, summed over turns. See
                # run_prompt.py: `wall - ttft` also contains post-answer server
                # work, which only became visible once prefix caching dropped
                # TTFT from ~54 s to ~2 s and the derived rate read 36.5 tok/s
                # against a server measuring 57.9. Measured from the stream, so
                # every engine is treated the same. None on older rows.
                "decode_window_seconds": parsed.get("decode_window_seconds"),
                "backend_prefill_seconds": parsed.get("backend_prefill_seconds"),
                "backend_generate_seconds": parsed.get("backend_generate_seconds"),
                "backend_cached_tokens": parsed.get("backend_cached_tokens"),
                "wall_seconds": parsed.get("wall_seconds"),
                # A correct answer that took many minutes isn't something
                # a real interactive session would tolerate, even though
                # it's fully entitled to the generous timeout_seconds
                # budget above (methodology review, finding F5) — see
                # bench_common.py's INTERACTIVE_BUDGET_SECONDS for why
                # this is a separate, distinct signal from timeout/pass.
                # None (not False) when wall_seconds itself is unknown
                # (e.g. a harness crash before run_prompt.py ever reported
                # one) — this row simply has no latency signal to judge,
                # not a fast one.
                "within_budget": (
                    parsed["wall_seconds"] <= INTERACTIVE_BUDGET_SECONDS
                    if parsed.get("wall_seconds") is not None else None
                ),
                "total_cost_usd": parsed.get("total_cost_usd"),
                "run_error": parsed.get("error") or (
                    f"task deadline exceeded ({task_timeout}s) — process group terminated"
                    if timeout_phase == "task_deadline" else None
                ),
                "usage_estimated": parsed.get("usage_estimated", False),
                "ttft_measurable": ttft_measurable,
                # The exact sampler/effort fields the backend received for this
                # task's first turn (run_prompt.py result `generation`), e.g.
                # {"temperature": 0} on the historic no-profile lane. None only
                # when run_prompt.py produced no parseable result.
                "generation": parsed.get("generation"),
                "peak_rss_gb": round(peak_rss_gb, 2) if peak_rss_gb is not None else None,
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
