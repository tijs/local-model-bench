"""Retain the complete predeclared long-context cache screen, including negatives."""

import json
import statistics
from collections import defaultdict

from run_matrix import PREP, ROOT, audit


def main():
    manifest = json.loads((PREP / "long-allocator-screen.json").read_text())
    progress = json.loads((PREP / "long-allocator-progress.json").read_text())
    keys = ("model", "cell", "config", "output")
    if (
        progress["status"] != "measurement_cells_complete"
        or [{k: c[k] for k in keys} for c in progress["completed"]] != manifest["cells"]
    ):
        raise ValueError("require the exact four completed predeclared cells")
    baseline = None
    groups = defaultdict(list)
    cells = []
    checks = removed = 0
    for cell in manifest["cells"]:
        output = ROOT / cell["output"]
        checked = audit(output, baseline)
        if checked != json.loads((output / "qualification-audit.json").read_text()):
            raise ValueError("raw evidence no longer matches saved audit")
        baseline = checked["reference"]
        hashes = json.loads((output / "post-run-model-hashes.json").read_text())
        cleanup = json.loads((output / "owned-kv-cleanup.json").read_text())
        if not hashes["all_match"] or not all(r["matches"] for r in hashes["files"]):
            raise ValueError("model integrity failed")
        if not cleanup["server_exited"] or not cleanup["deleted"]:
            raise ValueError("cleanup incomplete")
        checks += len(hashes["files"])
        removed += cleanup["bytes"]
        q = json.loads((output / "qualification.json").read_text())
        limit = 536870912 if cell["cell"].startswith("a") else 1073741824
        if q["observed_allocator_cache_limit_bytes"] != limit:
            raise ValueError("effective cache limit mismatch")
        for context in ("short", "loaded"):
            rows = [
                r
                for r in q["rows"]
                if r["phase"] == "measured" and r["context"] == context
            ]
            if len(rows) != 5:
                raise ValueError("require all five measured repeats")
            groups[limit, context].append([r["decode_tps"] for r in rows])
        cells.append(cell | {"audit": checked})
    timings = []
    for (limit, context), processes in groups.items():
        if len(processes) != 2:
            raise ValueError("require both fresh processes per allowance")
        values = [v for p in processes for v in p]
        timings.append(
            {
                "allocator_cache_bytes": limit,
                "context": context,
                "n": len(values),
                "mean_tps": statistics.fmean(values),
                "process_means_tps": [statistics.fmean(p) for p in processes],
                "process_medians_tps": [statistics.median(p) for p in processes],
                "observations_tps": values,
            }
        )
    summary = {
        "status": "completed_negative_for_cache_headroom_as_sufficient_fix",
        "scope": "same frozen candidate runtime hypothesis screen;not task scores or stable qualification",
        "elapsed_seconds": progress["finished_epoch"] - progress["started_epoch"],
        "aggregation": "two processes equally weighted;all five measured repeats/context/process retained",
        "model_file_hash_checks": checks,
        "owned_kv_bytes_removed": removed,
        "all_normal_pressure": all(c["audit"]["all_normal_pressure"] for c in cells),
        "cells": cells,
        "timings": timings,
        "interpretation": "1GiB did not eliminate rate bands and has lower means than512MiB in this predeclared screen. No default promotion. The same candidate can also run near70/50TPS at512MiB;earlier deficits and all slow processes remain preserved. This does not diagnose the CPU patch or internal allocator cause.",
    }
    with (PREP / "long-allocator-summary.json").open("x") as stream:
        json.dump(summary, stream, indent=2)
        stream.write("\n")
    print(json.dumps({k: v for k, v in summary.items() if k != "cells"}, indent=2))


if __name__ == "__main__":
    main()
