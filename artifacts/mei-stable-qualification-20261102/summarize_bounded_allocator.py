"""Audit the stopped declared cohort without promoting incomplete arms."""

import hashlib
import json
import shlex
import statistics
from collections import defaultdict

import yaml
from run_matrix import PREP, ROOT, audit


def validate_identity(snapshot, declared, preflight_sha, result, post, server_log):
    """Output parity alone cannot distinguish an accidental runtime/arm swap."""
    if snapshot != declared or hashlib.sha256(snapshot).hexdigest() != preflight_sha:
        raise ValueError("saved config differs from the predeclared snapshot")
    cfg = yaml.safe_load(snapshot)
    command = shlex.split(cfg["benchmark_launch_command"])
    if result.get("command") != command:
        raise ValueError("observed launch command differs from the declared arm")
    artifact = cfg["mei_release_artifact"]
    expected = {
        "mei_source_commit": cfg["mei_source_commit"],
        "vmlx_commit": cfg["vmlx_commit"],
        "binary_sha256": artifact["binary_sha256"],
        "metallib_sha256": artifact["metallib_sha256"],
        "binary_path": command[command.index("--mei-binary") + 1],
    }
    for observed in (result.get("runtime_identity"), post):
        if not isinstance(observed, dict) or any(
            observed.get(key) != value for key, value in expected.items()
        ):
            raise ValueError("observed runtime identity differs from the declared arm")
    for key in (
        "VMLX_ENABLE_UNSAFE_COMPILE",
        "VMLX_QWEN35_COMPILE_DECODE_REGIONS",
        "VMLX_QWEN4_EXP_COMPILE_ROUTED_MOE",
        "VMLX_FUSED_GATE_UP_CACHE_LIMIT_BYTES",
    ):
        value = cfg["required_runner_environment"][key]
        line = f"mei: vmlx switch {key}={value} (source operator)"
        if line not in server_log.splitlines():
            raise ValueError("effective compilation setting differs from declared arm")


