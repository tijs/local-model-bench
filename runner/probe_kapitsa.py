"""Guarded, unscored native Clover diffusion/tool admission on pinned Kapitsa."""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import importlib.util
import json
import os
import shlex
import signal
import socket
import subprocess
import sys
from pathlib import Path

from bench_common import REPO
from mei_provenance import listener_binary, sha256
from run_mei_acceptance import committed_native_config, monitor_child, wait_ready
from run_prompt import call_backend_streaming
from run_standin_suite import admission, write_json

REQUIRED = {"identity", "plain", "tool_nonstreaming_auto", "tool_streaming_auto", "dependent_continuation"}


def diagnostic_succeeded(output: Path) -> bool:
    data = json.loads((output / "probe.json").read_text())
    if not isinstance(data, dict) or not isinstance(data.get("probes"), dict):
        return False
    return (data.get("status") == "passed" and data.get("decoder_verified") == "block diffusion"
            and REQUIRED <= data["probes"].keys()
            and all(isinstance(row, dict) and row.get("status") == "passed" for row in data["probes"].values()))


def verify(cfg):
    source = Path(cfg["runtime_source"])
    revision = subprocess.check_output(["git", "-C", str(source), "rev-parse", "HEAD"], text=True).strip()
    if revision != cfg["runtime_revision"]:
        raise ValueError("Kapitsa source revision mismatch")
    dirty = subprocess.check_output([
        "git", "-C", str(source), "status", "--porcelain", "--untracked-files=all",
        "--", "src", "third_party", "cmake", "CMakeLists.txt",
    ], text=True)
    if dirty or sha256(Path(cfg["runtime_binary"])) != cfg["runtime_binary_sha256"]:
        raise ValueError("Kapitsa source/binary mismatch")
    if sha256(Path(cfg["probe_program"])) != cfg["probe_program_sha256"]:
        raise ValueError("native probe program mismatch")
    if cfg["required_runner_environment"]["NI_CLOVER_DECODE"] != "diffusion":
        raise ValueError("this diagnostic requires actual diffusion")


