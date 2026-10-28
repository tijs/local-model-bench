"""Bounded same-quant cache diagnostic; never writes scored benchmark rows."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import signal
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "runner"))
from bench_common import MIN_FREE_DISK_GB_BEFORE_LAUNCH, REPO
from run_bench import mei_stop_command, server_command, wait_for_health
from run_standin_suite import admission, committed_config, verify_endpoint_identity
from standin_domain import TOOLS


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    cfg, config_bytes = committed_config(args.config)
    assert cfg.get("diagnostic_only") is True
    assert cfg.get("diagnostic_admission") == "seeded-nonstream-v1"
    assert shutil.disk_usage(REPO).free >= MIN_FREE_DISK_GB_BEFORE_LAUNCH * 1024**3
    for port in (8024, 8017):
        with socket.socket() as sock:
            assert sock.connect_ex(("127.0.0.1", port)) != 0, f"port {port} occupied"
    args.out.mkdir(parents=True, exist_ok=False)
    (args.out / "config.yaml").write_bytes(config_bytes)
    (args.out / "provenance.json").write_text(
        json.dumps(
            {
                "runner_git_sha": subprocess.check_output(
                    ["git", "rev-parse", "HEAD"], text=True
                ).strip(),
                "script_sha256": hashlib.sha256(
                    Path(__file__).read_bytes()
                ).hexdigest(),
                "config_sha256": hashlib.sha256(config_bytes).hexdigest(),
            },
            indent=2,
        )
        + "\n"
    )
    base = cfg["benchmark_endpoint"]
    model = cfg["orchestration"]["served_model_id"]

    def seeded_client(base_url, model, messages, tools, **kwargs):
        # The diagnostic uses one prospectively chosen seed and HTTP mode for
        # both admission and replay. All stage/code/final checks still apply.
        body = json.dumps(
            {
                "model": model,
                "messages": messages,
                "tools": tools,
                "temperature": 1.0,
                "top_p": 0.95,
                "top_k": 20,
                "seed": 173,
                "max_tokens": kwargs["max_tokens"],
                "stream": False,
            }
        ).encode()
        request = urllib.request.Request(
            base_url + "/chat/completions",
            data=body,
            headers={"Content-Type": "application/json"},
        )
        start = time.monotonic()
        with urllib.request.urlopen(request, timeout=kwargs["timeout"]) as reply:
            response = json.load(reply)
        return response, None, time.monotonic() - start

    original = REPO / "results/standin/runs/20261028T065739Z-cce13341"
    inputs = {}
    for name in ("capture-multipart", "private-copy"):
        trace = json.loads((original / f"{name}-trial1.json").read_text())
        # Multipart replays the exact prefix before the truncated assistant.
        # Private-copy replays its initial user request, before the search loop.
        messages = (
            trace["messages"][:-1]
            if name == "capture-multipart"
            else trace["messages"][:2]
        )
        inputs[name] = {
            "model": model,
            "messages": messages,
            "tools": TOOLS,
            "temperature": 1.0,
            "top_p": 0.95,
            "top_k": 20,
            "seed": 173,
            "max_tokens": 1536,
            "stream": False,
        }
    (args.out / "inputs.json").write_text(json.dumps(inputs, indent=2) + "\n")
    server = None
    try:
        with (args.out / "server-launch.log").open("w") as log:
            server = subprocess.Popen(
                ["bash", "-c", server_command(cfg)],
                stdout=log,
                stderr=subprocess.STDOUT,
            )
            assert wait_for_health(base + "/models", timeout=300, proc=server)
            verify_endpoint_identity(base, model)
            with urllib.request.urlopen(base + "/mei/status", timeout=10) as reply:
                status = json.load(reply)
            (args.out / "status.json").write_text(json.dumps(status, indent=2) + "\n")
            assert status["cacheReuse"] is cfg["diagnostic_cache_reuse"]
            gate = admission(
                seeded_client,
                base,
                model,
                cfg["generation_profiles"]["model_card"],
            )
            (args.out / "admission.json").write_text(json.dumps(gate, indent=2) + "\n")
            assert gate["status"] == "passed", gate["status"]
            with (args.out / "replays.jsonl").open("w", buffering=1) as output:
                for name in (
                    "capture-multipart",
                    "private-copy",
                    "capture-multipart",
                    "private-copy",
                ):
                    body = json.dumps(inputs[name]).encode()
                    request = urllib.request.Request(
                        base + "/chat/completions",
                        data=body,
                        headers={"Content-Type": "application/json"},
                    )
                    start = time.monotonic()
                    with urllib.request.urlopen(request, timeout=120) as reply:
                        response = json.load(reply)
                    row = {
                        "name": name,
                        "input_sha256": hashlib.sha256(body).hexdigest(),
                        "seconds": time.monotonic() - start,
                        "response": response,
                    }
                    output.write(json.dumps(row) + "\n")
                    print(
                        name,
                        response["choices"][0]["finish_reason"],
                        response["usage"],
                        flush=True,
                    )
    finally:
        subprocess.run(mei_stop_command(cfg), check=True, timeout=45)
        if server is not None:
            try:
                server.wait(timeout=10)
            except subprocess.TimeoutExpired:
                server.terminate()
                server.wait(timeout=10)
        runtime = Path(cfg["required_runner_environment"]["MEI_RUNTIME_BASE"])
        shutil.copytree(runtime / "logs", args.out / "runtime-logs")


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(143))
    main()
