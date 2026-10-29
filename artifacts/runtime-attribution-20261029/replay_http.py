"""Exact archived failure-turn diagnostic. No scored benchmark rows are written."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import signal
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "runner"))
from mei_provenance import verify_mei_runtime
from run_bench import mei_stop_command, server_command, wait_for_health
from run_standin_suite import committed_config, run_task, verify_endpoint_identity
from standin_tasks import cases as task_cases


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    cfg, content = committed_config(args.config)
    assert cfg["diagnostic_only"] is True
    verify_mei_runtime(cfg)
    for port in (8024, 8017):
        with socket.socket() as sock:
            assert sock.connect_ex(("127.0.0.1", port)) != 0
    args.out.mkdir(parents=True, exist_ok=False)
    (args.out / "config.yaml").write_bytes(content)
    cases = json.loads(args.inputs.read_text())
    server = None
    try:
        with (args.out / "launch.log").open("w") as log:
            server = subprocess.Popen(
                ["bash", "-c", server_command(cfg)],
                cwd=ROOT,
                stdout=log,
                stderr=subprocess.STDOUT,
                env=os.environ.copy(),
            )
        base = cfg["benchmark_endpoint"]
        assert wait_for_health(base + "/models", timeout=600, proc=server)
        verify_endpoint_identity(base, cfg["model"])
        (args.out / "runtime-identity.json").write_text(
            json.dumps(verify_mei_runtime(cfg, base_url=base), indent=2) + "\n"
        )
        with (args.out / "responses.jsonl").open("a", buffering=1) as stream:
            for case in cases:
                request = copy.deepcopy(case["request"])
                for repetition in (1, 2):
                    body = json.dumps(request, ensure_ascii=False).encode()
                    req = urllib.request.Request(
                        base + "/chat/completions",
                        data=body,
                        headers={"Content-Type": "application/json"},
                    )
                    started = time.monotonic()
                    with urllib.request.urlopen(req, timeout=180) as reply:
                        response = json.load(reply)
                    stream.write(
                        json.dumps(
                            {
                                "name": case["name"],
                                "repetition": repetition,
                                "request_sha256": hashlib.sha256(body).hexdigest(),
                                "seconds": time.monotonic() - started,
                                "response": response,
                            }
                        )
                        + "\n"
                    )
                    msg = response["choices"][0]["message"]
                    print(
                        case["name"],
                        repetition,
                        response["choices"][0]["finish_reason"],
                        [
                            (c["function"]["name"], c["function"]["arguments"])
                            for c in msg.get("tool_calls") or []
                        ],
                        flush=True,
                    )

        # Natural multi-turn flows exercise real growing-prefix reuse. These
        # diagnostics are saved here only, never appended to benchmark rows.
        def client(base_url, model, messages, tools, **kwargs):
            body = json.dumps(
                {
                    "model": model,
                    "messages": messages,
                    "tools": tools,
                    "temperature": 0,
                    "top_p": 1,
                    "top_k": 0,
                    "max_tokens": kwargs["max_tokens"],
                    "stream": False,
                }
            ).encode()
            req = urllib.request.Request(
                base_url + "/chat/completions",
                data=body,
                headers={"Content-Type": "application/json"},
            )
            started = time.monotonic()
            with urllib.request.urlopen(req, timeout=kwargs["timeout"]) as reply:
                response = json.load(reply)
            return response, None, time.monotonic() - started

        for task in ("capture-ambiguous", "share-preview"):
            case = next(c for c in task_cases() if c.task_id == task)
            trace = run_task(
                case,
                client,
                base,
                cfg["model"],
                {"temperature": 0, "top_p": 1, "top_k": 0},
            )
            (args.out / ("workflow-" + task + ".json")).write_text(
                json.dumps(trace, indent=2) + "\n"
            )
            print("workflow", task, trace["grade"]["failed_checks"], flush=True)
    finally:
        subprocess.run(mei_stop_command(cfg), cwd=ROOT, check=False, timeout=45)
        if server is not None:
            try:
                server.wait(timeout=15)
            except subprocess.TimeoutExpired:
                server.send_signal(signal.SIGTERM)
                server.wait(timeout=15)


if __name__ == "__main__":
    main()
