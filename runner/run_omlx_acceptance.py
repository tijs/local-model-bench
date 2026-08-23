#!/usr/bin/env python3
"""Run isolated oMLX acceptance probes sequentially from benchmark configs."""
from __future__ import annotations

import argparse
import json
import re
import shlex
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any

import yaml

REPO = Path(__file__).resolve().parent.parent
DEFAULT_LOG = Path("~/.local/share/local-model-bench/omlx-logs/server.log").expanduser()


def get_json(url: str, timeout: float = 10) -> dict[str, Any]:
    with urllib.request.urlopen(url, timeout=timeout) as response:
        return json.loads(response.read())


def split_launch_command(command: str) -> list[str]:
    return shlex.split(re.sub(r"\\[ \t]*\n", " ", command))


def wait_ready(process: subprocess.Popen, base_url: str, timeout: float = 60) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"launcher exited before health, rc={process.returncode}")
        try:
            get_json(f"{base_url.removesuffix('/v1')}/health")
            return
        except Exception:
            time.sleep(0.5)
    raise TimeoutError(f"oMLX health was not ready after {timeout}s")


def run_config(config_path: Path, args: argparse.Namespace) -> dict[str, Any]:
    cfg = yaml.safe_load(config_path.read_text()) or {}
    orch = cfg.get("orchestration") or {}
    model = orch.get("served_model_id")
    if cfg.get("inference_engine") != "omlx" or not model:
        raise ValueError(f"not an oMLX served-model config: {config_path}")
    # Configs are shell-readable literal blocks with POSIX backslash/newline
    # continuations. We execute argv directly, so remove those continuations
    # before shlex; otherwise they become literal "\n" arguments.
    command = split_launch_command(str(cfg["benchmark_launch_command"]))
    base_url = str(cfg.get("benchmark_endpoint", "http://127.0.0.1:8020/v1"))
    model_root = Path("~/.local/share/local-model-bench/omlx-models").expanduser()
    tokenizer = model_root / model
    output_root = args.output_root / model / config_path.stem
    output_root.mkdir(parents=True, exist_ok=True)
    launch_log = output_root / "launcher.log"
    server_log = DEFAULT_LOG
    server_log_offset = server_log.stat().st_size if server_log.exists() else 0
    started = time.time()
    record: dict[str, Any] = {
        "config": str(config_path.relative_to(REPO)),
        "model": model,
        "source_model": cfg.get("model"),
        "source_revision": cfg.get("source_revision"),
        "cache_mode": cfg.get("cache_mode"),
        "mtp_mode": cfg.get("mtp_mode"),
        "command": command,
        "started_epoch": started,
    }
    process: subprocess.Popen | None = None
    try:
        with launch_log.open("w") as launch_stream:
            process = subprocess.Popen(command, cwd=REPO, stdout=launch_stream, stderr=subprocess.STDOUT, text=True)
            wait_ready(process, base_url)
            probe_path = output_root / "probe.json"
            probe_cmd = [
                str(Path("~/.local/share/local-model-bench/omlx-venv/bin/python").expanduser()),
                str(REPO / "runner" / "probe_omlx.py"),
                "--base-url", base_url,
                "--model", model,
                "--tokenizer", str(tokenizer),
                "--output", str(probe_path),
                "--timeout", str(args.timeout),
            ]
            if args.skip_context:
                probe_cmd.append("--skip-context")
            if args.skip_cache:
                probe_cmd.append("--skip-cache")
            completed = subprocess.run(probe_cmd, cwd=REPO, text=True, capture_output=True, timeout=args.timeout + 120)
            (output_root / "probe.stdout.log").write_text(completed.stdout)
            (output_root / "probe.stderr.log").write_text(completed.stderr)
            record["probe_returncode"] = completed.returncode
            if probe_path.exists():
                record["probe_status"] = json.loads(probe_path.read_text()).get("status")
            else:
                record["probe_status"] = "missing_artifact"
            health = get_json(f"{base_url.removesuffix('/v1')}/health")
            (output_root / "health.json").write_text(json.dumps(health, indent=2, sort_keys=True) + "\n")
            pid = process.pid
            ps = subprocess.run(
                ["ps", "-p", str(pid), "-o", "pid=,etime=,rss=,%mem=,command="],
                text=True, capture_output=True,
            )
            (output_root / "process.txt").write_text(ps.stdout)
            record["health"] = health
            record["status"] = "passed" if completed.returncode == 0 else "failed"
    except BaseException as exc:
        record.update(status="failed", error=f"{type(exc).__name__}: {exc}")
    finally:
        stop = subprocess.run(
            ["bash", str(REPO / "runner" / "stop_omlx_server.sh")],
            cwd=REPO, text=True, capture_output=True,
        )
        (output_root / "teardown.log").write_text(stop.stdout + stop.stderr)
        if process is not None:
            try:
                process.wait(timeout=20)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=10)
        if server_log.exists():
            with server_log.open("rb") as stream:
                stream.seek(server_log_offset)
                (output_root / "server.log").write_bytes(stream.read())
        record["teardown_returncode"] = stop.returncode
        record["finished_epoch"] = time.time()
        (output_root / "summary.json").write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    return record


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("configs", nargs="+", type=Path)
    parser.add_argument("--output-root", type=Path, default=Path("results/omlx/acceptance"))
    parser.add_argument("--timeout", type=float, default=3600)
    parser.add_argument("--skip-context", action="store_true")
    parser.add_argument("--skip-cache", action="store_true")
    args = parser.parse_args()
    records = []
    for config in args.configs:
        record = run_config(config.resolve(), args)
        records.append(record)
        print(json.dumps({key: record.get(key) for key in ("config", "model", "cache_mode", "mtp_mode", "status", "error")}, sort_keys=True), flush=True)
    summary = {"status": "passed" if all(r.get("status") == "passed" for r in records) else "failed", "records": records}
    args.output_root.mkdir(parents=True, exist_ok=True)
    (args.output_root / "matrix-summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    return 0 if summary["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
