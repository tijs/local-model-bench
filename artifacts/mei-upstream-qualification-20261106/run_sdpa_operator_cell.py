"""Run one declared, guarded SDPA operator cell, never a model or scored task."""

import argparse
import hashlib
import json
import math
import os
import socket
import sys
from pathlib import Path

PREP = Path(__file__).resolve().parent
ROOT = PREP.parents[1]
sys.path.insert(0, str(ROOT / "runner"))
from build_context_speed_cohort import validate_resources
from run_mei_acceptance import committed_native_config, monitor_child

DECLARATION = PREP / "qwen-sdpa-operator-screen-20261107.json"
MODEL_LAYOUT_DECLARATION = PREP / "qwen-sdpa-operator-model-layout-screen-20261107.json"


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def output_for(arm, case="contiguous"):
    name = "bf16" if case == "contiguous" else "qwen-layout"
    return ROOT / "artifacts" / f"mei011-sdpa-operator-{name}-{arm}-20261107"


def read_observation(output, cfg, arm):
    artifact = cfg["artifact"]
    asset = Path(artifact["asset_directory"])
    fixture = cfg["fixture"]
    force = cfg["arm_force_tk1"][arm]
    result = json.loads((output / "samples.json").read_text())
    log = (output / "child.log").read_text()
    traces = [
        line.split("[mei-sdpa-probe] ", 1)[1]
        for line in log.splitlines()
        if "[mei-sdpa-probe] " in line
    ]
    rounds = result["samples_seconds_per_operator_by_round"]
    if (
        result["numerical_check_passed"] is not True
        or result["architecture"] != "applegpu_g13s"
        or result["shape_qh_kvh_context_dim"]
        != [fixture[k] for k in ("query_heads", "kv_heads", "context", "head_dim")]
        or result["query_length"] != fixture["query_length"]
        or result["kv_storage_capacity"] != fixture["kv_storage_capacity"]
        or result["force_tk1"] != force
        or Path(result["metallib_override"]) != asset / "mlx.metallib"
        or result["dtype"] != fixture["dtype"]
        or len(rounds) != fixture["sample_rounds"]
        or any(
            len(row) != fixture["samples_per_round"]
            or any(not math.isfinite(v) or v <= 0 for v in row)
            for row in rounds
        )
        or len(traces) != 1
        or "Executed 1 test, with 0 failures" not in log
    ):
        raise ValueError(
            "operator observation lacks declared shape/numerical/trace proof"
        )
    trace = dict(token.split("=", 1) for token in traces[0].split())
    if trace["force_tk1"] != force or trace["arch"] != result["architecture"]:
        raise ValueError("kernel trace disagrees with executed test settings")
    if model_trace := cfg.get("model_trace"):
        ignored = {"qss", "kernel", "specialization", "force_tk1", "selected_max"}
        if (
            trace["ql"] != "1"
            or any(trace[k] != v for k, v in model_trace.items() if k not in ignored)
            or trace["kernel"].removesuffix("_tk1") != model_trace["kernel"]
            or trace["specialization"].removesuffix("_tk1")
            != model_trace["specialization"]
        ):
            raise ValueError(
                "operator dispatch/strides do not match the actual Qwen case"
            )
    return result, trace


def review_terminal(output, cfg, raw, arm):
    outcome = json.loads((output / "outcome.json").read_text())
    invocation = json.loads((output / "invocation.json").read_text())
    if (
        outcome["status"] != "passed"
        or outcome["returncode"] != 0
        or outcome["full_native_admission"] is not False
        or (output / "config.yaml").read_bytes() != raw
        or invocation["config_sha256"] != hashlib.sha256(raw).hexdigest()
    ):
        raise ValueError(
            "requires a terminal successful operator cell with committed inputs"
        )
    validate_resources(output, cfg, invocation)
    return read_observation(output, cfg, arm)


