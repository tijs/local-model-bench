"""Bounded request/residency diagnostic; never writes canonical benchmark rows."""

import argparse
import json
import os
import pathlib
import subprocess
import time
import urllib.request

p = argparse.ArgumentParser()
p.add_argument("out")
p.add_argument("--binary", required=True)
p.add_argument("--cache", choices=["true", "false"], required=True)
p.add_argument("--count", type=int, default=32)
p.add_argument("--repeat-last", type=int, default=0)
p.add_argument("--prefix-budget", type=int)
p.add_argument("--native-probes", action="store_true")
a = p.parse_args()
out = pathlib.Path(a.out)
out.mkdir(parents=True, exist_ok=True)
argv = [
    a.binary,
    "--model-dir",
    "/Users/tijs/.local/share/local-model-bench/mei-models/Flint-40B-A2.5B-JANGH2-mei-adapter",
    "--served-model-id",
    "OsaurusAI/Flint-40B-A2.5B-JANGH2",
    "--host",
    "127.0.0.1",
    "--port",
    "8024",
    "--context-cap",
    "65536",
    "--prefill-step-size",
    "64",
    "--max-tokens",
    "8192",
    "--temperature",
    "1",
    "--top-p",
    "0.95",
    "--top-k",
    "20",
    "--emit-reasoning",
    "true",
    "--cache-reuse",
    a.cache,
    "--cache-limit-bytes",
    "536870912",
    "--compiled-decode",
    "false",
    "--enable-flint",
    "true",
    "--enable-flint-jangh",
    "true",
    "--load-mmap",
    "true",
    "--request-log",
    str(out / "requests.jsonl"),
]
if a.prefix_budget is not None:
    argv += ["--prefix-cache-limit-bytes", str(a.prefix_budget)]
(out / "server-argv.json").write_text(json.dumps(argv, indent=2))
env = os.environ.copy()
env.pop("MLXPRESS", None)
env.pop("JANGPRESS", None)
env.update(VMLX_ENABLE_UNSAFE_COMPILE="0", VMLX_FUSED_GATE_UP_CACHE_LIMIT_BYTES="0")


def get(path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        "http://127.0.0.1:8024" + path,
        data=data,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.load(r)


server = None
try:
    with (out / "server.log").open("w") as log:
        server = subprocess.Popen(argv, stdout=log, stderr=subprocess.STDOUT, env=env)
        (out / "server.pid").write_text(str(server.pid))
        for _ in range(120):
            if server.poll() is not None:
                raise RuntimeError("server exited before health")
            try:
                get("/v1/models")
                break
            except OSError:
                time.sleep(1)
        else:
            raise RuntimeError("health timeout")
        initial = get("/v1/mei/status")
        (out / "initial-status.json").write_text(json.dumps(initial, indent=2))
        print("LOAD", initial["memory"], flush=True)
        with (out / "samples.jsonl").open("w", buffering=1) as samples:
            for i in range(a.count + a.repeat_last):
                system = (
                    "You are a helpful assistant. The following is neutral diagnostic context. "
                    + (
                        "A small library keeps books on shelves and lends them to readers. "
                        * 80
                    )
                    + f" Diagnostic request {min(i, a.count - 1)}."
                )
                body = {
                    "model": "OsaurusAI/Flint-40B-A2.5B-JANGH2",
                    "messages": [
                        {"role": "system", "content": system},
                        {
                            "role": "user",
                            "content": "What is 17 + 25? Answer concisely.",
                        },
                    ],
                    "temperature": 1.0,
                    "top_p": 0.95,
                    "top_k": 20,
                    "max_tokens": 128,
                    "stream": False,
                }
                started = time.monotonic()
                resp = get("/v1/chat/completions", body)
                status = get("/v1/mei/status")
                row = {
                    "index": i,
                    "response": resp,
                    "status": status,
                    "wall_seconds": time.monotonic() - started,
                }
                samples.write(json.dumps(row) + "\n")
                print(
                    i,
                    status["memory"]["activeBytes"],
                    status.get("cache"),
                    resp.get("usage"),
                    flush=True,
                )
        if a.native_probes:
            subprocess.run(
                [
                    "uv",
                    "run",
                    "--locked",
                    "python",
                    "runner/probe_mei.py",
                    "--model",
                    "OsaurusAI/Flint-40B-A2.5B-JANGH2",
                    "--skip-context",
                    "--output",
                    str(out / "native-probe.json"),
                ],
                check=True,
            )
            subprocess.run(
                [
                    "uv",
                    "run",
                    "--locked",
                    "python",
                    "artifacts/flint-memory-20261026/cache_replay_probe.py",
                    "--output",
                    str(out / "cache-replay.json"),
                ],
                check=True,
            )
        (out / "final-status.json").write_text(
            json.dumps(get("/v1/mei/status"), indent=2)
        )
finally:
    if server is not None and server.poll() is None:
        server.terminate()
        try:
            server.wait(timeout=15)
        except subprocess.TimeoutExpired:
            server.kill()
            server.wait()
