import json
import os
import shutil
import signal
import subprocess
import sys
import threading
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, "runner")
from supervise_bench import gate_reason, sample

root = Path("artifacts/mei-version-speed-20261105")
model = "/Users/tijs/.local/share/local-model-bench/mei-models/Qwen3.6-35B-A3B-4bit-textonly"
model_id = "Tostibrown/Qwen3.6-35B-A3B-4bit-textonly"
prompts = json.loads(
    Path(
        "artifacts/mei-stable-qwen-unused-boundary-clean1-20261104/prompts.json"
    ).read_text()
)
bins = {
    "0.8.0": "/tmp/mei-release-comparison-20261105/v08/mei-0.8.0-macos-arm64/bin/mei",
    "0.9.0": "/tmp/mei-release-comparison-20261105/v09/mei-0.9.0-macos-arm64/bin/mei",
    "0.10.0": "/opt/homebrew/Cellar/mei/0.10.0/libexec/mei",
}
initial = sample(os.getpid(), root)
assert (
    initial["kernel_pressure_level"] == 1
    and initial["disk_free_bytes"] > 10 * 1024**3
    and initial["swap_used_mib"] < 16384
)
for ver, binary in bins.items():
    out = root / ver
    out.mkdir(exist_ok=False)
    kv = out / "kv"
    kv.mkdir()
    log = (out / "server.log").open("w")
    args = [
        binary,
        "--model-dir",
        model,
        "--served-model-id",
        model_id,
        "--port",
        "8024",
        "--context-cap",
        "65536",
        "--prefill-step-size",
        "256",
        "--max-tokens",
        "8192",
        "--cache-limit-bytes",
        "536870912",
        "--compiled-decode",
        "false",
        "--cache-reuse",
        "true",
        "--kv-cache-dir",
        str(kv.resolve()),
    ]
    (out / "command.json").write_text(json.dumps(args, indent=2))
    proc = subprocess.Popen(
        args, stdout=log, stderr=subprocess.STDOUT, start_new_session=True
    )
    stop = threading.Event()
    danger = []

    def watch(stop=stop, proc=proc, out=out, danger=danger):
        warnings = 0
        while not stop.wait(5):
            try:
                p = sample(proc.pid, root)
            except Exception as exc:  # noqa: BLE001 - fail closed on monitor errors
                danger.append(f"monitor failed: {exc}")
                os.killpg(proc.pid, signal.SIGTERM)
                return
            warnings = warnings + 1 if p["kernel_pressure_level"] >= 2 else 0
            with (out / "resources.jsonl").open("a") as f:
                f.write(json.dumps(p) + "\n")
            why = gate_reason(p, initial, 0, warnings, percent_stop=False)
            if why:
                danger.append(why)
                os.killpg(proc.pid, signal.SIGTERM)
                return

    t = threading.Thread(target=watch, daemon=True)
    t.start()
    try:
        deadline = time.monotonic() + 600
        while time.monotonic() < deadline:
            if proc.poll() is not None:
                raise RuntimeError("server exited before health")
            try:
                with urllib.request.urlopen(
                    "http://127.0.0.1:8024/v1/models", timeout=2
                ) as r:
                    if r.status == 200:
                        break
            except (OSError, TimeoutError):
                time.sleep(2)
        else:
            raise TimeoutError("health")
        for phase in ("short", "loaded"):
            for n in range(3):
                body = json.dumps(
                    {
                        "model": model_id,
                        "prompt": prompts[phase],
                        "temperature": 0,
                        "top_p": 1,
                        "max_tokens": 128,
                        "stream": False,
                    }
                ).encode()
                req = urllib.request.Request(
                    "http://127.0.0.1:8024/v1/completions",
                    data=body,
                    headers={"Content-Type": "application/json"},
                )
                start = time.monotonic()
                with urllib.request.urlopen(req, timeout=1200) as response:
                    result = json.load(response)
                record = {
                    "version": ver,
                    "context": phase,
                    "repeat": n + 1,
                    "elapsed_seconds": time.monotonic() - start,
                    "response": result,
                }
                print(
                    json.dumps(
                        {
                            "version": ver,
                            "context": phase,
                            "repeat": n + 1,
                            "usage": result.get("usage"),
                        }
                    ),
                    flush=True,
                )
                with (out / "responses.jsonl").open("a") as f:
                    f.write(json.dumps(record) + "\n")
                if danger:
                    raise RuntimeError(danger[0])
        (out / "outcome.json").write_text(
            json.dumps({"status": "passed", "guard": danger}, indent=2)
        )
    except Exception as e:
        (out / "outcome.json").write_text(
            json.dumps({"status": "failed", "error": str(e), "guard": danger}, indent=2)
        )
        raise
    finally:
        stop.set()
        os.killpg(proc.pid, signal.SIGTERM) if proc.poll() is None else None
        try:
            proc.wait(timeout=15)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL)
            proc.wait()
        t.join(timeout=10)
        log.close()
        shutil.rmtree(kv)
