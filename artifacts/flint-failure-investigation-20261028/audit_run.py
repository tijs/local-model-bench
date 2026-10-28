"""Verify completed rows against their archived grader and resource campaign."""

import argparse
import datetime
import json
import shutil
import subprocess
import sys
import types
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "runner"))
from standin_domain import Domain
from standin_tasks import TASK_IDS, cases


def read(path):
    return json.loads(path.read_text())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("run", type=Path)
    parser.add_argument("supervision", type=Path)
    parser.add_argument("out", type=Path)
    args = parser.parse_args()
    manifest = read(args.run / "manifest.json")
    planned = {(p["task_id"], p["trial"]) for p in manifest["planned"]}
    assert planned and len(planned) == len(manifest["planned"])
    assert planned <= {(name, 1) for name in TASK_IDS}
    assert manifest["status"] == "completed" and manifest["rows_completed"] == len(
        planned
    )
    rows = [
        json.loads(s)
        for s in Path("results/standin/log.jsonl").read_text().splitlines()
    ]
    rows = [r for r in rows if r["run_id"] == manifest["run_id"]]
    assert (
        len(rows) == len(planned)
        and {(r["task_id"], r["trial"]) for r in rows} == planned
    )
    assert not any(r["harness_error"] or r["rank_eligible"] for r in rows)
    source = manifest["runner_git_sha"]
    grader = types.ModuleType("archived_grader")
    content = subprocess.check_output(
        ["git", "show", f"{source}:checks/peixinho_standin.py"]
    )
    exec(compile(content, "archived_grader", "exec"), grader.__dict__)  # noqa: S102 - pinned local grader
    tasks = []
    for case in cases(manifest["partition"]):
        if (case.task_id, 1) not in planned:
            continue
        result = read(args.run / f"{case.task_id}-trial1.json")
        assert result["initial"] == case.store.snapshot(), case.task_id
        case.store = Domain.restore(result["final"])
        grade = grader.grade(
            case,
            result["initial"],
            result["phases"],
            result["final_answers"],
            result["messages"],
            result["error"],
        )
        assert grade == result["grade"], case.task_id
        row = next(r for r in rows if r["task_id"] == case.task_id)
        assert (
            row["pass"] == grade["pass"]
            and row["failed_checks"] == grade["failed_checks"]
        )
        tasks.append(
            {
                "task_id": case.task_id,
                "pass": grade["pass"],
                "error": result["error"],
                "failed_checks": grade["failed_checks"],
                "turns": result["turns"],
                "final_answers": result["final_answers"],
                "unsafe_attempts": grade["unsafe_attempts"],
                "invalid_tool_calls": grade["invalid_tool_calls"],
                "critical_safety_failure": grade["critical_safety_failure"],
            }
        )
    cfg = yaml.safe_load((args.run / "config.yaml").read_text())
    runtime = Path(cfg["required_runner_environment"]["MEI_RUNTIME_BASE"])
    shutil.copytree(runtime / "logs", args.supervision / "runtime-logs")
    resources = [
        json.loads(s)
        for s in (args.supervision / "resources.jsonl").read_text().splitlines()
    ]
    start = read(args.supervision / "invocation.json")["initial"]["time"]
    cutoff = datetime.datetime.fromisoformat(start).timestamp()
    all_requests = [
        json.loads(s)
        for s in (runtime / "logs/requests.jsonl").read_text().splitlines()
    ]
    requests = [r for r in all_requests if r["t"] >= cutoff]
    outcome = read(args.supervision / "outcome.json")
    assert outcome["returncode"] == 0 and outcome["stop_reason"] is None
    baseline = subprocess.check_output(
        ["git", "show", "6eb2384:results/standin/log.jsonl"]
    )
    assert Path("results/standin/log.jsonl").read_bytes().startswith(baseline)
    audit = {
        "run_id": manifest["run_id"],
        "runner_source": source,
        "config_hash": manifest["config_hash"],
        "rows": len(rows),
        "passes": sum(r["pass"] for r in rows),
        "all_grades_reproduced_with_archived_grader": True,
        "original_standin_rows_unchanged_prefix": True,
        "requests": len(requests),
        "request_log_prior_rows_excluded": len(all_requests) - len(requests),
        "minimum_free_percent": min(r["free_percent"] for r in resources),
        "maximum_pressure": max(r["kernel_pressure_level"] for r in resources),
        "swap_growth_mib": max(r["swap_used_mib"] for r in resources)
        - resources[0]["swap_used_mib"],
        "peak_mlx_bytes": max(r["mem_peak_bytes"] for r in requests),
        "peak_server_physical_bytes": max(
            p["phys_footprint_bytes"]
            for r in resources
            for p in r["owned_processes"]
            if p["comm"].endswith("/mei")
        ),
        "tasks": tasks,
    }
    args.out.write_text(json.dumps(audit, indent=2) + "\n")
    print(json.dumps({k: v for k, v in audit.items() if k != "tasks"}, indent=2))


if __name__ == "__main__":
    main()
