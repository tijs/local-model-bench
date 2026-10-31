"""Bounded raw-envelope diagnostic; never writes scored benchmark rows."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "runner"))
from bench_common import git_sha
from mei_provenance import verify_mei_runtime
from owned_process import OwnedSession
from run_bench import mei_stop_command, server_command, wait_for_health
from run_prompt import call_backend_streaming
from run_standin_suite import committed_config, verify_endpoint_identity, write_json
from supervise_bench import gate_reason, launch_floor, now, sample


def worker(cfg, inputs, output):
    server = None
    try:
        with (output / "launch.log").open("x") as log:
            server = subprocess.Popen(
                ["bash", "-c", server_command(cfg)],
                cwd=ROOT,
                stdout=log,
                stderr=subprocess.STDOUT,
            )
        base = cfg["benchmark_endpoint"]
        if not wait_for_health(base + "/models", timeout=600, proc=server):
            raise RuntimeError("diagnostic server failed health")
        verify_endpoint_identity(base, cfg["model"])
        write_json(output / "runtime.json", verify_mei_runtime(cfg, base_url=base))
        log = (
            Path(cfg["required_runner_environment"]["MEI_RUNTIME_BASE"])
            / "logs/server.log"
        )
        request = inputs["request"]
        with (output / "responses.jsonl").open("x", buffering=1) as journal:
            for case in inputs["cases"]:
                offset = log.stat().st_size
                started = time.monotonic()
                response, ttft, decode = call_backend_streaming(
                    base,
                    cfg["model"],
                    request["messages"],
                    request["tools"],
                    timeout=180,
                    max_tokens=4096,
                    **case["sampler"],
                    connect_timeout=90,
                    first_progress_timeout=90,
                    stream_idle_timeout=30,
                )
                with log.open("rb") as stream:
                    stream.seek(offset)
                    text = stream.read().decode("utf-8")
                envelopes = [
                    line for line in text.splitlines() if "[vMLX tool-envelope]" in line
                ]
                record = {
                    "name": case["name"],
                    "sampler": case["sampler"],
                    "seconds": time.monotonic() - started,
                    "ttft": ttft,
                    "decode": decode,
                    "raw_envelope_lines": envelopes,
                    "response": response,
                }
                journal.write(json.dumps(record, ensure_ascii=True) + "\n")
                print(case["name"], "raw envelopes", len(envelopes), flush=True)
    finally:
        subprocess.run(mei_stop_command(cfg), cwd=ROOT, check=False, timeout=45)
        if server is not None:
            server.wait(timeout=15)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--worker", action="store_true")
    args = parser.parse_args()
    cfg, content = committed_config(args.config)
    if cfg.get("diagnostic_only") is not True:
        raise ValueError("a committed diagnostic-only config is required")
    inputs = json.loads(args.inputs.read_text())
    if args.worker:
        worker(cfg, inputs, args.out)
        return
    for port in (8024, 8017):
        with socket.socket() as sock:
            if sock.connect_ex(("127.0.0.1", port)) == 0:
                raise RuntimeError("another model already owns a benchmark port")
    if "+" in git_sha() or git_sha() == "unknown":
        raise ValueError("commit diagnostic configuration/source before launch")
    args.out.mkdir(parents=True, exist_ok=False)
    initial = sample(os.getpid(), args.out)
    floor = launch_floor(cfg)
    write_json(
        args.out / "invocation.json",
        {
            "time": now(),
            "source": git_sha(),
            "initial": initial,
            "launch_min_free_percent": floor,
            "deadline_seconds": 900,
            "config_sha256": hashlib.sha256(content).hexdigest(),
            "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "inputs_sha256": hashlib.sha256(args.inputs.read_bytes()).hexdigest(),
            "limitations": inputs["limits"],
        },
    )
    (args.out / "config.yaml").write_bytes(content)
    if (
        initial["free_percent"] < floor
        or initial["kernel_pressure_level"] != 1
        or gate_reason(initial, initial, 0, 0)
    ):
        write_json(
            args.out / "outcome.json",
            {"reason": "preflight declined", "server_started": False},
        )
        raise SystemExit(2)
    environment = os.environ.copy()
    environment.update(cfg["required_runner_environment"])
    reason = None
    low = warnings = 0
    end = time.monotonic() + 900
    with (
        (args.out / "worker.log").open("x") as log,
        (args.out / "resources.jsonl").open("x", buffering=1) as telemetry,
    ):
        process = subprocess.Popen(
            [
                sys.executable,
                str(Path(__file__).resolve()),
                "--config",
                str(args.config),
                "--inputs",
                str(args.inputs),
                "--out",
                str(args.out),
                "--worker",
            ],
            env=environment,
            stdout=log,
            stderr=subprocess.STDOUT,
            cwd=ROOT,
            start_new_session=True,
        )
        session = OwnedSession(process)
        try:
            while not session.leader_exited():
                current = sample(process.pid, args.out)
                telemetry.write(json.dumps(current) + "\n")
                low = low + 1 if current["free_percent"] <= 10 else 0
                warnings = warnings + 1 if current["kernel_pressure_level"] >= 2 else 0
                reason = gate_reason(current, initial, low, warnings)
                if reason is None and time.monotonic() >= end:
                    reason = "diagnostic deadline"
                if reason:
                    break
                time.sleep(5)
        except KeyboardInterrupt:
            reason = "interrupted"
        except (
            OSError,
            RuntimeError,
            ValueError,
            TypeError,
            KeyError,
            subprocess.SubprocessError,
        ) as exc:
            reason = f"monitor failure: {type(exc).__name__}: {exc}"
        finally:
            try:
                session.stop(grace_seconds=15)
            except (
                OSError,
                RuntimeError,
                ValueError,
                TypeError,
                KeyError,
                subprocess.SubprocessError,
            ) as exc:
                reason = f"{reason or 'cleanup'}: {type(exc).__name__}: {exc}"
            write_json(
                args.out / "outcome.json",
                {"time": now(), "reason": reason, "returncode": process.returncode},
            )
    if reason or process.returncode:
        raise SystemExit(1)


if __name__ == "__main__":

    def interrupt(_signum, _frame):
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, interrupt)
    main()
