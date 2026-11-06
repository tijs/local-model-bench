"""Re-audit one complete model ABBA group; never promote partial observations."""

import argparse
import hashlib
import json
import statistics
import sys
from collections import defaultdict

import yaml
from run_speed_matrix import PREP, ROOT, audit

sys.path.insert(0, str(ROOT / "runner"))
from build_context_speed_cohort import validate_resources


def review(model):
    matrix = json.loads((PREP / "batched-speed-matrix.json").read_text())
    progress = json.loads((PREP / "batched-speed-progress.json").read_text())
    cells = [c for c in matrix["cells"] if c["model"] == model]
    completed = [c["cell"] for c in progress["completed"] if c["model"] == model]
    if [c["cell"] for c in cells] != ["a1", "b1", "b2", "a2"] or completed != [
        "a1",
        "b1",
        "b2",
        "a2",
    ]:
        raise ValueError("requires all four completed predeclared model cells")
    reference = None
    groups = defaultdict(list)
    checked_cells = []
    hash_checks = 0
    model_identity = None
    model_files = None
    prompts = None
    for cell in cells:
        output = (ROOT / cell["output"]).resolve()
        config = (ROOT / cell["config"]).resolve()
        if not output.is_relative_to(ROOT / "artifacts") or not config.is_relative_to(
            ROOT / "configs"
        ):
            raise ValueError(
                "evidence must stay in its declared repository directories"
            )
        raw = config.read_bytes()
        cfg = yaml.safe_load(raw)
        identity = tuple(
            cfg[k]
            for k in (
                "model",
                "source_revision",
                "quant_family",
                "context_cap",
                "prefill_step_size",
                "temperature",
                "model_bytes",
            )
        )
        current_prompts = json.loads((output / "prompts.json").read_text())
        if model_identity is None:
            model_identity, prompts = identity, current_prompts
        elif identity != model_identity or current_prompts != prompts:
            raise ValueError(
                "model revision/precision/profile or exact prompts differ across arms"
            )
        invocation = json.loads((output / "invocation.json").read_text())
        if (
            raw != (output / "config.yaml").read_bytes()
            or hashlib.sha256(raw).hexdigest() != invocation["config_sha256"]
        ):
            raise ValueError("configuration snapshot or hash mismatch")
        validate_resources(output, cfg, invocation)
        checked = audit(output, reference)
        if checked != json.loads((output / "qualification-audit.json").read_text()):
            raise ValueError("saved audit differs from raw evidence")
        reference = checked["reference"]
        q = json.loads((output / "qualification.json").read_text())
        post = json.loads((output / "post-run-runtime-verification.json").read_text())
        expected = {
            "mei_source_commit": cfg["mei_source_commit"],
            "vmlx_commit": cfg["vmlx_commit"],
            "binary_sha256": cfg["mei_release_artifact"]["binary_sha256"],
            "metallib_sha256": cfg["mei_release_artifact"]["metallib_sha256"],
        }
        if q["model"] != cfg["model"] or any(
            any(r.get(k) != v for k, v in expected.items())
            for r in (q["runtime_identity"], post)
        ):
            raise ValueError("runtime or model identity mismatch")
        hashes = json.loads((output / "post-run-model-hashes.json").read_text())
        cleanup = json.loads((output / "owned-kv-cleanup.json").read_text())
        if (
            not hashes["all_match"]
            or not hashes["files"]
            or not all(r["matches"] for r in hashes["files"])
            or not cleanup["deleted"]
            or not cleanup["server_exited"]
        ):
            raise ValueError("model integrity or owned cleanup incomplete")
        files = tuple(
            sorted((r["file"], r["bytes"], r["sha256"]) for r in hashes["files"])
        )
        if model_files is None:
            model_files = files
        elif files != model_files:
            raise ValueError("post-run model contents differ across arms")
        http = q["swift_acceptance"]
        status = q["status_samples"]
        active = [r for r in status if r["active_generations"] > 0]
        if (
            not http["passed"]
            or http["returncode"] != 0
            or http["expected_tests"] != 9
            or http["journal_requests"] != 9
            or not active
            or not all(r["ok"] for r in status)
        ):
            raise ValueError("live API or status coverage incomplete")
        hash_checks += len(hashes["files"])
        for context in ("short", "loaded"):
            values = [
                r["decode_tps"]
                for r in q["rows"]
                if r["phase"] == "measured" and r["context"] == context
            ]
            if len(values) != 5 or any(not 0 < v < float("inf") for v in values):
                raise ValueError(
                    "requires five finite positive observations per context/process"
                )
            groups[cell["cell"][0], context].append(values)
        checked_cells.append(
            cell
            | {
                "audit": checked,
                "runtime": expected,
                "status_samples": len(status),
                "active_status_samples": len(active),
                "max_active_status_seconds": max(r["elapsed_seconds"] for r in active),
            }
        )
    timings = []
    for (arm, context), processes in groups.items():
        if len(processes) != 2:
            raise ValueError("requires two processes per version")
        values = [v for p in processes for v in p]
        timings.append(
            {
                "arm": arm,
                "context": context,
                "n": 10,
                "process_weights": [0.5, 0.5],
                "mean_tps": statistics.mean(values),
                "median_tps": statistics.median(values),
                "process_means_tps": [statistics.mean(p) for p in processes],
                "observations_tps": values,
            }
        )
    comparisons = []
    for context in ("short", "loaded"):
        a = next(r for r in timings if r["arm"] == "a" and r["context"] == context)
        b = next(r for r in timings if r["arm"] == "b" and r["context"] == context)
        comparisons.append(
            {
                "context": context,
                "mean_change_percent": 100 * (b["mean_tps"] / a["mean_tps"] - 1),
                "candidate_process_means_above_both_controls": min(
                    b["process_means_tps"]
                )
                > max(a["process_means_tps"]),
                "candidate_process_means_below_both_controls": max(
                    b["process_means_tps"]
                )
                < min(a["process_means_tps"]),
            }
        )
    return {
        "status": "complete_model_observables_passed_performance_review_required",
        "model": model,
        "scope": "Runtime/API qualification only. All56 observable rows match;40 measured requests and36 live API cases. Other models and final review remain required; not scored tasks or stable promotion.",
        "limits": "All repeats retained, equal process weights, no cold/warmup selection. HTTP observables do not expose hidden IDs. Process/system variation remains; no statistical superiority or universal speedup claim. Aggregate runtime/storage migration, not isolated patch attribution.",
        "model_file_hash_checks": hash_checks,
        "cells": checked_cells,
        "timings": timings,
        "comparisons": comparisons,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", choices=("qwen", "ornith", "groot"), required=True)
    args = parser.parse_args()
    result = review(args.model)
    output = PREP / f"{args.model}-batched-complete-speed-review.json"
    with output.open("x") as stream:
        json.dump(result, stream, indent=2)
        stream.write("\n")
    print(
        f"Audited all four {args.model} cells; no stable promotion or task-score claim"
    )


if __name__ == "__main__":
    main()