def main():
    matrix = json.loads((PREP / "bounded-allocator-matrix.json").read_text())
    progress = json.loads((PREP / "bounded-allocator-progress.json").read_text())
    keys = ("model", "cell", "config", "output")
    completed = [{k: c[k] for k in keys} for c in progress["completed"]]
    preflight = json.loads((PREP / "bounded-allocator-preflight.json").read_text())
    if preflight["status"] != "passed":
        raise ValueError("requires passed predeclaration identity checks")
    declared_hashes = {r["config"]: r["config_sha256"] for r in preflight["records"]}
    if (
        progress["status"] != "stopped_for_review"
        or completed != matrix["cells"][:15]
        or progress["current"] != matrix["cells"][15]
    ):
        raise ValueError("requires the exact 15 completed cells and stopped Ornith C2")
    baselines, groups, cells = {}, defaultdict(list), []
    totals = defaultdict(int)
    for cell in completed + [progress["current"]]:
        output = ROOT / cell["output"]
        result = json.loads((output / "qualification.json").read_text())
        outcome = json.loads((output / "outcome.json").read_text())
        validate_identity(
            (output / "config.yaml").read_bytes(),
            (ROOT / cell["config"]).read_bytes(),
            declared_hashes[cell["config"]],
            result,
            json.loads((output / "post-run-runtime-verification.json").read_text()),
            (output / "server.log").read_text(),
        )
        complete = cell in completed
        if complete:
            checked = audit(output, baselines.get(cell["model"]))
            if checked != json.loads((output / "qualification-audit.json").read_text()):
                raise ValueError("saved audit differs from raw evidence")
            baselines.setdefault(cell["model"], checked["reference"])
            for context in ("short", "loaded"):
                values = [
                    r["decode_tps"]
                    for r in result["rows"]
                    if r["phase"] == "measured" and r["context"] == context
                ]
                groups[cell["model"], cell["cell"][0], context].append(values)
        else:
            if (
                outcome["stop_reason"] != "sustained warning memory pressure"
                or result["status"] != "failed"
                or len(result["rows"]) != 3
                or any(r["phase"] == "measured" for r in result["rows"])
            ):
                raise ValueError("unexpected partial-cell outcome or coverage")
            if any(
                r["observable"] != baselines[cell["model"]][r["context"]]
                for r in result["rows"]
            ):
                raise ValueError("partial-cell outputs differ from control")
        hashes = json.loads((output / "post-run-model-hashes.json").read_text())
        cleanup = json.loads((output / "owned-kv-cleanup.json").read_text())
        if not hashes["all_match"] or not all(r["matches"] for r in hashes["files"]):
            raise ValueError("model hash check failed")
        if not cleanup["deleted"] or not cleanup["server_exited"]:
            raise ValueError("terminal owned KV cleanup incomplete")
        resources = [
            json.loads(x) for x in (output / "resources.jsonl").read_text().splitlines()
        ]
        warnings = sum(r["kernel_pressure_level"] == 2 for r in resources)
        max_warning_streak = streak = 0
        for row in resources:
            streak = streak + 1 if row["kernel_pressure_level"] == 2 else 0
            max_warning_streak = max(max_warning_streak, streak)
        totals["raw_requests"] += len(result["rows"])
        totals["measured_requests"] += sum(
            r["phase"] == "measured" for r in result["rows"]
        )
        totals["model_file_hash_checks"] += len(hashes["files"])
        totals["owned_kv_bytes_removed"] += cleanup["bytes"]
        totals["warning_samples"] += warnings
        if result.get("swift_acceptance_required"):
            native = result["swift_acceptance"]
            if not native["passed"] or native["returncode"] != 0:
                raise ValueError("declared Swift client did not pass")
            totals["swift_http_tests"] += native["expected_tests"]
        cells.append(
            cell
            | {
                "status": outcome["status"],
                "stop_reason": outcome.get("stop_reason"),
                "raw_requests": len(result["rows"]),
                "warning_samples": warnings,
                "maximum_warning_streak": max_warning_streak,
                "swap_growth_mib": max(r["swap_used_mib"] for r in resources)
                - min(r["swap_used_mib"] for r in resources),
                "all_observed_outputs_match_control": True,
                "model_hashes_match": True,
                "owned_cache_removed": True,
            }
        )
    if (
        totals["raw_requests"],
        totals["measured_requests"],
        totals["swift_http_tests"],
    ) != (213, 150, 54):
        raise ValueError("coverage totals differ from the stopped cohort")
    timings = []
    for (model, arm, context), processes in groups.items():
        if any(len(p) != 5 for p in processes) or len(processes) > 2:
            raise ValueError("invalid measured process coverage")
        full = len(processes) == 2
        timings.append(
            {
                "model": model,
                "arm": arm,
                "context": context,
                "complete_arm": full,
                "process_means_tps": [statistics.fmean(p) for p in processes],
                "observations_tps": processes,
                "equal_process_mean_tps": statistics.fmean(
                    statistics.fmean(p) for p in processes
                )
                if full
                else None,
            }
        )
    summary = {
        "status": "stopped_for_memory_review",
        "scope": "partial runtime qualification; no full score or stable-release qualification",
        "completed_cells": 15,
        "interrupted_cells": 1,
        "unstarted_cells": matrix["cells"][16:],
        "full_native_gates": "all three remain unstarted",
        "profile": "17/30000 input tokens;128 greedy output;prefill256;512MiB allocator/prefix;auto total limit",
        "totals": dict(totals),
        "cells": cells,
        "timings": timings,
        "limits": [
            "Only complete two-process arms have averages; incomplete Ornith arms remain unranked.",
            "Keep every measured observation and all cold/warmup evidence; two processes do not establish confidence.",
            "Guards and budgets were not relaxed; review pressure and mixed performance before any retry or release.",
            "Stable distribution, eight new task runs and final four-model figures remain pending.",
        ],
    }
    with (PREP / "bounded-allocator-summary.json").open("x") as stream:
        json.dump(summary, stream, indent=2)
        stream.write("\n")
    print(
        json.dumps(
            {k: v for k, v in summary.items() if k not in ("cells", "timings")},
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
