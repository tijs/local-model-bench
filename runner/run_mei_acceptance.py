#!/usr/bin/env python3
"""Run isolated Mei acceptance probes sequentially from benchmark configs.

Launches each mei config's benchmark_launch_command, waits for health, runs
runner/probe_mei.py, and records probe JSON + launcher logs under
~/.local/share/local-model-bench/results-mei/<model>/<config-stem>-<stamp>/.
Historical results are never overwritten: each run lands in a timestamped
subdirectory.
"""
from __future__ import annotations

import argparse
import json
import re
import shlex
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

import yaml

REPO = Path(__file__).resolve().parent.parent
MEI_MODEL_ROOT = Path("~/.local/share/local-model-bench/mei-models").expanduser()


def split_launch_command(command: str) -> list[str]:
    # YAML |-blocks keep the trailing line-continuation backslashes; strip
    # backslash-newline before shlex, otherwise they become literal "\n"
    # arguments (same handling as the retired oMLX acceptance runner).
    return shlex.split(re.sub(r"\\[ \t]*\n", " ", command))


def get_json(url: str, timeout: float = 10) -> dict[str, Any]:
    with urllib.request.urlopen(url, timeout=timeout) as response:
        return json.loads(response.read())


def wait_ready(process: subprocess.Popen, base_url: str, timeout: float = 900) -> None:
    models_url = f"{base_url.rstrip('/')}/models"
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"launcher exited before health, rc={process.returncode}")
        try:
            get_json(models_url)
            return
        except (urllib.error.URLError, OSError, ValueError):
            time.sleep(1.0)
    raise TimeoutError(f"Mei /v1/models was not ready after {timeout}s")


def run_config(config_path: Path, args: argparse.Namespace) -> dict[str, Any]:
    cfg = yaml.safe_load(config_path.read_text()) or {}
    orch = cfg.get("orchestration") or {}
    model = orch.get("served_model_id")
    if cfg.get("inference_engine") != "mei" or not model:
        raise ValueError(f"not a Mei served-model config: {config_path}")

    command = split_launch_command(str(cfg["benchmark_launch_command"]))
    base_url = str(cfg.get("benchmark_endpoint", "http://127.0.0.1:8024/v1"))
    # The launch command's --model-dir is the authoritative tokenizer/model
    # path. Failing that (defensive), try the served-id-name convention:
    # full hub id (mlx-community/Qwen3.8-27B-4bit) then its basename.
    # Staging dir names do NOT always equal the served-id basename
    # (e.g. Qwen3.8-27B-Uncensored-MLX-4bit), so guess-and-check is not
    # reliable — --model-dir is.
    tokenizer_args = [command[i + 1] for i, a in enumerate(command) if a == "--model-dir"]
    tokenizer: Path | None = Path(tokenizer_args[0]).expanduser() if tokenizer_args else None
    if tokenizer is None or not (tokenizer / "config.json").exists():
        candidates = [MEI_MODEL_ROOT / model, MEI_MODEL_ROOT / model.split("/")[-1]]
        tokenizer = next((p for p in candidates if (p / "config.json").exists()), candidates[1])
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    output_root = (
        Path("~/.local/share/local-model-bench/results-mei").expanduser()
        / model / f"{config_path.stem}-{stamp}"
    )
    output_root.mkdir(parents=True, exist_ok=True)
    launch_log = output_root / "launcher.log"
    started = time.time()
    record: dict[str, Any] = {
        "config": str(config_path.relative_to(REPO)),
        "model": model,
        "source_model": cfg.get("model"),
        "command": command,
        "started_epoch": started,
        "output_root": str(output_root),
    }
    process: subprocess.Popen | None = None
    try:
        with launch_log.open("w") as launch_stream:
            process = subprocess.Popen(
                command, cwd=REPO, stdout=launch_stream, stderr=subprocess.STDOUT, text=True)
            wait_ready(process, base_url)
            probe_path = output_root / "probe.json"
            probe_cmd = [
                sys.executable,
                str(REPO / "runner" / "probe_mei.py"),
                "--base-url", base_url,
                "--model", model,
                "--tokenizer", str(tokenizer),
                "--output", str(probe_path),
                "--context-cap", str(cfg.get("context_cap", 65536)),
            ]
            if args.skip_context:
                probe_cmd.append("--skip-context")
            if args.skip_cache:
                probe_cmd.append("--skip-cache")
            probe = subprocess.run(probe_cmd, capture_output=True, text=True, timeout=3600)
            record["probe_rc"] = probe.returncode
            record["probe_stdout"] = probe.stdout[-4000:]
            record["probe_stderr"] = probe.stderr[-2000:]
            record["status"] = "passed" if probe.returncode == 0 else "failed"
    except BaseException as exc:
        record["status"] = "error"
        record["error"] = f"{type(exc).__name__}: {exc}"
    finally:
        # Stop the real server FIRST, while the launcher (start_mei_server.sh
        # wrapper) is still alive and its pid file still exists. Terminating
        # the wrapper first triggers its EXIT trap, which deletes the pid
        # file, turning stop_mei_server.sh into a no-op and ORPHANING the Mei
        # server (observed live: leaked ~19-24 GB Metal heaps per run).
        subprocess.run(
            ["bash", str(REPO / "runner" / "stop_mei_server.sh")], capture_output=True, text=True)
        if process is not None:
            process.terminate()
            try:
                process.wait(timeout=30)
            except subprocess.TimeoutExpired:
                process.kill()
    record["finished_epoch"] = time.time()
    (output_root / "record.json").write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    return record


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, help="configs/<model>/mei*.yaml")
    parser.add_argument("--skip-context", action="store_true")
    parser.add_argument("--skip-cache", action="store_true")
    args = parser.parse_args()
    config_path = REPO / args.config
    record = run_config(config_path, args)
    print(json.dumps(record, indent=2, sort_keys=True))
    return 0 if record.get("status") == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
