"""Compare completed Pi coding runs that share their tasks and execution protocol."""

import argparse
import itertools
import json
from pathlib import Path
from statistics import median


def compare(paths):
    runs = {}
    protocols = set()
    for path in paths:
        manifest = json.loads((path / "manifest.json").read_text())
        if not manifest["complete"]:
            raise ValueError(f"Incomplete run: {path}")
        protocols.add(manifest["fingerprint"])
        label = manifest["profile"]
        if label in runs:
            raise ValueError(f"Duplicate profile {label}")
        rows = json.loads((path / "results.json").read_text())
        runs[label] = {r["task"]: r for r in rows}
        if len(rows) != len(runs[label]):
            raise ValueError("Duplicate task")
    if len(protocols) != 1 or len({frozenset(r) for r in runs.values()}) != 1:
        raise ValueError("Mismatched task set or protocol")
    return runs


def table(runs):
    labels = list(runs)
    lines = ["| Task | " + " | ".join(labels) + " |", "|---|" + "---:|" * len(labels)]
    for task in next(iter(runs.values())):
        cells = []
        for label in labels:
            r = runs[label][task]
            cells.append(
                f"pass · {r['first_pass_s']:.1f}s"
                if r["passed"]
                else ("time limit" if r["timed_out"] else "fail")
            )
        lines.append("| " + task + " | " + " | ".join(cells) + " |")
    lines.append(
        "| **Passing final patches** | "
        + " | ".join(
            str(sum(r["passed"] for r in rows.values())) + "/" + str(len(rows))
            for rows in runs.values()
        )
        + " |"
    )
    for left, right in itertools.combinations(labels, 2):
        matched = [
            (a["first_pass_s"], runs[right][k]["first_pass_s"])
            for k, a in runs[left].items()
            if a["passed"] and runs[right][k]["passed"]
        ]
        if matched:
            delta = median(b - a for a, b in matched)
            lines += [
                "",
                f"{left} vs {right}: {len(matched)} shared successes. Median paired time difference (right minus left) {delta:+.1f}s. {left} was faster on {sum(a < b for a, b in matched)}.",
            ]
    return "\n".join(lines)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("runs", nargs="+", type=Path)
    print(table(compare(p.parse_args().runs)))
