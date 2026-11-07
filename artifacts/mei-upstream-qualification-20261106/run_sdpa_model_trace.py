"""Trace one guarded real Qwen request using the separately built Debug probe."""

import argparse
import json
import os
import shutil
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path

PREP = Path(__file__).resolve().parent
ROOT = PREP.parents[1]
sys.path.insert(0, str(ROOT / "runner"))
from qualify_mei_release import observable, request_json, serving_settings
from run_mei_acceptance import committed_native_config, monitor_child, wait_ready
from run_sdpa_operator_cell import digest
from run_standin_suite import write_json

DECLARATION = PREP / "qwen-sdpa-model-trace-20261107.json"
OUTPUT = ROOT / "artifacts/mei011-qwen-sdpa-model-trace-20261107"
RUNTIME = (
    Path.home()
    / ".local/share/local-model-bench/mei-runtime/qwen-upstream011-sdpa-model-trace-20261107"
)


def check_ports():
    for port in (8017, 8024):
        with socket.socket() as connection:
            connection.settimeout(0.5)
            if connection.connect_ex(("127.0.0.1", port)) == 0:
                raise ValueError(f"benchmark port {port} is occupied")


def checked_artifact(cfg):
    artifact = cfg["artifact"]
    base = Path(artifact["asset_directory"])
    if (
        digest(base / "mei") != artifact["debug_mei_sha256"]
        or digest(base / "mlx.metallib") != artifact["production_metallib_sha256"]
        or artifact["restored_exact_source_and_unchanged_production_assets"] is not True
    ):
        raise ValueError(
            "instrumented executable or production Metal identity mismatch"
        )


def read_pinned(cfg, key):
    item = cfg[key]
    path = (ROOT / item["path"]).resolve()
    if not path.is_relative_to(ROOT / "artifacts") or digest(path) != item["sha256"]:
        raise ValueError(f"{key} evidence identity mismatch")
    return json.loads(path.read_text())


def model_hashes(cfg):
    manifest = read_pinned(cfg, "model_manifest")
    base = Path(manifest["directory"]).resolve()
    if base != Path(cfg["model_directory"]).resolve() or len(manifest["files"]) != 15:
        raise ValueError("unexpected staged model manifest")
    observed = []
    for item in manifest["files"]:
        path = (base / item["file"]).resolve()
        if not path.is_relative_to(base):
            raise ValueError("model manifest path escapes its pinned directory")
        observed.append(
            {
                "file": item["file"],
                "bytes": path.stat().st_size,
                "sha256": digest(path),
            }
        )
    if observed != manifest["files"]:
        raise ValueError("staged model bytes differ from pinned manifest")
    return observed


