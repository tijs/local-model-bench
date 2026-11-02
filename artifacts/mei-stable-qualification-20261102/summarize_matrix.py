"""Audit all predeclared cells and derive a timing report without scoring rows."""

import json
import statistics
from collections import defaultdict

from run_matrix import PREP, ROOT, audit


def main():
    declared = json.loads((PREP / "matrix.json").read_text())
    progress = json.loads((PREP / "matrix-progress.json").read_text())
    if (
        progress["status"] != "measurement_cells_complete"
        or len(progress["completed"]) != len(declared["cells"])
        or [
            {k: row[k] for k in ("model", "cell", "config", "output")}
            for row in progress["completed"]
        ]
        != declared["cells"]
    ):
        raise ValueError("requires the exact completed predeclared campaign")
    baselines = {}
    groups = defaultdict(list)
    cells = []
    totals = defaultdict(int)
    for cell in declared["cells"]:
        output = ROOT / cell["output"]
        checked = audit(output, baselines.get(cell["model"]))
        saved = json.loads((output / "qualification-audit.json").read_text())
        if checked != saved:
            raise ValueError("saved audit no longer matches raw evidence")
        baselines.setdefault(cell["model"], checked["reference"])
        hashes = json.loads((output / "post-run-model-hashes.json").read_text())
        cleanup = json.loads((output / "owned-kv-cleanup.json").read_text())
        if not hashes["all_match"] or not all(r["matches"] for r in hashes["files"]):
            raise ValueError("post-run model integrity did not pass")
        if not cleanup["deleted"] or not cleanup["server_exited"]:
            raise ValueError("owned cache preservation/cleanup is incomplete")
        result = json.loads((output / "qualification.json").read_text())
        measured = [r for r in result["rows"] if r["phase"] == "measured"]
        for context in ("short", "loaded"):
            values = [r["decode_tps"] for r in measured if r["context"] == context]
            groups[(cell["model"], cell["cell"][0], context)].append(values)
        totals["raw_timing_requests"] += len(result["rows"])
        totals["measured_requests"] += len(measured)
        totals["model_file_hash_checks"] += len(hashes["files"])
        totals["owned_kv_bytes_removed"] += cleanup["bytes"]
        totals["resource_samples"] += checked["resource_samples"]
        if result.get("swift_acceptance_required"):
            native = result["swift_acceptance"]
            if not native["passed"] or native["returncode"] != 0:
                raise ValueError("a declared native client did not pass")
            totals["swift_http_tests"] += native["expected_tests"]
        cells.append(cell | {"audit": checked})
    summary = {
        "status": "observables_passed_performance_review_pending",
        "scope": "runtime qualification, not a scored benchmark or stable release",
        "elapsed_seconds": progress["finished_epoch"] - progress["started_epoch"],
        "totals": dict(totals),
        "all_normal_pressure": all(c["audit"]["all_normal_pressure"] for c in cells),
        "cells": cells,
        "timings": [
            {
                "model": model,
                "arm": arm,
                "context": context,
                "n": len(values),
                "median_tps": statistics.median(values),
                "mean_tps": statistics.mean(values),
                "sample_stdev_tps": statistics.stdev(values),
                "process_medians_tps": [statistics.median(p) for p in processes],
                "observations_tps": values,
            }
            for (model, arm, context), processes in groups.items()
            for values in [[value for process in processes for value in process]]
        ],
        "open_gates": [
            "Investigate Qwen/Ornith process-level throughput variation and assess regressions; no generalized decode-speed claim.",
            "Compare the API-correct control and candidate at the same public compilation-enabled profile before default promotion.",
            "Complete each separately predeclared native tools/history/cache/exact-context gate.",
            "Publish and verify stable distribution, then run and publish the eight scored front-runner repeats.",
        ],
    }
    if totals["measured_requests"] != 180 or totals["swift_http_tests"] != 54:
        raise ValueError("declared observation/native coverage is incomplete")
    with (PREP / "matrix-summary.json").open("x") as stream:
        json.dump(summary, stream, indent=2)
        stream.write("\n")
    print(json.dumps({k: v for k, v in summary.items() if k != "cells"}, indent=2))


if __name__ == "__main__":
    main()
