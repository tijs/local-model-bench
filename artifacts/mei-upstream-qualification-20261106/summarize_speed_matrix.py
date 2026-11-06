"""Re-audit the complete predeclared campaign; retain every measured repeat."""

import argparse
import hashlib
import json
import statistics
from collections import defaultdict
from pathlib import Path

import yaml
from run_speed_matrix import PREP, ROOT, audit


def summarize(matrix, progress):
    expected_order = [
        (model, cell)
        for model in ("qwen", "ornith", "groot")
        for cell in ("a1", "b1", "b2", "a2")
    ]
    declared = matrix["cells"]
    if (
        [(c["model"], c["cell"]) for c in declared] != expected_order
        or progress["status"] != "measurement_cells_complete"
        or progress.get("current") is not None
        or [
            {k: c[k] for k in ("model", "cell", "config", "output")}
            for c in progress["completed"]
        ]
        != declared
    ):
        raise ValueError("requires the exact complete twelve-cell ABBA campaign")
    references = {}
    groups = defaultdict(list)
    cells = []
    for cell in declared:
        output = (ROOT / cell["output"]).resolve()
        config = (ROOT / cell["config"]).resolve()
        if not output.is_relative_to(ROOT / "artifacts") or not config.is_relative_to(
            ROOT / "configs"
        ):
            raise ValueError("campaign paths must remain in their owning directories")
        raw_config = config.read_bytes()
        invocation = json.loads((output / "invocation.json").read_text())
        if (output / "config.yaml").read_bytes() != raw_config or hashlib.sha256(
            raw_config
        ).hexdigest() != invocation["config_sha256"]:
            raise ValueError("configuration snapshot/hash differs from declaration")
        cfg = yaml.safe_load(raw_config)
        result = json.loads((output / "qualification.json").read_text())
        checked = audit(output, references.get(cell["model"]))
        if checked != json.loads((output / "qualification-audit.json").read_text()):
            raise ValueError("saved audit differs from raw evidence")
        references.setdefault(cell["model"], checked["reference"])
        expected_runtime = {
            "mei_source_commit": cfg["mei_source_commit"],
            "vmlx_commit": cfg["vmlx_commit"],
            "binary_sha256": cfg["mei_release_artifact"]["binary_sha256"],
            "metallib_sha256": cfg["mei_release_artifact"]["metallib_sha256"],
        }
        post = json.loads((output / "post-run-runtime-verification.json").read_text())
        if result["model"] != cfg["model"] or any(
            any(observed.get(k) != v for k, v in expected_runtime.items())
            for observed in (result["runtime_identity"], post)
        ):
            raise ValueError("runtime/model provenance mismatch")
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
        native = result["swift_acceptance"]
        status = result["status_samples"]
        active_status = [s for s in status if s["active_generations"] > 0]
        if (
            not native["passed"]
            or native["returncode"] != 0
            or native["expected_tests"] != 9
            or native["journal_requests"] != 9
            or not active_status
            or not all(s["ok"] for s in status)
        ):
            raise ValueError("live HTTP/status coverage incomplete")
        measured = [r for r in result["rows"] if r["phase"] == "measured"]
        for context in ("short", "loaded"):
            groups[cell["model"], cell["cell"][0], context].append(
                [r["decode_tps"] for r in measured if r["context"] == context]
            )
        cells.append(
            cell
            | {
                "audit": checked,
                "runtime": expected_runtime,
                "model_revision": cfg["source_revision"],
                "status_samples": len(status),
                "active_status_samples": len(active_status),
                "max_active_status_seconds": max(
                    s["elapsed_seconds"] for s in active_status
                ),
            }
        )
    timings = []
    for (model, arm, context), processes in groups.items():
        if len(processes) != 2 or any(len(p) != 5 for p in processes):
            raise ValueError("requires two processes and five repeats each")
        values = [v for p in processes for v in p]
        if any(not 0 < v < float("inf") for v in values):
            raise ValueError("invalid measured rate")
        timings.append(
            {
                "model": model,
                "arm": arm,
                "context": context,
                "n": len(values),
                "mean_tps": statistics.mean(values),
                "median_tps": statistics.median(values),
                "process_means_tps": [statistics.mean(p) for p in processes],
                "process_medians_tps": [statistics.median(p) for p in processes],
                "observations_tps": values,
            }
        )
    return {
        "status": "all_observables_passed_performance_review_pending",
        "scope": "Runtime qualification only; not scored tasks or stable promotion.",
        "weighting": "Two processes/version, five measured repeats/context each; equal process weight. Cold and warmup excluded, no best-repeat selection.",
        "limits": "ABBA observations include process/system variation. HTTP text/count/finish parity does not expose hidden token IDs. No statistical superiority or universal speedup claim.",
        "elapsed_seconds": progress["finished_epoch"] - progress["started_epoch"],
        "measured_requests": 120,
        "swift_http_tests": 108,
        "timings": timings,
        "cells": cells,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--matrix", type=Path, default=PREP / "speed-matrix.json")
    parser.add_argument(
        "--progress", type=Path, default=PREP / "speed-matrix-retry-progress.json"
    )
    parser.add_argument(
        "--output", type=Path, default=PREP / "speed-matrix-summary.json"
    )
    args = parser.parse_args()
    result = summarize(
        json.loads(args.matrix.read_text()), json.loads(args.progress.read_text())
    )
    with args.output.open("x") as stream:
        json.dump(result, stream, indent=2)
        stream.write("\n")
    print(json.dumps({k: v for k, v in result.items() if k != "cells"}, indent=2))


if __name__ == "__main__":
    main()
