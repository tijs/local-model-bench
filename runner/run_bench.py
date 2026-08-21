#!/usr/bin/env python3
"""
The single entry point for this whole benchmark: run one model+backend
config, or every config in the repo, unattended.

Requires PyYAML — run with cocore's python:
  /Users/tijs/.cocore/python/bin/python runner/run_bench.py --config configs/<model>/<backend>.yaml
  /Users/tijs/.cocore/python/bin/python runner/run_bench.py --all

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
  6. hermes_ops suite (unless orchestration.viable says to skip it)
  7. the one coding-suite spot-check, kiem_mini-feature (unless
     orchestration.viable says to skip it, or hermes_provider is unset)
  8. regenerate results/LEADERBOARD.md
  9. tear down (unload_all.sh again) before moving to the next config,
     if running --all

`orchestration.viable` controls which of steps 5-7 run:
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
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
COCORE_PY = "/Users/tijs/.cocore/python/bin/python"
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


def _base_repo_name(model_id):
    """Strip a ':quant' suffix, e.g. 'foo/Bar-GGUF:Q4_K_M' -> 'foo/Bar-GGUF'."""
    return model_id.split(":")[0]


def assert_serving_expected_model(raw_port, expected_model):
    """Confirm the server actually answering raw_port is serving the model
    THIS config expects, not a stale process left over from a previous
    config (adversarial review finding H2: wait_for_health only checks
    that *something* answers 200 — a leftover server on the same port
    would pass that check while silently serving the wrong model)."""
    url = f"http://127.0.0.1:{raw_port}/v1/models"
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            data = json.loads(resp.read())
    except (urllib.error.URLError, OSError, ValueError) as e:
        print(f"FAILED: could not verify served model via {url}: {e}")
        return False
    served_ids = [m.get("id", "") for m in data.get("data", [])]
    expected = _base_repo_name(expected_model)
    if any(expected in sid or sid in expected for sid in served_ids if sid):
        return True
    print(f"FAILED: {url} is serving {served_ids!r}, expected something matching {expected!r} "
          f"— a stale server from a previous config may still be bound to this port.")
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


def server_command(cfg):
    """benchmark_launch_command sometimes documents a follow-up proxy step
    inline (as literal shell text, not a shell comment) — that's for a
    human reading the file, not something to execute as one blob. Only
    take the lines up to the first mention of bench_local_proxy.py."""
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
    return text


def run_one(config_path: Path, trials: int = 1):
    cfg = yaml.safe_load(config_path.read_text())
    orch = cfg.get("orchestration")
    if not orch:
        sys.exit(f"{config_path} has no orchestration: block — see configs/README.md")

    model = cfg["model"]
    backend = cfg["backend"]
    viable = orch.get("viable", "full")

    print(f"\n{'=' * 70}\n{model} ({backend}) — {config_path}\nviable={viable}\n{'=' * 70}")

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
        print("\n--- unload any existing candidate backend ---")
        run(["bash", str(REPO / "runner" / "unload_all.sh")])

        print("\n--- launch candidate server ---")
        cmd = server_command(cfg)
        log_file = f"/tmp/bench_{config_path.parent.name}_{config_path.stem}_server.log"
        print(f"(backgrounded, log: {log_file})")
        server_proc = subprocess.Popen(
            cmd, shell=True, cwd=str(REPO),
            stdout=open(log_file, "w"), stderr=subprocess.STDOUT,
        )

        if not wait_for_health(f"http://127.0.0.1:{raw_port}/v1/models", proc=server_proc):
            print(f"FAILED: backend never became healthy — check {log_file}")
            return
        if not assert_serving_expected_model(raw_port, model):
            print(f"FAILED: refusing to continue against the wrong model — check {log_file} "
                  f"and confirm no stale process survived unload_all.sh (e.g. `lsof -i :{raw_port}`).")
            return

        if needs_proxy:
            print("\n--- launch bench_local_proxy.py ---")
            parser = orch["proxy_parser"]
            upstream = f"http://127.0.0.1:{raw_port}"
            proxy_log = f"/tmp/bench_proxy_{proxy_port}.log"
            env_cmd = (
                f"BENCH_TOOL_PARSER={parser} "
                f"BENCH_PROXY_UPSTREAM={upstream} "
                f"BENCH_PROXY_PORT={proxy_port} "
                f"{COCORE_PY} {REPO / 'runner' / 'bench_local_proxy.py'}"
            )
            proxy_proc = subprocess.Popen(
                env_cmd, shell=True, cwd=str(REPO),
                stdout=open(proxy_log, "w"), stderr=subprocess.STDOUT,
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

    if viable in ("full", "sanity_and_hermes_ops_only", "sanity_only"):
        print("\n--- sanity (fail-fast gate) ---")
        with tempfile.TemporaryDirectory() as td:
            summary_path = Path(td) / "sanity_summary.json"
            proc = run([COCORE_PY, str(REPO / "runner" / "run_prompt_suite.py"),
                        "--suite", "sanity", "--base-url", base_url, "--model", model,
                        "--backend", backend, "--config", str(config_path),
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
        basic_rows = [r for r in sanity_rows if r["task_id"] == "sanity-basic"]
        if not basic_rows or not all(r["pass"] for r in basic_rows):
            print(f"\n!!! {model} FAILED sanity-basic — not viable. Stopping here.")
            _leaderboard()
            return
        tool_rows = [r for r in sanity_rows if r["task_id"] == "sanity-tool"]
        if viable == "sanity_only" or not tool_rows or not all(r["pass"] for r in tool_rows):
            print("\nsanity-tool failed (or this config is sanity_only) — skipping hermes_ops/coding.")
            _leaderboard()
            return

    if viable in ("full", "sanity_and_hermes_ops_only"):
        print("\n--- hermes_ops ---")
        run([COCORE_PY, str(REPO / "runner" / "run_prompt_suite.py"),
             "--suite", "hermes_ops", "--base-url", base_url, "--model", model,
             "--backend", backend, "--config", str(config_path),
             "--trials", str(trials)])

    if viable in ("full", "coding_only") and hermes_provider:
        print(f"\n--- coding spot-check ({CODING_SPOTCHECK_TASK}) ---")
        run([COCORE_PY, str(REPO / "runner" / "run_fixture_suite.py"),
             "--suite", CODING_SPOTCHECK_SUITE, "--only-task", CODING_SPOTCHECK_TASK,
             "--hermes-provider", hermes_provider, "--hermes-model", model,
             "--backend", backend, "--config", str(config_path),
             "--trials", str(trials)])
    elif viable in ("full", "coding_only"):
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


def _leaderboard():
    run([COCORE_PY, str(REPO / "runner" / "build_leaderboard.py")])


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
    args = ap.parse_args()

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
            if isinstance(loaded, dict) and "orchestration" in loaded:
                configs.append(c)
        print(f"Running {len(configs)} configs...")
        for i, config_path in enumerate(configs, 1):
            print(f"\n\n########## [{i}/{len(configs)}] {config_path} ##########")
            run_one(config_path, trials=args.trials)
    else:
        run_one(Path(args.config), trials=args.trials)


if __name__ == "__main__":
    main()
