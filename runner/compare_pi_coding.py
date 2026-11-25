"""Compare completed Pi coding runs that share their tasks and execution protocol."""

import argparse
import hashlib
import itertools
import json
from pathlib import Path
from statistics import median


def compare(paths):
    runs = {}
    protocols = set()
    hosts = set()
    for path in paths:
        manifest = json.loads((path / "manifest.json").read_text())
        if not manifest["complete"]:
            raise ValueError(f"Incomplete run: {path}")
        protocol = manifest["protocol"]
        fingerprint = hashlib.sha256(
            json.dumps(protocol, sort_keys=True).encode()
        ).hexdigest()
        if fingerprint != manifest["fingerprint"]:
            raise ValueError(f"Protocol fingerprint mismatch: {path}")
        protocols.add(fingerprint)
        hosts.add(json.dumps(manifest["host"], sort_keys=True))
        label = manifest["profile"]
        if label in runs:
            raise ValueError(f"Duplicate profile {label}")
        rows = json.loads((path / "results.json").read_text())
        runs[label] = {r["task"]: r for r in rows}
        suite = protocol.get("suite", "pi-coding-v1")
        declared = {
            Path(name).stem
            for name in protocol["sources"]
            if name.startswith(f"tasks/{suite}/") and name.endswith(".yaml")
        }
        if declared != set(runs[label]):
            raise ValueError(f"Missing or unexpected task results: {path}")
        if len(rows) != len(runs[label]):
            raise ValueError("Duplicate task")
    if len(protocols) != 1 or len({frozenset(r) for r in runs.values()}) != 1:
        raise ValueError("Mismatched task set or protocol")
    return runs, len(hosts) == 1


def table(runs, same_host):
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
    if not same_host:
        lines += ["", "Host specifications differ. Paired timing comparisons omitted."]
        return "\n".join(lines)
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
    print(table(*compare(p.parse_args().runs)))