def child(cfg):
    result = {"status": "failed", "scope": "Dispatch trace only; no timing verdict."}
    launcher = None
    try:
        checked_artifact(cfg)
        result["pre_run_model_hashes"] = model_hashes(cfg)
        prompts = read_pinned(cfg, "prompts")
        baseline = read_pinned(cfg, "baseline_audit")["reference"]
        launcher = subprocess.Popen(cfg["launch_command"], cwd=ROOT)
        endpoint = cfg["endpoint"]
        wait_ready(launcher, endpoint)
        ids = {item["id"] for item in request_json(endpoint + "/models")["data"]}
        if ids != {cfg["served_model"]}:
            raise ValueError("unexpected served-model identity")
        result["startup_settings"] = serving_settings(
            request_json(endpoint + "/mei/status"), cfg["launch_command"]
        )
        for context in ("short", "loaded"):
            body = {
                "model": cfg["served_model"],
                "prompt": prompts[context],
                "temperature": 0,
                "top_p": 1,
                "top_k": 1,
                "max_tokens": 128,
                "seed": 1,
                "stream": False,
            }
            response = request_json(endpoint + "/completions", body)
            write_json(OUTPUT / f"{context}-response.json", response)
            if observable(response) != baseline[context]:
                raise ValueError(
                    f"{context} observable differs from final release-qualification control"
                )
        log = (RUNTIME / "logs/server.log").read_text()
        lines = [
            line.split("[mei-sdpa-probe] ", 1)[1]
            for line in log.splitlines()
            if "[mei-sdpa-probe] " in line
        ]
        if len(lines) != 1:
            raise ValueError("requires exactly one actual dispatch trace")
        trace = dict(token.split("=", 1) for token in lines[0].split())
        result["trace"] = trace
        if (
            trace["force_tk1"] != "0"
            or trace["ql"] != "1"
            or not 30000 <= int(trace["kl"]) <= 30128
        ):
            raise ValueError(
                "first trace was outside the declared loaded decode fixture"
            )
        result["status"] = "observables_passed"
    except KeyboardInterrupt:
        result["error"] = "owned trace interrupted"
    except (OSError, ValueError, KeyError, TypeError, RuntimeError) as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
    finally:
        if launcher is not None:
            try:
                stop = subprocess.run(
                    [
                        "bash",
                        "runner/stop_mei_server.sh",
                        "--runtime-base",
                        str(RUNTIME),
                        "--timeout",
                        "8",
                    ],
                    cwd=ROOT,
                    timeout=10,
                    check=False,
                )
                result["stop_returncode"] = stop.returncode
                result["launcher_returncode"] = launcher.wait(timeout=5)
                if stop.returncode:
                    result["status"] = "failed"
            except (OSError, subprocess.SubprocessError) as exc:
                result.update(
                    status="failed", cleanup_error=f"{type(exc).__name__}: {exc}"
                )
        for name in ("server.log", "requests.jsonl"):
            source = RUNTIME / "logs" / name
            if source.is_file():
                shutil.copy2(source, OUTPUT / name)
        write_json(OUTPUT / "trace-result.json", result)
    if result["status"] == "observables_passed":
        check_ports()
        checked_artifact(cfg)
        result["post_run_model_hashes"] = model_hashes(cfg)
        result.update(status="passed", server_stopped=True)
        write_json(OUTPUT / "trace-result.json", result)
        return 0
    return 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--child", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    cfg, raw = committed_native_config(DECLARATION)
    if (
        cfg["benchmark_scope"] != "mei-kernel-diagnostic-v1"
        or cfg["environment"]["MEI_RUNTIME_BASE"] != str(RUNTIME)
        or RUNTIME.resolve() != RUNTIME
    ):
        raise ValueError("unexpected diagnostic scope or owned runtime path")
    if args.child:
        owned = OUTPUT / "process.json"
        for _ in range(20):
            if owned.is_file():
                break
            time.sleep(0.05)
        if not owned.is_file() or (OUTPUT / "outcome.json").exists():
            raise ValueError("trace child requires its live resource supervisor")
        identity = json.loads(owned.read_text())
        if (
            identity != {"pid": os.getpid(), "pgid": os.getpgrp()}
            or (OUTPUT / "config.yaml").read_bytes() != raw
        ):
            raise ValueError(
                "trace child requires its live resource-supervisor ownership"
            )

        def interrupted(_signum, _frame):
            signal.signal(signal.SIGTERM, signal.SIG_IGN)
            raise KeyboardInterrupt()

        signal.signal(signal.SIGTERM, interrupted)
        return child(cfg)
    check_ports()
    checked_artifact(cfg)
    if RUNTIME.exists():
        raise ValueError("refuse an existing owned runtime directory")
    os.environ.clear()
    os.environ.update(cfg["environment"])
    args.output, args.deadline, args.skip_context, args.skip_cache = (
        OUTPUT,
        900,
        True,
        True,
    )

    def checked(out):
        result = json.loads((out / "trace-result.json").read_text())
        return result["status"] == "passed" and result["server_stopped"] is True

    command = [sys.executable, str(Path(__file__).resolve()), "--child"]
    return monitor_child(cfg, raw, args, command, diagnostic_check=checked)


if __name__ == "__main__":
    raise SystemExit(main())
