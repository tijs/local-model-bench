"""Trace one guarded real Qwen request using the separately built Debug probe."""

import argparse
import json
import math
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


def child(cfg, output, runtime):
    result = {"status": "failed", "scope": "Dispatch trace only; no timing verdict."}
    launcher = None
    result["requests"] = []
    if cfg.get("arm"):
        result["scope"] = (
            "Controlled same-Debug-binary dispatch screen, one loaded observation per process; no release timing claim."
        )
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
            begin = time.monotonic()
            response = request_json(endpoint + "/completions", body)
            elapsed = time.monotonic() - begin
            write_json(output / f"{context}-response.json", response)
            if observable(response) != baseline[context]:
                raise ValueError(
                    f"{context} observable differs from final release-qualification control"
                )
            usage = response["usage"]
            metrics = {
                "request_wall_seconds": elapsed,
                "decode_tps": usage["tokens_per_second"],
                "backend_prefill_ms": usage["prefill_ms"],
                "backend_generate_ms": usage["generate_ms"],
            }
            if any(not math.isfinite(v) or v <= 0 for v in metrics.values()):
                raise ValueError("invalid diagnostic phase measurements")
            result["requests"].append({"context": context, **metrics})
        log = (runtime / "logs/server.log").read_text()
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
            trace["force_tk1"] != cfg["environment"]["MLX_SDPA_PROBE_FORCE_TK1"]
            or trace["ql"] != "1"
            or not 30000 <= int(trace["kl"]) <= 30128
        ):
            raise ValueError(
                "first trace was outside the declared loaded decode fixture"
            )
        if cfg.get("arm"):
            expected = read_pinned(cfg, "pilot_trace")["trace"]
            suffix = "_tk1" if trace["force_tk1"] == "1" else ""
            variable = {"kernel", "specialization", "force_tk1", "selected_max"}
            if (
                any(trace[k] != v for k, v in expected.items() if k not in variable)
                or trace["kernel"] != expected["kernel"] + suffix
                or trace["specialization"] != expected["specialization"] + suffix
            ):
                raise ValueError(
                    "actual Qwen dispatch differs beyond the intended TK variant"
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
                        str(runtime),
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
            source = runtime / "logs" / name
            if source.is_file():
                shutil.copy2(source, output / name)
        write_json(output / "trace-result.json", result)
    if result["status"] == "observables_passed":
        check_ports()
        checked_artifact(cfg)
        result["post_run_model_hashes"] = model_hashes(cfg)
        result.update(status="passed", server_stopped=True)
        write_json(output / "trace-result.json", result)
        return 0
    return 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--child", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument(
        "--arm", choices=("trace", "a1", "b1", "b2", "a2"), default="trace"
    )
    args = parser.parse_args()
    arm = args.arm
    declaration = (
        DECLARATION if arm == "trace" else PREP / f"qwen-sdpa-model-{arm}-20261107.json"
    )
    output = (
        OUTPUT
        if arm == "trace"
        else OUTPUT.with_name(f"mei011-qwen-sdpa-model-{arm}-20261107")
    )
    runtime = (
        RUNTIME
        if arm == "trace"
        else RUNTIME.with_name(f"qwen-upstream011-sdpa-model-{arm}-20261107")
    )
    cfg, raw = committed_native_config(declaration)
    if (
        cfg["benchmark_scope"] != "mei-kernel-diagnostic-v1"
        or cfg["environment"]["MEI_RUNTIME_BASE"] != str(runtime)
        or runtime.resolve() != runtime
    ):
        raise ValueError("unexpected diagnostic scope or owned runtime path")
    if args.child:
        owned = output / "process.json"
        for _ in range(20):
            if owned.is_file():
                break
            time.sleep(0.05)
        if not owned.is_file() or (output / "outcome.json").exists():
            raise ValueError("trace child requires its live resource supervisor")
        identity = json.loads(owned.read_text())
        if (
            identity != {"pid": os.getpid(), "pgid": os.getpgrp()}
            or (output / "config.yaml").read_bytes() != raw
        ):
            raise ValueError(
                "trace child requires its live resource-supervisor ownership"
            )

        def interrupted(_signum, _frame):
            signal.signal(signal.SIGTERM, signal.SIG_IGN)
            raise KeyboardInterrupt()

        signal.signal(signal.SIGTERM, interrupted)
        return child(cfg, output, runtime)
    if arm != "trace":
        order = ["a1", "b1", "b2", "a2"]
        force = "1" if arm.startswith("b") else "0"
        if cfg["arm"] != arm or cfg["environment"]["MLX_SDPA_PROBE_FORCE_TK1"] != force:
            raise ValueError("unexpected declared real-model treatment")
        matched, _ = committed_native_config(
            PREP / "qwen-sdpa-operator-model-layout-review-20261107.json"
        )
        if (
            matched.get("both_forced_process_means_faster_than_both_default_processes")
            is not True
        ):
            raise ValueError(
                "requires the reviewed positive matched-layout operator screen"
            )
        for prior in order[: order.index(arm)]:
            prior_dir = OUTPUT.with_name(f"mei011-qwen-sdpa-model-{prior}-20261107")
            outcome = json.loads((prior_dir / "outcome.json").read_text())
            result = json.loads((prior_dir / "trace-result.json").read_text())
            if (
                outcome["status"] != "passed"
                or result["status"] != "passed"
                or not result["server_stopped"]
            ):
                raise ValueError(
                    "previous declared model arm needs review before another launch"
                )
    check_ports()
    checked_artifact(cfg)
    if runtime.exists():
        raise ValueError("refuse an existing owned runtime directory")
    os.environ.clear()
    os.environ.update(cfg["environment"])
    args.output, args.deadline, args.skip_context, args.skip_cache = (
        output,
        900,
        True,
        True,
    )

    def checked(out):
        result = json.loads((out / "trace-result.json").read_text())
        return result["status"] == "passed" and result["server_stopped"] is True

    command = [sys.executable, str(Path(__file__).resolve()), "--arm", arm, "--child"]
    return monitor_child(cfg, raw, args, command, diagnostic_check=checked)


if __name__ == "__main__":
    raise SystemExit(main())
