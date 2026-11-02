"""Replay saved grades and submitted scripts without a model server."""

import hashlib
import json
import subprocess
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "runner"))
from automation_tasks import tasks
from run_automation_suite import execute_source, grader_module, strict_json
from standin_domain import Domain
from standin_tasks import cases

OUT = Path(__file__).resolve().parent
HOUSE = ROOT / "results/standin/runs/20261102T005318Z-266aff30"
AUTO = ROOT / "results/automation/runs/20261102T010429Z-a2cd6cb4"
# Load the exact measured grader; later language fixes never regrade this run.
manifest = json.loads((HOUSE / "manifest.json").read_text())
frozen_source = subprocess.check_output(
    [
        "git",
        "-C",
        str(ROOT),
        "show",
        manifest["runner_git_sha"] + ":checks/peixinho_standin.py",
    ]
)
assert (
    hashlib.sha256(frozen_source).hexdigest()
    == manifest["versions"]["peixinho_standin.py"]
)
frozen = types.ModuleType("measured_grader")
exec(  # noqa: S102 - hash-verified measured repository code
    compile(frozen_source, "measured:checks/peixinho_standin.py", "exec"),
    frozen.__dict__,
)
report = {"household": [], "python": [], "grader_source": manifest["runner_git_sha"]}
for case in cases("heldout"):
    trace = json.loads((HOUSE / f"{case.task_id}-trial1.json").read_text())
    case.store = Domain.restore(trace["final"])
    grade = frozen.grade(
        case,
        trace["initial"],
        trace["phases"],
        trace["final_answers"],
        trace["messages"],
        trace["error"],
    )
    api = [
        (call["function"]["name"], json.loads(call["function"]["arguments"]))
        for message in trace["messages"]
        for call in message.get("tool_calls", [])
    ]
    journal = [
        (event["tool"], event["arguments"]) for event in trace["final"]["journal"]
    ]
    item = {
        "task": case.task_id,
        "grade_matches": grade == trace["grade"],
        "api_matches_journal": api == journal,
        "passed": grade["pass"],
        "failed_checks": grade["failed_checks"],
    }
    assert item["grade_matches"] and item["api_matches_journal"], item
    report["household"].append(item)
oracle = grader_module()
for task in tasks():
    trace = json.loads((AUTO / f"{task.task_id}-trial1.json").read_text())
    replay = []
    for index, data in enumerate(oracle.variants(task.task_id, "heldout")):
        result = execute_source(trace["script"], task.filename, data)
        passed = (
            result["returncode"] == 0
            and not result.get("timed_out")
            and not result.get("limit_reason")
            and strict_json(result["stdout"]) == oracle.expected(task.task_id, data)
        )
        assert passed == trace["validation"][index]["pass"], (task.task_id, index)
        replay.append({"variant": index, "passed": passed, "execution": result})
    report["python"].append(
        {
            "task": task.task_id,
            "passed": trace["grade"]["pass"],
            "replay_matches": True,
            "variants": replay,
        }
    )
samples = [
    json.loads(line) for line in (OUT / "resources.jsonl").read_text().splitlines()
]
baseline = [
    json.loads(line) for line in (OUT / "baseline.jsonl").read_text().splitlines()
]
report["resources"] = {
    "samples": len(samples),
    "pressure_levels": sorted({sample["kernel_pressure_level"] for sample in samples}),
    "swap_growth_mib": max(sample["swap_used_mib"] for sample in samples)
    - baseline[-1]["swap_used_mib"],
    "minimum_free_percent_telemetry": min(sample["free_percent"] for sample in samples),
}
report["decoder"] = {
    "mode": "block diffusion32 threshold0.95",
    "reasoning_tool_promotions": (OUT / "server.log")
    .read_text()
    .count("written inside the reasoning returned as tool calls"),
}
(OUT / "audit.json").write_text(json.dumps(report, indent=2) + "\n")
print(
    json.dumps(
        {
            "household": sum(item["passed"] for item in report["household"]),
            "python": sum(item["passed"] for item in report["python"]),
            "resources": report["resources"],
            "decoder": report["decoder"],
        },
        indent=2,
    )
)
