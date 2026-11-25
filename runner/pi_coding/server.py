"""Launch one verified local Mei process or attach to a configured test endpoint."""

import fcntl
import hashlib
import json
import os
import signal
import socket
import subprocess
import tempfile
import threading
import time
import urllib.request
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import urlparse

from pi_coding.workspace import write_json
from supervise_bench import baseline_ready, gate_reason, sample


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def get(url):
    with urllib.request.urlopen(url, timeout=5) as response:
        return json.load(response)


def verify(path, expected):
    if digest(path) != expected:
        raise ValueError(f"Artifact checksum mismatch: {path}")


@contextmanager
def endpoint(cfg, config_path, out):
    base = cfg["endpoint"].rstrip("/")
    url = urlparse(base)
    if url.hostname not in {"127.0.0.1", "localhost", "::1"}:
        raise ValueError("Pi coding expects a local model endpoint")
    is_llama = "llama" in cfg
    managed = cfg.get("llama") if is_llama else cfg.get("mei")
    if not managed:
        if cfg["model"] not in [m["id"] for m in get(base + "/models")["data"]]:
            raise ValueError("Expected served model missing")
        yield
        return
    binary = Path(managed["binary"]).expanduser().resolve()
    verify(binary, managed["binary_sha256"])
    if is_llama:
        gguf = Path(managed["model_path"]).expanduser().resolve()
        model = gguf.parent
        weights = {gguf.name: managed["model_sha256"]}
        for name, checksum in managed["libraries"].items():
            verify(binary.with_name(name), checksum)
    else:
        model = Path(managed["directory"]).expanduser().resolve()
        verify(binary.with_name("mlx.metallib"), managed["metallib_sha256"])
        weights = json.loads(
            (config_path.parent / managed["file_manifest"]).read_text()
        )
        if {p.name for p in model.glob("*.safetensors")} != {
            n for n in weights if n.endswith(".safetensors")
        }:
            raise ValueError("Unexpected model shard set")
    with open(
        Path(tempfile.gettempdir()) / "local-model-bench-pi-coding.lock", "a"
    ) as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        names = subprocess.check_output(["ps", "-axo", "comm="], text=True).splitlines()
        if any(
            Path(n.strip()).name
            in {"mei", "llama-server", "llama-cli", "SenseNovaProbe"}
            for n in names
        ):
            raise RuntimeError("An existing inference process owns the host")
        with socket.socket() as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((url.hostname, url.port))
        for name, checksum in weights.items():
            verify(model / name, checksum)
        baseline = []
        for _ in range(3):
            baseline.append(sample(os.getpid(), out))
            time.sleep(1)
        if not baseline_ready(baseline, None, 2):
            raise RuntimeError("Resource baseline failed")
        if is_llama:
            cmd = [
                str(binary),
                "--model",
                str(gguf),
                "--alias",
                cfg["model"],
                "--host",
                url.hostname,
                "--port",
                str(url.port),
                "--ctx-size",
                str(cfg["context"]),
                "--temp",
                "0",
                *managed["args"],
            ]
        else:
            cmd = [
                str(binary),
                "--model-dir",
                str(model),
                "--served-model-id",
                cfg["model"],
                "--port",
                str(url.port),
                "--context-cap",
                str(cfg["context"]),
                "--max-tokens",
                str(cfg["output_tokens"]),
                "--cache-mode",
                "off",
                "--temperature",
                "0",
                "--log-requests",
                "true",
                "--request-log",
                str(out / "requests.jsonl"),
                *managed["args"],
            ]
        env = {
            k: v
            for k, v in os.environ.items()
            if not k.startswith(("VMLX_", "MEI_", "MLX_", "MLXPRESS_"))
        }
        env.update(managed.get("environment", {}))
        write_json(
            out / "launch.json",
            {
                "command": cmd,
                "environment": managed.get("environment", {}),
                "weights": weights,
                "baseline": baseline,
            },
        )
        with (out / "server.log").open("w") as log:
            proc = subprocess.Popen(
                cmd, stdout=log, stderr=log, env=env, start_new_session=True
            )
            stopped = threading.Event()
            errors = []

            def monitor():
                warnings = 0
                try:
                    with (out / "resources.jsonl").open("w") as journal:
                        while not stopped.is_set():
                            point = sample(proc.pid, out)
                            journal.write(json.dumps(point) + "\n")
                            journal.flush()
                            warnings = (
                                warnings + 1
                                if point["kernel_pressure_level"] != 1
                                else 0
                            )
                            reason = gate_reason(
                                point, baseline[0], 0, warnings, percent_stop=False
                            )
                            footprint = next(
                                (
                                    r["phys_footprint_bytes"]
                                    for r in point["owned_processes"]
                                    if r["pid"] == proc.pid
                                ),
                                0,
                            )
                            if (
                                reason
                                or not footprint
                                or footprint > 24 * 1024**3
                                or point["swap_used_mib"] - baseline[0]["swap_used_mib"]
                                >= 256
                            ):
                                raise RuntimeError(
                                    reason
                                    or "Server footprint/swap guard tripped or server exited"
                                )
                            stopped.wait(1)
                except Exception as exc:  # noqa: BLE001 -- sampler failures must stop the owned server
                    errors.append(str(exc))
                    if proc.poll() is None:
                        proc.terminate()

            watcher = threading.Thread(target=monitor, daemon=True)
            watcher.start()
            try:
                for _ in range(600):
                    if proc.poll() is not None:
                        raise RuntimeError(f"Model server exited: {errors}")
                    try:
                        if [m["id"] for m in get(base + "/models")["data"]] == [
                            cfg["model"]
                        ]:
                            break
                    except OSError:
                        pass
                    time.sleep(1)
                else:
                    raise TimeoutError("Model readiness deadline")
                status = (
                    get(base.rsplit("/v1", 1)[0] + "/props")
                    if is_llama
                    else get(base + "/mei/status")
                )
                if is_llama:
                    if status["default_generation_settings"]["n_ctx"] != cfg["context"]:
                        raise ValueError("Unexpected llama.cpp context")
                elif status["contextCap"] != cfg["context"] or status["cacheReuse"]:
                    raise ValueError("Unexpected server settings")
                write_json(out / "status.json", status)
                yield
            finally:
                stopped.set()
                watcher.join()
                if proc.poll() is None:
                    os.killpg(proc.pid, signal.SIGTERM)
                    try:
                        proc.wait(15)
                    except subprocess.TimeoutExpired:
                        os.killpg(proc.pid, signal.SIGKILL)
                        proc.wait()
                write_json(
                    out / "shutdown.json",
                    {"returncode": proc.returncode, "errors": errors},
                )
            if errors:
                raise RuntimeError(str(errors))
