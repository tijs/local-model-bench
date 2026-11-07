"""Audit saved request/phase latencies after a model's complete ABBA group."""

import argparse
import json
import math
import statistics
from collections import defaultdict

from review_batched_model_speed import review
from run_speed_matrix import PREP, ROOT


def latencies(model, campaign="batched"):
    audited = review(model, campaign)
    groups = defaultdict(list)
    for cell in audited["cells"]:
        result = json.loads((ROOT / cell["output"] / "qualification.json").read_text())
        for context in ("short", "loaded"):
            rows = [
                r
                for r in result["rows"]
                if r["phase"] == "measured" and r["context"] == context
            ]
            metrics = {
                "request_wall_seconds": [r["elapsed_seconds"] for r in rows],
                "backend_prefill_seconds": [
                    r["response"]["usage"]["prefill_ms"] / 1000 for r in rows
                ],
                "backend_generation_seconds": [
                    r["response"]["usage"]["generate_ms"] / 1000 for r in rows
                ],
            }
            for metric, values in metrics.items():
                if len(values) != 5 or any(
                    not math.isfinite(v) or v < 0 for v in values
                ):
                    raise ValueError(
                        "requires five finite nonnegative measurements per process"
                    )
                groups[cell["cell"][0], context, metric].append(values)
    timings = []
    for (arm, context, metric), processes in groups.items():
        if len(processes) != 2:
            raise ValueError("requires two processes/version")
        values = [v for p in processes for v in p]
        timings.append(
            {
                "arm": arm,
                "context": context,
                "metric": metric,
                "n": 10,
                "process_weights": [0.5, 0.5],
                "mean_seconds": statistics.mean(values),
                "process_means_seconds": [statistics.mean(p) for p in processes],
                "observations_seconds": values,
            }
        )
    comparisons = []
    for context in ("short", "loaded"):
        for metric in (
            "request_wall_seconds",
            "backend_prefill_seconds",
            "backend_generation_seconds",
        ):
            a = next(
                r
                for r in timings
                if (r["arm"], r["context"], r["metric"]) == ("a", context, metric)
            )
            b = next(
                r
                for r in timings
                if (r["arm"], r["context"], r["metric"]) == ("b", context, metric)
            )
            if a["mean_seconds"] <= 0:
                raise ValueError(
                    "control mean must be positive for relative comparison"
                )
            comparisons.append(
                {
                    "context": context,
                    "metric": metric,
                    "mean_change_percent_positive_is_slower": 100
                    * (b["mean_seconds"] / a["mean_seconds"] - 1),
                    "candidate_process_means_faster_than_both_controls": max(
                        b["process_means_seconds"]
                    )
                    < min(a["process_means_seconds"]),
                    "candidate_process_means_slower_than_both_controls": min(
                        b["process_means_seconds"]
                    )
                    > max(a["process_means_seconds"]),
                }
            )
    return {
        "status": "complete_model_latency_observations_review_required",
        "model": model,
        "scope": "Saved measured requests only, all repeats and equal process weights. No new model requests. Request wall time complements decode TPS; backend phase counters retain their native conventions and must not be summed as independent intervals. Not startup time, task quality, application acceptance or stable promotion.",
        "limits": "ABBA process/system variation remains; two processes/version do not establish confidence intervals. Backend phase names alone do not prove identical phase boundaries. Aggregate runtime/storage migration, not an isolated patch ablation.",
        "timings": timings,
        "comparisons": comparisons,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", choices=("qwen", "ornith", "groot"), required=True)
    parser.add_argument("--campaign", choices=("batched", "apple-main"), default="batched")
    args = parser.parse_args()
    result = latencies(args.model, args.campaign)
    with (PREP / f"{args.model}-{args.campaign}-latency-review.json").open("x") as stream:
        json.dump(result, stream, indent=2)
        stream.write("\n")
    print(f"Audited {args.model} saved request and backend phase latencies")


if __name__ == "__main__":
    main()
