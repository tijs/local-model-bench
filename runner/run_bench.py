#!/usr/bin/env python3
"""
The single entry point: run the full benchmark (sanity -> hermes_ops -> the
3 coding suites) for one candidate model/backend, unattended. Tijs runs this
one script and watches; nothing else needs to be run by hand.

Requires PyYAML — run with a python that has it:
  /Users/tijs/.cocore/python/bin/python runner/run_bench.py --config configs/<model>/mlx.yaml

What it does, in order:
  1. runner/unload_all.sh          — kill any existing candidate backend
  2. launch benchmark_launch_command from the config (backgrounded)
  3. wait for the backend to answer /v1/models
  4. runner/start_bench_proxy.sh   — start/confirm the tool-call-parsing proxy
  5. runner/reset_bench_profile.sh — fresh hermes session/memory state
  6. sanity suite — fail-fast: if sanity-basic fails, stop here, log
     "not viable", skip everything else for this model+backend
  7. hermes_ops suite
  8. kiem_mini, hearth_mini, kipclip_mini fixture suites
  9. regenerate results/LEADERBOARD.md from results/log.jsonl
  10. print a final summary

KNOWN CAVEAT: the MLX backend shares its underlying engine (vllm_mlx.server,
port 8012) process-for-process with whatever cocore/hermes are already using
for local inference — step 1 kills that. Running this script interrupts
Tijs's live local-model fallback (if in use) for the duration of the run.
Not automated further than the unload/reload itself; see AGENTS.md.
"""
import argparse
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
COCORE_PY = "/Users/tijs/.cocore/python/bin/python"


def run(cmd, **kw):
    print(f"$ {cmd}")
    return subprocess.run(cmd, shell=isinstance(cmd, str), cwd=str(REPO), **kw)


def wait_for_health(url, timeout=180):
    print(f"Waiting for {url} to respond (timeout {timeout}s)...")
    start = time.time()
    while time.time() - start < timeout:
        try:
            with urllib.request.urlopen(url, timeout=3) as resp:
                if resp.status == 200:
                    print(f"  healthy after {time.time() - start:.1f}s")
                    return True
        except (urllib.error.URLError, ConnectionError, TimeoutError):
            pass
        time.sleep(2)
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True, help="path to configs/<model>/<backend>.yaml")
    ap.add_argument("--skip-load", action="store_true", help="assume the backend is already running with the right model")
    args = ap.parse_args()

    config_path = Path(args.config)
    cfg = yaml.safe_load(config_path.read_text())
    model = cfg["model"]
    backend = cfg["backend"]
    provider = f"custom:local-{backend}"
    proxy_port = 8015 if backend == "mlx" else 8016
    base_url = f"http://127.0.0.1:{proxy_port}/v1"
    parser = None
    for s in cfg.get("settings", []):
        if s.get("name") == "tool_call_parser":
            parser = s["value"]
    parser = parser or "lfm"

    print(f"=== local-model-bench: {model} ({backend}) ===")
    print(f"config: {config_path}")
    print(f"provider={provider} base_url={base_url} tool_call_parser={parser}\n")

    if not args.skip_load:
        print("--- Step 1: unload any existing candidate backend ---")
        run(["bash", str(REPO / "runner" / "unload_all.sh")])

        print("\n--- Step 2: load candidate model ---")
        launch_cmd = cfg["benchmark_launch_command"].strip()
        print(f"$ {launch_cmd}  (backgrounded)")
        subprocess.Popen(
            launch_cmd, shell=True, cwd=str(REPO),
            stdout=open("/tmp/bench_model_server.log", "w"), stderr=subprocess.STDOUT,
        )

        print("\n--- Step 3: wait for backend health ---")
        upstream_port = 8012 if backend == "mlx" else 8013
        if not wait_for_health(f"http://127.0.0.1:{upstream_port}/v1/models"):
            sys.exit(f"FAILED: backend never became healthy — check /tmp/bench_model_server.log")

    print("\n--- Step 4: start tool-call-parsing proxy ---")
    upstream_port = 8012 if backend == "mlx" else 8013
    run(["bash", str(REPO / "runner" / "start_bench_proxy.sh"), str(upstream_port), str(proxy_port), parser], check=True)

    print("\n--- Step 5: reset bench profile session/memory state ---")
    run(["bash", str(REPO / "runner" / "reset_bench_profile.sh")], check=True)

    print("\n--- Step 6: sanity tier (fail-fast gate) ---")
    sanity = run(
        [COCORE_PY, str(REPO / "runner" / "run_prompt_suite.py"),
         "--suite", "sanity", "--base-url", base_url, "--model", model,
         "--backend", backend, "--config", str(config_path)],
    )
    log_path = REPO / "results" / "log.jsonl"
    sanity_rows = [l for l in log_path.read_text().splitlines()[-2:]]
    import json
    if any(not json.loads(r)["pass"] for r in sanity_rows if json.loads(r)["task_id"] == "sanity-basic"):
        print(f"\n!!! {model} FAILED sanity-basic — not viable for this use case. Stopping here.")
        print_leaderboard()
        return

    print("\n--- Step 7: hermes_ops suite ---")
    run(
        [COCORE_PY, str(REPO / "runner" / "run_prompt_suite.py"),
         "--suite", "hermes_ops", "--base-url", base_url, "--model", model,
         "--backend", backend, "--config", str(config_path)],
    )

    print("\n--- Step 8: coding suites ---")
    for suite in ["kiem_mini", "hearth_mini", "kipclip_mini"]:
        run(
            [COCORE_PY, str(REPO / "runner" / "run_fixture_suite.py"),
             "--suite", suite, "--hermes-provider", provider, "--hermes-model", model,
             "--backend", backend, "--config", str(config_path)],
        )

    print("\n--- Step 9: leaderboard ---")
    print_leaderboard()


def print_leaderboard():
    run([COCORE_PY, str(REPO / "runner" / "build_leaderboard.py")])


if __name__ == "__main__":
    main()
