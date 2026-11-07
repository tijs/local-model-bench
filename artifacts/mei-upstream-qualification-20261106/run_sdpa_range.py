"""Run the predeclared model-free attention range sweep under one resource guard."""

import argparse
import json
import os
import socket
import statistics
import subprocess
import sys
import time
from pathlib import Path

from run_sdpa_operator_cell import (
    PREP,
    ROOT,
    comparable_trace,
    digest,
    read_observation,
)

# isort: split
from build_context_speed_cohort import validate_resources
from run_mei_acceptance import committed_native_config, monitor_child

DECLARATION = PREP / "qwen-sdpa-range-20261107.json"
OUTPUT = ROOT / "artifacts/mei011-sdpa-range-corrected-20261107"


def check_ports():
    for port in (8017, 8024):
        with socket.socket() as connection:
            connection.settimeout(0.5)
            if connection.connect_ex(("127.0.0.1", port)) == 0:
                raise ValueError(f"benchmark port {port} is occupied")


def paths(cfg):
    artifact = cfg["artifact"]
    asset = Path(artifact["asset_directory"])
    bundle = asset / "MeiTests.xctest"
    metal = asset / "mlx.metallib"
    if (
        digest(bundle / "Contents/MacOS/MeiTests") != artifact["xctest_sha256"]
        or digest(metal) != artifact["production_metallib_sha256"]
        or artifact["restored_exact_source_and_unchanged_production_assets"] is not True
    ):
        raise ValueError("range XCTest or production Metal identity mismatch")
    return bundle, metal


def case_output(fixture, arm):
    return OUTPUT / f"{fixture['context']}-{arm}"


def checked_case(cfg, fixture, arm):
    samples, trace = read_observation(
        case_output(fixture, arm), {**cfg, "fixture": fixture}, arm
    )
    reference = cfg["pilot_trace"]
    excluded = {"kl", "khs", "vhs", "qss"}
    base = comparable_trace(reference)
    actual = comparable_trace(trace)
    suffix = "_tk1" if arm.startswith("b") else ""
    capacity = fixture["kv_storage_capacity"]
    context = fixture["context"]
    # The existing g13s dispatch changes the block-count specialization at
    # 8,192 and 32,768 tokens for this GQA fixture. Check it explicitly.
    blocks = 128 if context <= 8192 else 256 if context <= 32768 else 512
    specialization = reference["specialization"].rsplit("_", 1)[0]
    if (
        any(actual[k] != v for k, v in base.items() if k not in excluded)
        or trace["kl"] != str(fixture["context"])
        or any(trace[k] != str(capacity * 256) for k in ("khs", "vhs"))
        or trace["kernel"] != reference["kernel"] + suffix
        or trace["specialization"] != f"{specialization}_{blocks}{suffix}"
        or int(trace["selected_max"]) < int(trace["threads"])
    ):
        raise ValueError("range fixture did not exercise the declared dispatch")
    return {
        "arm": arm,
        "output": str(case_output(fixture, arm).relative_to(ROOT)),
        "trace": trace,
        "mean_ms": statistics.mean(
            t for row in samples["samples_seconds_per_operator_by_round"] for t in row
        )
        * 1000,
    }


def report(cfg):
    paths(cfg)
    contexts = []
    for fixture in cfg["fixtures"]:
        cells = [checked_case(cfg, fixture, arm) for arm in cfg["order"]]
        default = [cell["mean_ms"] for cell in cells if cell["arm"].startswith("a")]
        forced = [cell["mean_ms"] for cell in cells if cell["arm"].startswith("b")]
        contexts.append(
            {
                "context": fixture["context"],
                "kv_storage_capacity": fixture["kv_storage_capacity"],
                "cells": cells,
                "forced_mean_latency_change_percent": (
                    statistics.mean(forced) / statistics.mean(default) - 1
                )
                * 100,
                "both_forced_faster_than_both_defaults": max(forced) < min(default),
            }
        )
    return {
        "status": "operator_range_completed",
        "scope": "Numerical reference and operator timings only; no model or production policy qualified.",
        "contexts": contexts,
    }