def child(cfg, content, output):
    if os.environ.get("BENCH_ADMITTED_CONFIG_SHA256") != hashlib.sha256(content).hexdigest():
        raise ValueError("missing matching parent admission")
    verify(cfg)
    runtime = Path(cfg["runtime_base"])
    runtime.mkdir(parents=True, exist_ok=False)
    spec = importlib.util.spec_from_file_location("release_probe", cfg["probe_program"])
    if spec is None or spec.loader is None:
        raise ValueError("cannot load pinned stdlib probe helpers")
    probe = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(probe)
    result = {"status": "running", "engine": "kapitsa-metal", "probes": {}, "decoder_verified": None}
    write_json(output / "probe.json", result)
    command = shlex.split(cfg["benchmark_launch_command"])
    record = {"command": command, "runtime_revision": cfg["runtime_revision"],
              "binary_sha256": cfg["runtime_binary_sha256"], "probe_sha256": cfg["probe_program_sha256"]}
    url, model = cfg["benchmark_endpoint"], cfg["served_model_id"]

    def gate(name, fn):
        probe.checkpointed_probe(name, result, fn, output / "probe.json")

    with (output / "server.log").open("x") as log:
        server = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT)
        try:
            wait_ready(server, url, timeout=180)
            actual = listener_binary(url)
            if actual.resolve() != Path(cfg["runtime_binary"]).resolve():
                raise ValueError("listener is not the pinned Kapitsa executable")
            log_text = (output / "server.log").read_text()
            if "Clover: block diffusion, 32-row blocks, threshold 0.95" not in log_text:
                raise ValueError("startup did not confirm native diffusion32/threshold0.95")
            result["decoder_verified"] = "block diffusion"

            def identity():
                response, seconds = probe.request_json(url + "/models", timeout=15)
                if model not in [r["id"] for r in response["data"]]:
                    raise ValueError("served model identity mismatch")
                return {"response": response, "request_seconds": seconds}

            gate("identity", identity)
            payload = {"model": model, "messages": [{"role": "user", "content": "Say only ready."}],
                       "temperature": 0, "max_tokens": 4096, "stream": False}

            def plain():
                response, seconds = probe.request_json(url + "/chat/completions", payload, timeout=180)
                write_json(output / "plain-response.json", response)
                if (response["choices"][0]["message"].get("content") or "").strip().lower() != "ready":
                    raise ValueError("plain response did not say ready")
                return {"response": response, "request_seconds": seconds}

            gate("plain", plain)
            tool_payload = payload | {
                "messages": [{"role": "user", "content": "What is 15 + 27? You must use add_numbers to compute it."}],
                "tools": [{"type": "function", "function": {"name": "add_numbers", "description": "Add two integers.",
                    "parameters": {"type": "object", "properties": {"a": {"type": "integer"}, "b": {"type": "integer"}},
                                   "required": ["a", "b"], "additionalProperties": False}}}],
                "tool_choice": "auto",
            }

            def nonstream():
                response, seconds = probe.request_json(url + "/chat/completions", tool_payload, timeout=180)
                return probe.tool_probe_detail(response, seconds)

            def stream():
                response, seconds, ttft = probe.request_stream(url + "/chat/completions", tool_payload, timeout=180)
                return probe.tool_probe_detail(response, seconds, streaming=True, ttft=ttft)

            gate("tool_nonstreaming_auto", nonstream)
            gate("tool_streaming_auto", stream)

            def dependent():
                trace = admission(call_backend_streaming, url, model, {"temperature": 0})
                write_json(output / "dependent-admission.json", trace)
                if trace["status"] != "passed":
                    raise ValueError("native dependent tool continuation failed; see dependent-admission.json")
                return {"status": "passed", "turns": trace["turns"], "final_text": trace["final_text"]}

            gate("dependent_continuation", dependent)
            result["status"] = probe.aggregate_status(result["probes"])
        except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
            result.update(status="failed", error=f"{type(exc).__name__}: {exc}")
        finally:
            server.terminate()
            try:
                server.wait(timeout=15)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait(timeout=3)
            write_json(output / "probe.json", result)
            write_json(output / "record.json", record | {"status": result["status"]})
    return 0 if diagnostic_succeeded(output) else 1


def main():
    def interrupt(_signum, _frame):
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, interrupt)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--child", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    cfg, content = committed_native_config(args.config.resolve())
    verify(cfg)
    if cfg.get("benchmark_scope") != "kapitsa-native-diagnostic-v1" or cfg.get("diagnostic_only") is not True:
        raise ValueError("this runner is diagnostic-only")
    if args.child:
        return child(cfg, content, args.output)
    if Path(cfg["runtime_base"]).exists():
        raise ValueError("choose a fresh owned runtime base")
    for port in (8017, 8024):
        with socket.socket() as connection:
            connection.settimeout(0.5)
            if connection.connect_ex(("127.0.0.1", port)) == 0:
                raise ValueError(f"occupied benchmark port {port}")
    hashes = []
    for row in json.loads((REPO / cfg["model_manifest"]).read_text()):
        path = Path(cfg["model_directory"]) / row["file"]
        digest = sha256(path)
        if digest != row["sha256"] or path.stat().st_size != row["bytes"]:
            raise ValueError(f"model file mismatch: {path.name}")
        hashes.append(row)
    args.deadline, args.skip_cache, args.skip_context = 900, False, True
    with Path("/tmp/kapitsa-gpu.lock").open("a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        rc = monitor_child(cfg, content, args, [
            sys.executable, str(Path(__file__).resolve()), "--config", str(args.config.resolve()),
            "--output", str(args.output.resolve()), "--child",
        ], diagnostic_check=diagnostic_succeeded)
    write_json(args.output / "pre-run-model-hashes.json", hashes)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
