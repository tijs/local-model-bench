"""Generate coverage-aware Python automation evidence without mixing tracks."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from automation_tasks import SCOPE


def render(rows: list[dict[str, Any]], manifests: list[dict[str, Any]]) -> str:
    by_id = {m["run_id"]: m for m in manifests}
    if len(by_id) != len(manifests) or any(
        r.get("run_id") not in by_id or r.get("benchmark_scope") != SCOPE for r in rows
    ):
        raise ValueError("duplicate manifest or unknown scope/run")
    lines = [
        "# Python automation",
        "",
        "Real isolated Python execution on synthetic files. Separate from household workflow and real Peixinho app results.",
        "",
        "Each submitted script is checked on visible and unseen fixture variants. Shared server/cache trials are not independent samples.",
        "",
        "| Run | Model / engine | Config / runner | Partition / profile | Status | Executed / planned | Passed | Invalid calls | Task seconds |",
        "|---|---|---|---|---|---:|---:|---:|---:|",
    ]
    for manifest in manifests:
        run = [r for r in rows if r["run_id"] == manifest["run_id"]]
        planned = Counter((r["task_id"], r["trial"]) for r in manifest["planned"])
        actual = Counter((r["task_id"], r["trial"]) for r in run)
        if any(v != 1 for v in planned.values()) or any(
            v != 1 or k not in planned for k, v in actual.items()
        ):
            raise ValueError("duplicate or unexpected task/trial")
        for row in run:
            if any(
                row.get(k) != manifest.get(k)
                for k in (
                    "config_hash",
                    "runner_git_sha",
                    "versions",
                    "model",
                    "inference_engine",
                    "partition",
                    "generation_profile",
                    "cache_policy",
                    "runtime_identity",
                    "isolation",
                )
            ):
                raise ValueError("row/manifest provenance mismatch")
        if manifest["rows_completed"] != len(run) or (
            manifest["status"] == "completed" and actual != planned
        ):
            raise ValueError("completion/coverage mismatch")
        usable = manifest["status"] == "completed" and not any(
            r.get("harness_error") for r in run
        )
        status = (
            manifest["status"]
            if usable
            else manifest["status"] + " (incomplete/unusable)"
        )
        lines.append(
            f"| {manifest['run_id']} | {manifest['model']} / {manifest['inference_engine']} | {manifest['config_hash']} / {manifest['runner_git_sha']} | {manifest['partition']} / {manifest['generation_profile']} | {status} | {len(run)}/{len(planned)} | {sum(bool(r['pass']) for r in run)} | {sum(r['invalid_tool_calls'] for r in run)} | {sum(r['wall_seconds'] for r in run):.2f} |"
        )
    lines.extend(
        [
            "",
            "Scores require matching task/tool/validator and release identities. Partial runs are never a complete-model score.",
            "",
        ]
    )
    return "\n".join(lines)


def build_report(root: Path) -> None:
    log = root / "results/automation/log.jsonl"
    rows = (
        [json.loads(line) for line in log.read_text().splitlines() if line.strip()]
        if log.exists()
        else []
    )
    manifests = [
        json.loads(p.read_text())
        for p in sorted((root / "results/automation/runs").glob("*/manifest.json"))
    ]
    destination = root / "results/AUTOMATION.md"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(render(rows, manifests))


if __name__ == "__main__":
    from bench_common import REPO

    build_report(REPO)
