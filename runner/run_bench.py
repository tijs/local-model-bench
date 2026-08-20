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
import subprocess
import sys
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


def wait_for_health(url, timeout=600):
    print(f"Waiting for {url} to respond (timeout {timeout}s)...")
    start = time.time()
    while time.time() - start < timeout:
        try:
            with urllib.request.urlopen(url, timeout=3) as resp:
                if resp.status == 200:
                    print(f"  healthy after {time.time() - start:.1f}s")
                    return True
        except (urllib.error.URLError, ConnectionError, TimeoutError, OSError):
            pass
        time.sleep(3)
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


def last_n_rows(n):
    log_path = REPO / "results" / "log.jsonl"
    lines = log_path.read_text().splitlines()
    return [json.loads(l) for l in lines[-n:]]


def run_one(config_path: Path, skip_teardown=False):
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

    if raw_port is not None:
        print("\n--- unload any existing candidate backend ---")
        run(["bash", str(REPO / "runner" / "unload_all.sh")])

        print("\n--- launch candidate server ---")
        cmd = server_command(cfg)
        log_file = f"/tmp/bench_{config_path.parent.name}_{config_path.stem}_server.log"
        print(f"(backgrounded, log: {log_file})")
        subprocess.Popen(
            cmd, shell=True, cwd=str(REPO),
            stdout=open(log_file, "w"), stderr=subprocess.STDOUT,
        )

        if not wait_for_health(f"http://127.0.0.1:{raw_port}/v1/models"):
            print(f"FAILED: backend never became healthy — check {log_file}")
            return

        if needs_proxy:
            print("\n--- launch bench_local_proxy.py ---")
            parser = orch["proxy_parser"]
            proxy_log = f"/tmp/bench_proxy_{proxy_port}.log"
            env_cmd = (
                f"BENCH_TOOL_PARSER={parser} "
                f"BENCH_PROXY_UPSTREAM=http://127.0.0.1:{raw_port} "
                f"BENCH_PROXY_PORT={proxy_port} "
                f"{COCORE_PY} {REPO / 'runner' / 'bench_local_proxy.py'}"
            )
            subprocess.Popen(
                env_cmd, shell=True, cwd=str(REPO),
                stdout=open(proxy_log, "w"), stderr=subprocess.STDOUT,
            )
            if not wait_for_health(f"http://127.0.0.1:{proxy_port}/healthz", timeout=30):
                print(f"FAILED: proxy never became healthy — check {proxy_log}")
                return

    base_url = f"http://127.0.0.1:{proxy_port if needs_proxy else raw_port}/v1"

    if viable in ("full", "sanity_and_hermes_ops_only", "sanity_only"):
        print("\n--- sanity (fail-fast gate) ---")
        run([COCORE_PY, str(REPO / "runner" / "run_prompt_suite.py"),
             "--suite", "sanity", "--base-url", base_url, "--model", model,
             "--backend", backend, "--config", str(config_path)])
        sanity_rows = last_n_rows(2)
        basic = next((r for r in sanity_rows if r["task_id"] == "sanity-basic"), None)
        if basic and not basic["pass"]:
            print(f"\n!!! {model} FAILED sanity-basic — not viable. Stopping here.")
            _teardown(needs_proxy, skip_teardown)
            _leaderboard()
            return
        tool_row = next((r for r in sanity_rows if r["task_id"] == "sanity-tool"), None)
        if viable == "sanity_only" or (tool_row and not tool_row["pass"]):
            print("\nsanity-tool failed (or this config is sanity_only) — skipping hermes_ops/coding.")
            _teardown(needs_proxy, skip_teardown)
            _leaderboard()
            return

    if viable in ("full", "sanity_and_hermes_ops_only"):
        print("\n--- hermes_ops ---")
        run([COCORE_PY, str(REPO / "runner" / "run_prompt_suite.py"),
             "--suite", "hermes_ops", "--base-url", base_url, "--model", model,
             "--backend", backend, "--config", str(config_path)])

    if viable in ("full", "coding_only") and hermes_provider:
        print(f"\n--- coding spot-check ({CODING_SPOTCHECK_TASK}) ---")
        run([COCORE_PY, str(REPO / "runner" / "run_fixture_suite.py"),
             "--suite", CODING_SPOTCHECK_SUITE, "--only-task", CODING_SPOTCHECK_TASK,
             "--hermes-provider", hermes_provider, "--hermes-model", model,
             "--backend", backend, "--config", str(config_path)])
    elif viable in ("full", "coding_only"):
        print("\n(coding spot-check skipped — no hermes_provider registered for this config)")

    _teardown(needs_proxy, skip_teardown)
    _leaderboard()


def _teardown(needs_proxy, skip_teardown):
    if skip_teardown:
        return
    print("\n--- teardown ---")
    run(["bash", str(REPO / "runner" / "unload_all.sh")])


def _leaderboard():
    run([COCORE_PY, str(REPO / "runner" / "build_leaderboard.py")])


def main():
    ap = argparse.ArgumentParser()
    group = ap.add_mutually_exclusive_group(required=True)
    group.add_argument("--config", help="path to one configs/<model>/<backend>.yaml")
    group.add_argument("--all", action="store_true", help="run every configs/*/*.yaml in sequence")
    args = ap.parse_args()

    if args.all:
        configs = sorted(REPO.glob("configs/*/*.yaml"))
        print(f"Running {len(configs)} configs...")
        for i, config_path in enumerate(configs, 1):
            print(f"\n\n########## [{i}/{len(configs)}] {config_path} ##########")
            run_one(config_path)
    else:
        run_one(Path(args.config))


if __name__ == "__main__":
    main()
