"""Render the matched-method Mei 0.10/0.11 task delta from audited cohorts."""

import json
import sys
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "runner"))
from build_four_model_summary import aggregate_points, load_points

BASELINE = "results/four-model-mei010-comparison.json"
CURRENT = "results/four-model-mei011-comparison.json"
METRICS = (
    "household_passed",
    "python_passed",
    "task_seconds",
    "wall_minutes",
    "wired_increase_gib",
)


def compare(root: Path, baseline: dict, current: dict) -> dict:
    for key in ("benchmark_release", "release_commit", "models", "seeds"):
        if baseline[key] != current[key]:
            raise ValueError(f"cohorts differ in {key}")
    if len(baseline["models"]) != 4 or baseline["seeds"] != [17, 29]:
        raise ValueError("requires the declared four profiles and two seeds")
    labels = list(baseline["models"].values())
    points = [load_points(root, spec) for spec in (baseline, current)]
    ids = [
        {getattr(p, key) for p in cohort for key in ("household_run", "python_run")}
        for cohort in points
    ]
    if any(len(group) != 16 for group in ids) or ids[0] & ids[1]:
        raise ValueError("each cohort needs eight distinct fresh runs and two tracks")
    averages = [
        {p.label: asdict(p) for p in aggregate_points(cohort, labels)}
        for cohort in points
    ]
    pairs = [{(p.label, p.seed): p for p in cohort} for cohort in points]
    rows = []
    for label in labels:
        old, new = (group[label] for group in averages)
        if old["engine"] != new["engine"]:
            raise ValueError(f"engine changed for {label}")
        seeds = []
        for seed in (17, 29):
            left, right = (group[label, seed] for group in pairs)
            seeds.append(
                {
                    "seed": seed,
                    "household_change": right.household - left.household,
                    "python_change": right.python - left.python,
                    "baseline_review": left.supervision,
                    "current_review": right.supervision,
                }
            )
        rows.append(
            {
                "label": label,
                "engine": old["engine"],
                "baseline": {key: old[key] for key in METRICS},
                "current": {key: new[key] for key in METRICS},
                "change": {
                    key: new[key] - old[key]
                    if old[key] is not None and new[key] is not None
                    else None
                    for key in METRICS
                },
                "seeds": seeds,
            }
        )
    return {"method": baseline["benchmark_release"], "models": rows}


def render(result: dict) -> str:
    lines = [
        "# Mei 0.10.0 to 0.11.0: scored workflow comparison",
        "",
        f"Both cohorts used **{result['method']}**, two seeds per profile and the same task coverage. Logics-SWE keeps its pinned llama.cpp runtime as a control.",
        "",
        "| Profile | Household passes | Python passes | Mean task time | Mean full-run time | Peak wired increase |",
        "|---|---:|---:|---:|---:|---:|",
    ]

    def delta(row, key, digits, unit):
        old, new, change = (
            row[field][key] for field in ("baseline", "current", "change")
        )
        if change is None:
            return "unavailable"
        return f"{old:.{digits}f} → {new:.{digits}f} {unit} ({change:+.{digits}f})"

    for row in result["models"]:
        values = [
            delta(row, "household_passed", 0, "/ 24"),
            delta(row, "python_passed", 0, "/ 6"),
            delta(row, "task_seconds", 2, "s"),
            delta(row, "wall_minutes", 2, "min"),
            delta(row, "wired_increase_gib", 2, "GiB"),
        ]
        lines.append("| " + " | ".join([row["label"], *values]) + " |")
    lines.extend(
        [
            "",
            "Changes are current minus baseline. Two seeds do not isolate runtime effects. Groot's allocator pool also changed, and weights moved to Expansion before the current cohort. Full-run time includes model load; GGUF can also read file-backed weights during tasks. Wired increase is a host measurement, not the model's total memory.",
            "",
            "| Profile | Seed | Household change | Python change | Audits |",
            "|---|---:|---:|---:|---|",
        ]
    )
    for row in result["models"]:
        for seed in row["seeds"]:
            left, right = (seed[f"{key}_review"] for key in ("baseline", "current"))
            lines.append(
                f"| {row['label']} | {seed['seed']} | {seed['household_change']:+d} | "
                f"{seed['python_change']:+d} | [Earlier](../{left}/README.md) · [Current](../{right}/README.md) |"
            )
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    baseline, current = (
        json.loads((ROOT / name).read_text()) for name in (BASELINE, CURRENT)
    )
    result = compare(ROOT, baseline, current)
    outputs = {
        ROOT / "results/MEI011_DELTA.md": render(result),
        ROOT / "results/mei011-scored-delta.json": json.dumps(result, indent=2) + "\n",
    }
    if any(path.exists() for path in outputs):
        raise FileExistsError("refuse to replace published comparison evidence")
    for path, content in outputs.items():
        with path.open("x") as stream:
            stream.write(content)


if __name__ == "__main__":
    main()
