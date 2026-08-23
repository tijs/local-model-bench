#!/usr/bin/env python3
"""
The single entry point for this whole benchmark: run one model+backend
config, or every config in the repo, unattended.

Requires PyYAML. Run benchmark orchestration through the repository's locked
uv environment:
  uv run --locked python runner/run_bench.py --config configs/<model>/<backend>.yaml
  uv run --locked python runner/run_bench.py --all
  uv run --locked python runner/run_bench.py --all --trials 3 --coding-suites kiem_mini,hearth_mini,kipclip_mini

Reads the `orchestration:` block each configs/<model>/<backend>.yaml file
carries (see configs/README.md for the schema) — that block is the single
source of truth this script drives off of, not anything re-derived from
this conversation. Adding a new candidate model means: copy an existing
config directory, adapt `benchmark_launch_command`/`settings`/
`orchestration` to the new model, done — no code changes needed unless the
new model needs a genuinely new mechanism (a new bench_local_proxy.py
parser, a special build like the DFlash2 fork).

What it does per config, in order:
  1. runner/unload_all.sh           — kill any existing candidate backend
  2. launch the server half of benchmark_launch_command (backgrounded)
  3. wait for the raw backend to answer /v1/models
  4. if orchestration.needs_proxy: launch bench_local_proxy.py with the
     right BENCH_TOOL_PARSER, wait for its health
  5. sanity suite — fail-fast: if sanity-basic fails, stop here
  6. hermes_ops suite (unless orchestration.viable says to skip it) —
     followed by a speed gate: if this run's own avg tok/s across every
     hermes_ops task is below bench_common.MIN_HERMES_OPS_TOKENS_PER_SECOND
     (10, a floor for practical interactive use — see that constant's own
     comment), skip the coding suite (typically far more expensive: real
     builds + multi-turn agentic loops) rather than spend that time
     confirming an outcome hermes_ops already answered
  7. the one coding-suite spot-check, kiem_mini-feature (unless
     orchestration.viable says to skip it, hermes_provider is unset, or
     the speed gate above tripped)
  8. regenerate results/LEADERBOARD.md
  9. tear down (unload_all.sh again) before moving to the next config,
     if running --all

`orchestration.viable` controls which of steps 5-7 run (the speed gate
inside step 6 only matters when the coding suite in step 7 would
otherwise run — `full`):
  full                       -> sanity, hermes_ops, coding
  sanity_and_hermes_ops_only -> sanity, hermes_ops (coding structurally
                                 blocked, e.g. hermes's 64K context
                                 minimum not met by this config)
  sanity_only                -> sanity only (a known sanity-tool failure,
                                 or coding/hermes_ops not worth attempting)
  coding_only                -> coding only (hosted/API models where
                                 sanity/hermes_ops can't reach a raw
                                 OpenAI-compatible endpoint, e.g. Luna)
  blocked                    -> skip entirely, print why and move on
                                 (e.g. Laguna-XS-2.1 MLX: mlx-lm doesn't
                                 support the architecture at all)

A `raw_port: null` config (api backend, no local server, e.g. Luna) skips
steps 1-4 entirely.
"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path
from statistics import mean

import yaml

from bench_common import MIN_HERMES_OPS_TOKENS_PER_SECOND

REPO = Path(__file__).resolve().parent.parent
CODING_SPOTCHECK_SUITE = "kiem_mini"
CODING_SPOTCHECK_TASK = "kiem_mini-feature"


def run(cmd, **kw):
    printable = cmd if isinstance(cmd, str) else " ".join(str(c) for c in cmd)
    print(f"$ {printable}")
    return subprocess.run(cmd, shell=isinstance(cmd, str), cwd=str(REPO), **kw)


def wait_for_health(url, timeout=600, proc=None):
    """proc, if given, is the just-launched server's Popen handle — if it
    has already exited, fail immediately instead of waiting out the full
    timeout only to report a generic "never became healthy" (adversarial
    review finding H2, partial: this alone doesn't catch a STALE process
    silently answering instead of the new one — see model/parser identity
    checks in run_one())."""
    print(f"Waiting for {url} to respond (timeout {timeout}s)...")
    start = time.time()
    while time.time() - start < timeout:
        if proc is not None and proc.poll() is not None:
            print(f"  server process exited early (returncode={proc.returncode}) — not waiting further")
            return False
        try:
            with urllib.request.urlopen(url, timeout=3) as resp:
                if resp.status == 200:
                    print(f"  healthy after {time.time() - start:.1f}s")
                    return True
        except (urllib.error.URLError, ConnectionError, TimeoutError, OSError):
            pass
        time.sleep(3)
    return False


def _majority_pass(rows):
    """More than half of *rows* passed. Used for the sanity fail-fast gate
    instead of requiring ALL rows to pass (adversarial review finding
    M-12): with --trials N, the flag added specifically to MEASURE
    flakiness made a single flaky failure among N trials abort hermes_ops
    AND the coding suite too — the more trials you run to detect
    flakiness, the more likely one of them randomly fails and the more
    destructive that single failure becomes. A flaky sanity result is
    still recorded (see the "Flaky tasks" leaderboard section) even when
    the majority passes and the run continues."""
    return sum(1 for r in rows if r["pass"]) * 2 > len(rows)


def _base_repo_name(model_id):
    """Strip a ':quant' suffix, e.g. 'foo/Bar-GGUF:Q4_K_M' -> 'foo/Bar-GGUF'."""
    return model_id.split(":")[0]


def assert_serving_expected_model(raw_port, expected_model, alias=None, served_model_id=None):
    """Confirm the server actually answering raw_port is serving the model
    THIS config expects, not a stale process left over from a previous
    config (adversarial review finding H2: wait_for_health only checks
    that *something* answers 200 — a leftover server on the same port
    would pass that check while silently serving the wrong model).

    When *alias* is given (gguf configs — see server_command()), this
    checks for an EXACT match against it instead of a repo-name substring
    match. Confirmed live: llama-server's --alias fully replaces /v1/models'
    "id" field with the given string. Needed because a repo-name substring
    match can't distinguish a config from its own speculative-decoding
    sibling (adversarial review finding H-5) — three pairs in this repo
    share both a base repo id and raw_port (e.g. Qwen3.8-27B/gguf.yaml vs.
    gguf-dflash2.yaml), so a stale sibling server answers with the
    identical id and would silently pass a substring check."""
    url = f"http://127.0.0.1:{raw_port}/v1/models"
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            data = json.loads(resp.read())
    except (urllib.error.URLError, OSError, ValueError) as e:
        print(f"FAILED: could not verify served model via {url}: {e}")
        return False
    served_ids = [m.get("id", "") for m in data.get("data", [])]
    # oMLX serves the local model-directory (or configured model-alias) ID,
    # not necessarily the source HF repository recorded as `model:` in the
    # benchmark config. A fuzzy source-ID match would accept an old oMLX
    # directory that happens to share part of the source name, so oMLX config
    # must supply a stable `orchestration.served_model_id` and match it exactly.
    if served_model_id:
        if served_model_id in served_ids:
            return True
        print(f"FAILED: {url} is serving {served_ids!r}, expected exact served_model_id "
              f"{served_model_id!r} — a stale oMLX process or model directory may be bound "
              "to this port.")
        return False
    if alias:
        if alias in served_ids:
            return True
        print(f"FAILED: {url} is serving {served_ids!r}, expected exact alias {alias!r} "
              f"— a stale sibling-config server (e.g. the plain vs. speculative-decoding "
              f"variant) may still be bound to this port.")
        return False
    expected = _base_repo_name(expected_model)
    if any(expected in sid or sid in expected for sid in served_ids if sid):
        return True
    print(f"FAILED: {url} is serving {served_ids!r}, expected something matching {expected!r} "
          f"— a stale server from a previous config may still be bound to this port.")
    return False


def assert_plain_completion(base_url, request_model, timeout=60):
    """Prove the selected endpoint can generate ordinary assistant text.

    A 200 /v1/models response only proves a process is listening. Before any
    benchmark rows are recorded, make one minimal non-streaming completion on
    the same served model ID that the suites will request.
    """
    url = f"{base_url.rstrip('/')}/chat/completions"
    body = json.dumps({
        "model": request_model,
        "messages": [{"role": "user", "content": "Reply with exactly: ready"}],
        "temperature": 0,
        "max_tokens": 8,
        "stream": False,
    }).encode()
    request = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as resp:
            data = json.loads(resp.read())
    except (urllib.error.URLError, OSError, ValueError) as e:
        print(f"FAILED: plain completion probe at {url} failed: {e}")
        return False
    choices = data.get("choices") or []
    message = (choices[0].get("message") or {}) if choices else {}
    content = message.get("content")
    # Some llama-server chat templates misclassify an entire short response
    # (this probe's whole 8-token budget) as reasoning_content, leaving
    # content empty — bench_local_proxy.py's normalize_response() already
    # has a documented 2026-08-20 fix for exactly this (confirmed live for
    # poolside/Laguna-XS-2.1), but that fix only runs for proxied configs;
    # this probe deliberately hits the RAW backend, before any proxy is
    # even started, so it never benefited from it. Confirmed live again
    # 2026-08-23: this false-failed poolside/Laguna-XS-2.1/gguf.yaml AND
    # LiquidAI/LFM2.5-2.6B-GGUF:Q8_0/gguf.yaml (a config with real,
    # previously-confirmed 45+ tok/s hermes_ops results) in the same
    # sweep — both servers' own logs showed a real completed generation at
    # probe time, so this is a probe-side false negative, not a dead
    # backend. tool_calls presence is also accepted as life, matching
    # normalize_response()'s own "tool_calls means don't touch it" logic.
    if isinstance(content, str) and content.strip():
        print("Plain completion probe passed.")
        return True
    if message.get("tool_calls"):
        print("Plain completion probe passed (tool_calls).")
        return True
    reasoning_content = message.get("reasoning_content")
    if isinstance(reasoning_content, str) and reasoning_content.strip():
        print("Plain completion probe passed (reasoning_content).")
        return True
    print(f"FAILED: plain completion probe returned no assistant content for {request_model!r}.")
    return False


def assert_proxy_matches(proxy_port, expected_parser, expected_upstream):
    """Same identity check as assert_serving_expected_model, for the proxy
    layer: a stale bench_local_proxy.py left bound to the port would also
    answer /healthz successfully while pointed at the wrong parser/upstream
    (the exact failure mode observed live 2026-08-20 — see AGENTS.md's
    killed-task retry hazard note)."""
    url = f"http://127.0.0.1:{proxy_port}/healthz"
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            data = json.loads(resp.read())
    except (urllib.error.URLError, OSError, ValueError) as e:
        print(f"FAILED: could not verify proxy identity via {url}: {e}")
        return False
    actual_parser = data.get("tool_call_parser")
    actual_upstream = data.get("upstream")
    if actual_parser == expected_parser and actual_upstream == expected_upstream:
        return True
    print(f"FAILED: proxy on {proxy_port} reports parser={actual_parser!r} upstream={actual_upstream!r}, "
          f"expected parser={expected_parser!r} upstream={expected_upstream!r} — "
          f"a stale proxy process is likely still bound to this port.")
    return False


def server_command(cfg, alias=None):
    """benchmark_launch_command sometimes documents a follow-up proxy step
    inline (as literal shell text, not a shell comment) — that's for a
    human reading the file, not something to execute as one blob. Only
    take the lines up to the first mention of bench_local_proxy.py.

    *alias*, when given, is appended as `--alias <alias>` on llama-server's
    own command line (adversarial review finding H-5): three config pairs
    in this repo share both a base HF repo id and raw_port (a plain config
    and its speculative-decoding sibling, e.g. Qwen3.8-27B/gguf.yaml vs.
    gguf-dflash2.yaml) — /v1/models reports the same `id` for both, so the
    repo-name identity check couldn't tell a stale sibling server from the
    one actually requested. llama-server (and both forked binaries used
    for DFlash2/DSpark) support --alias; vllm-mlx (the MLX backend) does
    not, so this only applies to gguf configs."""
    text = cfg["benchmark_launch_command"].strip()
    marker = "bench_local_proxy.py"
    if marker in text:
        idx = text.index(marker)
        # walk back to the start of the line that introduces this step
        # (the "# then, separately" comment line, if present) and cut there
        prior_newline = text.rfind("\n", 0, idx)
        comment_start = text.rfind("\n#", 0, idx)
        cut = comment_start if comment_start != -1 else prior_newline
        text = text[:cut].strip()
    if alias and cfg.get("framework", "").startswith("llama.cpp"):
        # A third independent adversarial review (finding CR3-2) found this
        # used to blindly string-append to the END of `text` — but
        # Qwen3.5-9B/gguf.yaml's launch block ends with a trailing shell
        # COMMENT (explaining a --ctx-size choice), so the alias landed
        # inside it and was never actually passed to llama-server at all.
        # /v1/models then reported the real repo id, assert_serving_
        # expected_model's exact-alias check failed, and that config was
        # silently skipped on every --all sweep. Walk backward past any
        # trailing blank/comment-only lines to find the actual last
        # command line, and append there instead.
        lines = text.split("\n")
        i = len(lines) - 1
        while i >= 0 and (not lines[i].strip() or lines[i].lstrip().startswith("#")):
            i -= 1
        if i < 0:
            text += f" --alias {alias}"  # entire block was comments/blank — fall back
        else:
            lines[i] = lines[i] + f" --alias {alias}"
            text = "\n".join(lines)
    return text


def _hermes_ops_tps_values(summary_path):
    """tokens_per_second from THIS invocation's own hermes_ops rows (every
    task the suite actually ran, not one probe task — see
    MIN_HERMES_OPS_TOKENS_PER_SECOND's own comment for why a single-task
    probe was tried and rejected), excluding harness_error rows the same
    way build_leaderboard.py's own avg-tok/s column does. None if the
    summary is missing/unreadable — treated as "don't gate on nothing",
    same discipline as the sanity gate above: a harness crash isn't
    evidence the MODEL is slow."""
    if not summary_path.exists():
        return None
    try:
        rows = json.loads(summary_path.read_text())
    except (json.JSONDecodeError, OSError):
        return None
    values = [r["tokens_per_second"] for r in rows
              if not r.get("harness_error") and r.get("tokens_per_second") is not None]
    return values or None


def _record_speed_gate_failure(model, framework, config_path, config_hash, measured, avg_tps):
    """Append one row to results/speed_gate.jsonl — a dedicated, append-
    only log kept separate from results/log.jsonl (whose task/suite-keyed
    schema every other grouping/flakiness check in build_leaderboard.py
    assumes) and separate from the config YAML files themselves (which
    stay hand-authored/human-curated — see configs/README.md — not
    something this script rewrites at run time). build_leaderboard.py
    renders this as its own "Speed-gated configs" section."""
    entry = {
        "model": model,
        "framework": framework,
        "config_path": str(config_path),
        "config_hash": config_hash,
        "suite": "hermes_ops",
        "measured_tokens_per_second": measured,
        "avg_tokens_per_second": avg_tps,
        "threshold_tokens_per_second": MIN_HERMES_OPS_TOKENS_PER_SECOND,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    path = REPO / "results" / "speed_gate.jsonl"
    with open(path, "a") as f:
        f.write(json.dumps(entry) + "\n")


def _run_one_impl(config_path: Path, trials: int = 1, coding_suites=None, stage="all"):
    cfg = yaml.safe_load(config_path.read_text())
    orch = cfg.get("orchestration")
    if not orch:
        sys.exit(f"{config_path} has no orchestration: block — see configs/README.md")

    model = cfg["model"]
    framework = cfg["framework"]
    served_model_id = orch.get("served_model_id")
    if cfg.get("framework") == "omlx" and not served_model_id:
        sys.exit(f"{config_path} is framework: omlx but has no orchestration.served_model_id")
    # oMLX deliberately serves a stable local directory/alias ID while log
    # rows retain the source artifact ID in `model`. Other frameworks request
    # the model ID directly as before.
    request_model = served_model_id or model
    config_hash = hashlib.sha256(config_path.read_bytes()).hexdigest()[:12]
    viable = orch.get("viable", "full")

    print(f"\n{'=' * 70}\n{model} ({framework}) — {config_path}\nviable={viable}\n{'=' * 70}")

    if viable == "blocked":
        print("SKIPPED (blocked) — see the config's known_gaps for why.")
        return

    raw_port = orch.get("raw_port")
    needs_proxy = orch.get("needs_proxy", False)
    proxy_port = orch.get("proxy_port", 8015)
    hermes_provider = orch.get("hermes_provider")
    api_base_url = orch.get("api_base_url")

    if api_base_url and not orch.get("api_key_env"):
        sys.exit(f"{config_path} sets api_base_url but no api_key_env")
    if api_base_url and not os.environ.get(orch["api_key_env"]):
        print(f"FAILED: {orch['api_key_env']} is not set in the environment — "
              f"export it before running this config.")
        return

    if raw_port is not None:
        if cfg.get("framework") == "omlx":
            print("\n--- stop any prior isolated oMLX server ---")
            run(["bash", str(REPO / "runner" / "stop_omlx_server.sh")])
        print("\n--- unload any existing candidate backend ---")
        run(["bash", str(REPO / "runner" / "unload_all.sh")])

        # reset_bench_profile.sh exists specifically to prevent session/
        # memory state leaking from one candidate model's test batch into
        # the next, but was never actually called anywhere (3rd
        # adversarial review, low finding) — the exact "starting a new
        # candidate model's test batch" moment its own header describes.
        # Best-effort like unload_all.sh above (not gating this run on its
        # exit code) since a missing bench profile shouldn't abort an
        # otherwise-working config.
        print("\n--- reset bench hermes profile session/memory state ---")
        run(["bash", str(REPO / "runner" / "reset_bench_profile.sh")])

        print("\n--- launch candidate server ---")
        alias = f"bench-{config_hash}" if framework.startswith("llama.cpp") else None
        cmd = server_command(cfg, alias=alias)
        log_file = f"/tmp/bench_{config_path.parent.name}_{config_path.stem}_server.log"
        print(f"(backgrounded, log: {log_file})")
        # The file object is closed right after Popen() returns (adversarial
        # review finding L2: these were never closed at all) — safe to do
        # immediately since Popen dup()s the fd into the child before
        # returning; the child keeps its own copy independent of this
        # process's handle.
        with open(log_file, "w") as f:
            server_proc = subprocess.Popen(
                cmd, shell=True, cwd=str(REPO),
                stdout=f, stderr=subprocess.STDOUT,
            )

        if not wait_for_health(f"http://127.0.0.1:{raw_port}/v1/models", proc=server_proc):
            print(f"FAILED: backend never became healthy — check {log_file}")
            return
        if not assert_serving_expected_model(raw_port, model, alias=alias, served_model_id=served_model_id):
            print(f"FAILED: refusing to continue against the wrong model — check {log_file} "
                  f"and confirm no stale process survived unload_all.sh (e.g. `lsof -i :{raw_port}`).")
            return
        if not assert_plain_completion(f"http://127.0.0.1:{raw_port}/v1", request_model, timeout=900):
            print(f"FAILED: refusing to benchmark an endpoint that cannot complete a plain request — check {log_file}")
            return

        if needs_proxy:
            print("\n--- launch bench_local_proxy.py ---")
            parser = orch["proxy_parser"]
            upstream = f"http://127.0.0.1:{raw_port}"
            proxy_log = f"/tmp/bench_proxy_{proxy_port}.log"
            proxy_env = os.environ.copy()
            proxy_env.update({
                "BENCH_TOOL_PARSER": parser,
                "BENCH_PROXY_UPSTREAM": upstream,
                "BENCH_PROXY_PORT": str(proxy_port),
            })
            with open(proxy_log, "w") as f:
                proxy_proc = subprocess.Popen(
                    [sys.executable, str(REPO / "runner" / "bench_local_proxy.py")],
                    cwd=str(REPO), env=proxy_env,
                    stdout=f, stderr=subprocess.STDOUT,
                )
            if not wait_for_health(f"http://127.0.0.1:{proxy_port}/healthz", timeout=30, proc=proxy_proc):
                print(f"FAILED: proxy never became healthy — check {proxy_log}")
                return
            if not assert_proxy_matches(proxy_port, parser, upstream):
                print(f"FAILED: refusing to continue against a proxy pointed at the wrong "
                      f"parser/upstream — check {proxy_log} and confirm no stale proxy process "
                      f"survived unload_all.sh (e.g. `lsof -i :{proxy_port}`).")
                return

    base_url = api_base_url or f"http://127.0.0.1:{proxy_port if needs_proxy else raw_port}/v1"

    if stage == "all" and viable in ("full", "sanity_and_hermes_ops_only", "sanity_only"):
        print("\n--- sanity (fail-fast gate) ---")
        with tempfile.TemporaryDirectory() as td:
            summary_path = Path(td) / "sanity_summary.json"
            proc = run([sys.executable, str(REPO / "runner" / "run_prompt_suite.py"),
                        "--suite", "sanity", "--base-url", base_url, "--model", model,
                        "--request-model", request_model, "--framework", framework, "--config", str(config_path),
                        "--trials", str(trials), "--summary-out", str(summary_path)])
            # Read THIS invocation's own rows, not "whatever's at the tail
            # of the shared log" — a crashed/misconfigured subprocess used
            # to leave last_n_rows(2) silently reading the PREVIOUS
            # config's rows, which could pass a gate for a model that
            # never actually answered a prompt (adversarial review finding
            # H3). A missing/unparseable summary is treated the same as a
            # sanity-basic failure: stop, don't guess.
            if proc.returncode != 0 or not summary_path.exists():
                print(f"\n!!! sanity suite subprocess failed (returncode={proc.returncode}) "
                      f"— not viable. Stopping here.")
                _leaderboard()
                return
            try:
                sanity_rows = json.loads(summary_path.read_text())
            except (json.JSONDecodeError, OSError) as e:
                print(f"\n!!! could not read sanity summary ({e}) — not viable. Stopping here.")
                _leaderboard()
                return
        # harness_error rows excluded here (3rd adversarial review, finding
        # CR3-6): a harness crash (e.g. an npm ci network blip) is not
        # evidence about the MODEL at all, but before this fix it was
        # indistinguishable from a genuine failed trial to _majority_pass —
        # a flaky CI-adjacent hiccup could flip a viable model's gate to
        # "not viable" for a reason that has nothing to do with it.
        basic_rows = [r for r in sanity_rows if r["task_id"] == "sanity-basic" and not r.get("harness_error")]
        if not basic_rows or not _majority_pass(basic_rows):
            print(f"\n!!! {model} FAILED sanity-basic — not viable. Stopping here.")
            _leaderboard()
            return
        tool_rows = [r for r in sanity_rows if r["task_id"] == "sanity-tool" and not r.get("harness_error")]
        if viable == "sanity_only" or not tool_rows or not _majority_pass(tool_rows):
            print("\nsanity-tool failed (or this config is sanity_only) — skipping hermes_ops/coding.")
            _leaderboard()
            return

    if stage == "all" and viable in ("full", "sanity_and_hermes_ops_only"):
        print("\n--- hermes_ops ---")
        with tempfile.TemporaryDirectory() as td:
            summary_path = Path(td) / "hermes_ops_summary.json"
            run([sys.executable, str(REPO / "runner" / "run_prompt_suite.py"),
                 "--suite", "hermes_ops", "--base-url", base_url, "--model", model,
                 "--request-model", request_model, "--framework", framework, "--config", str(config_path),
                 "--trials", str(trials), "--summary-out", str(summary_path)])
            tps_values = _hermes_ops_tps_values(summary_path)

        # Speed gate (fail-fast, before the coding suite): a config whose
        # hermes_ops run averages under MIN_HERMES_OPS_TOKENS_PER_SECOND is
        # too slow to be a practical Hermes backend regardless of
        # correctness — skip the coding suite (typically far more
        # expensive: real builds + multi-turn agentic loops) rather than
        # spend that time confirming an outcome the hermes_ops data
        # already answers. A missing/unreadable summary does NOT fail the
        # gate (see _hermes_ops_tps_values) — a harness crash isn't
        # evidence the model is slow.
        if tps_values:
            avg_tps = mean(tps_values)
            if avg_tps < MIN_HERMES_OPS_TOKENS_PER_SECOND:
                _record_speed_gate_failure(model, framework, config_path, config_hash, tps_values, avg_tps)
                print(f"\n!!! {model} ({framework}) hermes_ops averaged {avg_tps:.2f} tok/s "
                      f"({tps_values}) — below the {MIN_HERMES_OPS_TOKENS_PER_SECOND} tok/s "
                      f"viability cutoff. Too slow to be practical. Skipping the coding suite. "
                      f"Stopping here.")
                _leaderboard()
                return

    if stage in ("all", "coding") and viable in ("full", "coding_only") and hermes_provider:
        if coding_suites:
            # Adversarial review finding H1: the coding "suite" was
            # structurally just ONE task (kiem_mini-feature) — hearth_mini,
            # kipclip_mini, and every debug/test-writing task never ran
            # against any model. Opt-in via --coding-suites so the default
            # --all sweep's runtime/historical comparability doesn't change
            # underneath existing results.
            for suite in coding_suites:
                print(f"\n--- coding suite: {suite} (every task) ---")
                run([sys.executable, str(REPO / "runner" / "run_fixture_suite.py"),
                     "--suite", suite,
                     "--hermes-provider", hermes_provider, "--hermes-model", request_model,
                     "--log-model", model, "--framework", framework, "--config", str(config_path),
                     "--trials", str(trials)])
        else:
            print(f"\n--- coding spot-check ({CODING_SPOTCHECK_TASK}) ---")
            run([sys.executable, str(REPO / "runner" / "run_fixture_suite.py"),
                 "--suite", CODING_SPOTCHECK_SUITE, "--only-task", CODING_SPOTCHECK_TASK,
                 "--hermes-provider", hermes_provider, "--hermes-model", request_model,
                 "--log-model", model, "--framework", framework, "--config", str(config_path),
                 "--trials", str(trials)])
    elif stage in ("all", "coding") and viable in ("full", "coding_only"):
        print("\n(coding spot-check skipped — no hermes_provider registered for this config)")

    # Deliberately no teardown here — the NEXT config's own run_one() (in
    # --all mode) already calls unload_all.sh at its start, so a second
    # call here is pure redundancy (and cocore's bounce mechanism errors
    # noisily, if harmlessly, when called twice in a row with nothing
    # restored in between). For a single --config run, leaving the server
    # up matches this script's original behavior — useful if you want to
    # keep poking at the same model afterward. Run
    # runner/restore_local_backends.sh manually when you're done for the
    # day to bring back cocore/hermes's own local fallback.
    _leaderboard()


def run_one(config_path: Path, trials: int = 1, coding_suites=None, stage="all"):
    """Run one config and always tear down the isolated oMLX process.

    The implementation has many deliberate fail-fast returns.  Keeping cleanup
    in this outer wrapper ensures an identity, load, completion, sanity, or
    tool failure cannot strand a Metal model or stale port 8020 process.
    Historical backends retain their original single-config lifecycle.
    """
    try:
        return _run_one_impl(
            config_path, trials=trials, coding_suites=coding_suites, stage=stage
        )
    finally:
        try:
            cfg = yaml.safe_load(config_path.read_text()) or {}
        except (OSError, yaml.YAMLError):
            cfg = {}
        if cfg.get("framework") == "omlx":
            run(["bash", str(REPO / "runner" / "stop_omlx_server.sh")])


def _leaderboard():
    run([sys.executable, str(REPO / "runner" / "build_leaderboard.py")])


def sweep_stale_run_dirs(min_age_seconds=3600):
    """Remove leftover runner/runs/tmp*/ directories from a killed run
    (adversarial review finding L1) — found one live: a full git-initialized
    fixture copy from a task that never got to clean up its own
    TemporaryDirectory context manager. Harmless (gitignored) but
    accumulates indefinitely otherwise. Only sweeps directories older than
    min_age_seconds (default 1h, comfortably longer than any real task
    takes) so this can never race a genuinely concurrent run's own
    in-progress temp dir."""
    runs_root = REPO / "runner" / "runs"
    if not runs_root.is_dir():
        return
    now = time.time()
    for child in runs_root.iterdir():
        if child.is_dir() and (now - child.stat().st_mtime) > min_age_seconds:
            shutil.rmtree(child, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser()
    group = ap.add_mutually_exclusive_group(required=True)
    group.add_argument("--config", help="path to one configs/<model>/<backend>.yaml")
    group.add_argument("--all", action="store_true", help="run every configs/*/*.yaml in sequence")
    ap.add_argument("--trials", type=int, default=1,
                     help="run each task N times per config (default 1) — see "
                          "run_fixture_suite.py's --trials help (adversarial review "
                          "finding C5: single-trial temperature=0 results aren't reliably "
                          "reproducible on MLX/Metal)")
    ap.add_argument("--coding-suites", default=None,
                     help="comma-separated tasks/<suite>.yaml names (e.g. "
                          "'kiem_mini,hearth_mini,kipclip_mini') to run EVERY task from, "
                          "instead of the single kiem_mini-feature spot-check this repo has "
                          "run by default until now (adversarial review finding H1: "
                          "hearth_mini/kipclip_mini and every debug/test-writing task had "
                          "never been run against any model). Opt-in — omitting this leaves "
                          "--all's runtime and existing results' comparability unchanged.")
    ap.add_argument("--framework", default=None,
                    help="with --all, run only configs whose top-level framework matches "
                         "this value (for example: omlx); keeps an oMLX sweep from "
                         "re-running every historical llama.cpp/vllm-mlx config")
    ap.add_argument("--stage", choices=("all", "coding"), default="all",
                    help="run the normal full config matrix (all), or only the coding "
                         "fixture stage after a harness repair (coding); identity, cold "
                         "load, and plain-completion gates still run")
    args = ap.parse_args()
    coding_suites = [s.strip() for s in args.coding_suites.split(",")] if args.coding_suites else None

    # After parse_args(), not before (adversarial review finding L-7) — this
    # used to run before argument parsing at all, so it fired on --help and
    # on invalid arguments too, not just a real invocation.
    sweep_stale_run_dirs()

    if args.all:
        # Only files with an orchestration: block are real benchmark
        # configs — a stray non-config .yaml dropped into a model
        # directory used to become a silent, unintended benchmark run
        # (adversarial review finding L3).
        candidates = sorted(REPO.glob("configs/*/*.yaml"))
        configs = []
        for c in candidates:
            try:
                loaded = yaml.safe_load(c.read_text())
            except yaml.YAMLError:
                continue
            if (isinstance(loaded, dict) and "orchestration" in loaded
                    and (args.framework is None or loaded.get("framework") == args.framework)):
                configs.append(c)
        print(f"Running {len(configs)} configs...")
        for i, config_path in enumerate(configs, 1):
            print(f"\n\n########## [{i}/{len(configs)}] {config_path} ##########")
            run_one(
                config_path, trials=args.trials, coding_suites=coding_suites,
                stage=args.stage,
            )
    else:
        run_one(
            Path(args.config), trials=args.trials, coding_suites=coding_suites,
            stage=args.stage,
        )


if __name__ == "__main__":
    main()