def comparable_trace(trace):
    variable = {"kernel", "specialization", "selected_max", "force_tk1"}
    return {k: v for k, v in trace.items() if k not in variable}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arm", choices=("a1", "b1", "b2", "a2"), required=True)
    parser.add_argument(
        "--case", choices=("contiguous", "model-layout"), default="contiguous"
    )
    options = parser.parse_args()
    arm, case = options.arm, options.case
    cfg, raw = committed_native_config(
        DECLARATION if case == "contiguous" else MODEL_LAYOUT_DECLARATION
    )
    if (
        cfg["benchmark_scope"] != "mei-operator-diagnostic-v1"
        or cfg["diagnostic_only"] is not True
        or cfg["order"] != ["a1", "b1", "b2", "a2"]
        or cfg["arm_force_tk1"] != {"a1": "0", "b1": "1", "b2": "1", "a2": "0"}
    ):
        raise ValueError("unexpected operator declaration")
    reference = None
    for prior in cfg["order"][: cfg["order"].index(arm)]:
        _, trace = review_terminal(output_for(prior, case), cfg, raw, prior)
        if reference is None:
            if trace["kernel"].endswith("_tk1"):
                raise ValueError("default already selects TK1; no distinct treatment")
            reference = trace
        elif (
            comparable_trace(trace) != comparable_trace(reference)
            or trace["kernel"] != reference["kernel"] + "_tk1"
            or trace["specialization"] != reference["specialization"] + "_tk1"
        ):
            raise ValueError(
                "prior forced arm did not select only the expected TK1 variant"
            )
    asset = Path(cfg["artifact"]["asset_directory"])
    bundle = asset / "MeiTests.xctest"
    exe = bundle / "Contents/MacOS/MeiTests"
    metal = asset / "mlx.metallib"

    def artifact_matches():
        return (
            digest(exe) == cfg["artifact"]["xctest_sha256"]
            and digest(metal) == cfg["artifact"]["metallib_sha256"]
        )

    if not artifact_matches():
        raise ValueError("Debug test executable or production Metal hash mismatch")
    for port in (8017, 8024):
        with socket.socket() as connection:
            if connection.connect_ex(("127.0.0.1", port)) == 0:
                raise ValueError(f"benchmark port {port} is occupied")
    output = output_for(arm, case)
    fixture = cfg["fixture"]
    environment = {
        "HOME": str(Path.home()),
        "PATH": "/usr/bin:/bin:/usr/sbin:/sbin",
        "DEVELOPER_DIR": "/Applications/Xcode.app/Contents/Developer",
        "MEI_RUN_SDPA_PROBE": "1",
        "MEI_SDPA_PROBE_OUTPUT": str(output / "samples.json"),
        "MEI_SDPA_PROBE_METALLIB": str(metal),
        "MEI_SDPA_PROBE_DTYPE": fixture["dtype"],
        "MEI_SDPA_PROBE_CONTEXT": str(fixture["context"]),
        "MEI_SDPA_PROBE_CAPACITY": str(fixture["kv_storage_capacity"]),
        "MLX_SDPA_PROBE_TRACE": "1",
        "MLX_SDPA_PROBE_FORCE_TK1": cfg["arm_force_tk1"][arm],
    }
    os.environ.clear()
    os.environ.update(environment)

    def checked(out):
        try:
            _, trace = read_observation(out, cfg, arm)
            suffix = "_tk1" if cfg["arm_force_tk1"][arm] == "1" else ""
            return artifact_matches() and (
                reference is None
                or (
                    comparable_trace(trace) == comparable_trace(reference)
                    and trace["kernel"] == reference["kernel"] + suffix
                    and trace["specialization"] == reference["specialization"] + suffix
                )
            )
        except (OSError, KeyError, TypeError, ValueError):
            return False

    args = argparse.Namespace(
        output=output, deadline=300, skip_context=True, skip_cache=True
    )
    command = [
        "/usr/bin/xcrun",
        "xctest",
        "-XCTest",
        "MeiTests.QwenSDPAProbeTests/testVectorProbe",
        str(bundle),
    ]
    return monitor_child(cfg, raw, args, command, diagnostic_check=checked)


if __name__ == "__main__":
    raise SystemExit(main())
