"""Report stand-in workflows separately from model-only and actual app results."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from statistics import median

from standin_domain import SCOPE, Json


def render(rows: list[Json], manifests: list[Json]) -> str:
    lines = [
        "# Peixinho stand-in workflows",
        "",
        "Synthetic household state and bounded domain tools. **Not Peixinho app acceptance evidence.**",
        "",
        "Fresh simulator state per trial does not imply independent model samples; backend cache policy is recorded per run.",
        "",
        "| Run | Model / engine | Config / runner | Partition / profile | Status | Executed / planned | Missing | Passed | Invalid calls | Unsafe attempts | Critical safety failures |",
        "|---|---|---|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    known_ids = {m["run_id"] for m in manifests}
    if any(
        r.get("benchmark_scope") != SCOPE or r.get("run_id") not in known_ids
        for r in rows
    ):
        raise ValueError("stand-in log has an unknown scope/run manifest")
    for manifest in manifests:
        run = [r for r in rows if r["run_id"] == manifest["run_id"]]
        planned = Counter((r["task_id"], r["trial"]) for r in manifest["planned"])
        actual = Counter((r["task_id"], r["trial"]) for r in run)
        if any(count != 1 for count in planned.values()) or any(
            count != 1 or key not in planned for key, count in actual.items()
        ):
            raise ValueError("duplicate or unexpected task/trial identity")
        for row in run:
            if any(
                row.get(key) != manifest.get(key)
                for key in (
                    "config_hash",
                    "runner_git_sha",
                    "versions",
                    "model",
                    "inference_engine",
                    "partition",
                    "generation_profile",
                    "cache_policy",
                    "supervision_id",
                )
            ):
                raise ValueError("row/manifest provenance mismatch")
        missing = len(planned - actual)
        if manifest["status"] == "completed" and missing:
            raise ValueError("completed manifest has missing coverage")
        lines.append(
            f"| {manifest['run_id']} | {manifest['model']} / {manifest['inference_engine']} | {manifest['config_hash']} / {manifest['runner_git_sha']} | {manifest['partition']} / {manifest['generation_profile']} | {manifest['status']} | {len(run)}/{len(planned)} | {missing} | {sum(r['pass'] for r in run)}/{len(run)} | {sum(r['invalid_tool_calls'] for r in run)} | {sum(r['unsafe_attempts'] for r in run)} | {sum(r['critical_safety_failure'] for r in run)} |"
        )
        if run:
            lines += [
                "",
                "| Domain | Passed / executed | Median task wall s | Median output tok/s (wall) |",
                "|---|---:|---:|---:|",
            ]
            for domain in sorted({r["domain"] for r in run}):
                domain_rows = [r for r in run if r["domain"] == domain]
                lines.append(
                    f"| {domain} | {sum(r['pass'] for r in domain_rows)}/{len(domain_rows)} | {median(r['wall_seconds'] for r in domain_rows):.2f} | {median(r['tokens_per_second'] for r in domain_rows):.2f} |"
                )
            failures = Counter(
                r["failure_class"] for r in run if r.get("failure_class")
            )
            lines += [
                "",
                "Failure classes: "
                + (
                    ", ".join(
                        f"{key}={value}" for key, value in sorted(failures.items())
                    )
                    or "none"
                ),
                "",
            ]
    lines += [
        "",
        "Output rate includes whole task wall time, not pure decode. RSS is not total model memory; consult the supervised server/Metal/physical-footprint and system pressure trace.",
        "No composite score is computed. Safety failures and prevented unsafe attempts remain explicit; passing other tasks cannot offset them.",
        "",
    ]
    return "\n".join(lines)


def build_report(root: Path) -> None:
    log = root / "results/standin/log.jsonl"
    rows = (
        [json.loads(line) for line in log.read_text().splitlines() if line.strip()]
        if log.exists()
        else []
    )
    manifests = [
        json.loads(p.read_text())
        for p in sorted((root / "results/standin/runs").glob("*/manifest.json"))
    ]
    destination = root / "results/STANDIN.md"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(render(rows, manifests))


if __name__ == "__main__":
    from bench_common import REPO

    build_report(REPO)