def run_cases(cfg, raw):
    owner = OUTPUT / "process.json"
    for _ in range(40):
        if owner.is_file():
            break
        time.sleep(0.05)
    if (
        not owner.is_file()
        or (OUTPUT / "outcome.json").exists()
        or json.loads(owner.read_text()) != {"pid": os.getpid(), "pgid": os.getpgrp()}
        or (OUTPUT / "config.yaml").read_bytes() != raw
    ):
        raise ValueError("range sweep requires its live resource supervisor")
    bundle, metal = paths(cfg)
    for fixture in cfg["fixtures"]:
        for arm in cfg["order"]:
            output = case_output(fixture, arm)
            output.mkdir()
            env = {
                **os.environ,
                "MEI_RUN_SDPA_PROBE": "1",
                "MEI_SDPA_PROBE_OUTPUT": str(output / "samples.json"),
                "MEI_SDPA_PROBE_METALLIB": str(metal),
                "MEI_SDPA_PROBE_DTYPE": fixture["dtype"],
                "MEI_SDPA_PROBE_CONTEXT": str(fixture["context"]),
                "MEI_SDPA_PROBE_CAPACITY": str(fixture["kv_storage_capacity"]),
                "MLX_SDPA_PROBE_TRACE": "1",
                "MLX_SDPA_PROBE_FORCE_TK1": cfg["arm_force_tk1"][arm],
            }
            with (output / "child.log").open("xb") as log:
                subprocess.run(
                    [
                        "/usr/bin/xcrun",
                        "xctest",
                        "-XCTest",
                        "MeiTests.QwenSDPAProbeTests/testVectorProbe",
                        str(bundle),
                    ],
                    env=env,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    check=True,
                )
            checked_case(cfg, fixture, arm)
            print(f"PASS {fixture['context']} {arm}", flush=True)
    return 0


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--child", action="store_true", help=argparse.SUPPRESS)
    p.add_argument("--verify", action="store_true")
    options = p.parse_args()
    cfg, raw = committed_native_config(DECLARATION)
    if (
        cfg["benchmark_scope"] != "mei-operator-diagnostic-v1"
        or cfg["diagnostic_only"] is not True
        or cfg["order"] != ["a1", "b1", "b2", "a2"]
        or cfg["arm_force_tk1"] != {"a1": "0", "b1": "1", "b2": "1", "a2": "0"}
        or [f["context"] for f in cfg["fixtures"]] != [8192, 16384, 24576, 32768, 65536]
    ):
        raise ValueError("range declaration differs from predeclared order or fixture")
    if options.child:
        return run_cases(cfg, raw)
    if options.verify:
        outcome = json.loads((OUTPUT / "outcome.json").read_text())
        invocation = json.loads((OUTPUT / "invocation.json").read_text())
        if (
            outcome["status"] != "passed"
            or outcome["returncode"] != 0
            or outcome["diagnostic_only"] is not True
            or (OUTPUT / "config.yaml").read_bytes() != raw
            or invocation["config_sha256"] != digest(DECLARATION)
        ):
            raise ValueError("range sweep does not have a passing terminal receipt")
        validate_resources(OUTPUT, cfg, invocation)
        print(json.dumps(report(cfg), indent=2))
        return 0
    check_ports()
    paths(cfg)
    environment = {
        "HOME": str(Path.home()),
        "PATH": "/usr/bin:/bin:/usr/sbin:/sbin",
        "DEVELOPER_DIR": "/Applications/Xcode.app/Contents/Developer",
    }
    os.environ.clear()
    os.environ.update(environment)

    def diagnostic_check(_out):
        return report(cfg)["status"] == "operator_range_completed"

    args = argparse.Namespace(
        output=OUTPUT, deadline=600, skip_context=True, skip_cache=True
    )
    return monitor_child(
        cfg,
        raw,
        args,
        [sys.executable, str(Path(__file__).resolve()), "--child"],
        diagnostic_check=diagnostic_check,
    )


if __name__ == "__main__":
    raise SystemExit(main())
