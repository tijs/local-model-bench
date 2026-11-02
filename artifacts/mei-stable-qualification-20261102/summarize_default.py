"""Audit the original Groot cells and fresh Qwen/Ornith continuation together."""

import json
import statistics
from collections import defaultdict

from run_matrix import PREP, ROOT, audit


def main():
    original = json.loads((PREP / "default-matrix.json").read_text())
    interrupted = json.loads((PREP / "default-progress.json").read_text())
    continued = json.loads((PREP / "default-continuation1-matrix.json").read_text())
    finished = json.loads((PREP / "default-continuation1-progress.json").read_text())
    keys = ("model", "cell", "config", "output")
    first = [{k: row[k] for k in keys} for row in interrupted["completed"]]
    rest = [{k: row[k] for k in keys} for row in finished["completed"]]
    if (
        interrupted["status"] != "stopped_for_review"
        or first != original["cells"][:4]
        or finished["status"] != "measurement_cells_complete"
        or rest != continued["cells"]
        or len(rest) != 8
        or [(c["model"], c["cell"]) for c in first + rest]
        != [(c["model"], c["cell"]) for c in original["cells"]]
    ):
        raise ValueError(
            "requires the exact reviewed interruption and completed continuation"
        )
    baselines = {}
    groups = defaultdict(list)
    cells = []
    totals = defaultdict(int)
    for cell in first + rest:
        output = ROOT / cell["output"]
        checked = audit(output, baselines.get(cell["model"]))
        saved = json.loads((output / "qualification-audit.json").read_text())
        if checked != saved:
            raise ValueError("saved audit differs from raw evidence")
        baselines.setdefault(cell["model"], checked["reference"])
        hashes = json.loads((output / "post-run-model-hashes.json").read_text())
        cleanup = json.loads((output / "owned-kv-cleanup.json").read_text())
        if not hashes["all_match"] or not all(r["matches"] for r in hashes["files"]):
            raise ValueError("post-run model integrity failed")
        if not cleanup["deleted"] or not cleanup["server_exited"]:
            raise ValueError("owned cache preservation/cleanup incomplete")
        result = json.loads((output / "qualification.json").read_text())
        for context in ("short", "loaded"):
            values = [
                r["decode_tps"]
                for r in result["rows"]
                if r["phase"] == "measured" and r["context"] == context
            ]
            groups[(cell["model"], cell["cell"][0], context)].append(values)
        totals["raw_timing_requests"] += len(result["rows"])
        totals["measured_requests"] += sum(
            r["phase"] == "measured" for r in result["rows"]
        )
        totals["model_file_hash_checks"] += len(hashes["files"])
        totals["owned_kv_bytes_removed"] += cleanup["bytes"]
        totals["resource_samples"] += checked["resource_samples"]
        native = result.get("swift_acceptance")
        if result.get("swift_acceptance_required"):
            if not native["passed"] or native["returncode"] != 0:
                raise ValueError("declared Swift client failed")
            totals["swift_http_tests"] += native["expected_tests"]
        cells.append(cell | {"audit": checked})
    if totals["measured_requests"] != 120 or totals["swift_http_tests"] != 27:
        raise ValueError("incomplete predeclared observation/client coverage")
    timings = []
    for (model, arm, context), processes in groups.items():
        if len(processes) != 2 or any(len(p) != 5 for p in processes):
            raise ValueError("require two processes, five measurements each")
        values = [v for p in processes for v in p]
        timings.append(
            {
                "model": model,
                "arm": arm,
                "context": context,
                "n": len(values),
                "mean_tps": statistics.fmean(values),
                "median_tps": statistics.median(values),
                "process_means_tps": [statistics.fmean(p) for p in processes],
                "process_medians_tps": [statistics.median(p) for p in processes],
                "observations_tps": values,
            }
        )
    summary = {
        "status": "observables_passed_performance_review_pending",
        "scope": "runtime qualification only; no stable release or task score",
        "excluded_interruption": "artifacts/mei-stable-qwen-default-a1-20261102",
        "profile": "compilation enabled;512MiB allocator/prefix limits;17/30000-token input;128-token greedy output",
        "aggregation": "equal weight per fresh process,each with five measured observations;all declared completed processes retained",
        "totals": dict(totals),
        "cells": cells,
        "timings": timings,
        "open_gates": [
            "Review material Qwen throughput deficit and Ornith process variation before stable/default promotion.",
            "Complete three full native tools/history/cache/exact65536 gates.",
            "Publish and verify stable distribution,then eight fresh scored runs and four-model short/long-context figures.",
        ],
    }
    with (PREP / "default-summary.json").open("x") as stream:
        json.dump(summary, stream, indent=2)
        stream.write("\n")
    print(json.dumps({k: v for k, v in summary.items() if k != "cells"}, indent=2))


if __name__ == "__main__":
    main()
