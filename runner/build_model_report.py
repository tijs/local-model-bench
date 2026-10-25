#!/usr/bin/env python3
"""Report native model checks separately from historical application scores."""

from __future__ import annotations

import json
import math
from collections import defaultdict
from pathlib import Path
from statistics import median

REPO = Path(__file__).resolve().parents[1]
SCOPE = "model-only-v1"


def render(rows):
    groups = defaultdict(list)
    for row in rows:
        if row.get("benchmark_scope") == SCOPE:
            key = (
                row["model"],
                row.get("inference_engine", "unknown"),
                row.get("config_hash"),
                row.get("runner_git_sha"),
                row["suite"],
                row.get("generation_profile"),
            )
            groups[key].append(row)
    lines = [
        "# Model-only benchmark",
        "",
        (
            "Native HTTP model behavior with mocked tools. "
            "No coding-agent, Peixinho application, or historical composite score is claimed."
        ),
        "",
        "Hermes-specific workloads are retired. Historical rows remain in log.jsonl and the legacy leaderboard.",
        "",
        "| Model | Engine | Config | Runner | Suite | Profile | Passed / rows | Harness errors | Median output tok/s (wall) | Median TTFT s |",
        "|---|---|---|---|---|---|---:|---:|---:|---:|",
    ]
    for key, data in sorted(
        groups.items(), key=lambda item: tuple(str(x) for x in item[0])
    ):
        model, engine, config, runner, suite, profile = key
        scored = [r for r in data if not r.get("harness_error")]

        def metric(name, scored=scored):
            values = [
                r[name]
                for r in scored
                if isinstance(r.get(name), (int, float)) and math.isfinite(r[name])
            ]
            return f"{median(values):.2f}" if values else "—"

        lines.append(
            f"| {model} | {engine} | {config} | {(runner or 'unknown')[:12]} | {suite} "
            f"| {profile or 'deterministic'} | {sum(r.get('pass') is True for r in scored)}/{len(data)} "
            f"| {sum(bool(r.get('harness_error')) for r in data)} "
            f"| {metric('tokens_per_second')} | {metric('ttft_seconds')} |"
        )
    lines += [
        "",
        (
            "Groups retain configuration and runner identity. Sanity is a gate; model_tools uses a neutral "
            "prompt and six simulated tools. Output rate divides completion tokens by total task wall time, including prefill and tool turns. Single trials and timing samples do not establish a front-runner."
        ),
        "",
    ]
    return "\n".join(lines)


def main():
    path = REPO / "results/log.jsonl"
    rows = (
        [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
        if path.exists()
        else []
    )
    (REPO / "results/MODEL_ONLY.md").write_text(render(rows))


if __name__ == "__main__":
    main()
