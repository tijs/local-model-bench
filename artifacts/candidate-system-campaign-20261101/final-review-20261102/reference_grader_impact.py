"""Diagnostic compatibility audit; never emits or promotes benchmark rows."""

import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "runner"))
from standin_domain import Domain
from standin_tasks import cases

OUT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location(
    "current_grader", ROOT / "checks/peixinho_standin.py"
)
assert spec and spec.loader
grader = importlib.util.module_from_spec(spec)
spec.loader.exec_module(grader)
campaign = json.loads((ROOT / "results/agent-v9-20261101.json").read_text())
report = {
    "scope": "Diagnostic replay of saved trajectories to identify grading impact only; not fresh model runs, new scores, or ranking eligibility",
    "models": [],
}
for entry in campaign["models"]:
    directory = ROOT / "results/standin/runs" / entry["household_run"]
    manifest = json.loads((directory / "manifest.json").read_text())
    # State and case semantics used for replay must be exactly the measured ones.
    for name in ("standin_domain.py", "standin_tasks.py"):
        digest = hashlib.sha256((ROOT / "runner" / name).read_bytes()).hexdigest()
        assert digest == manifest["versions"][name], (entry["model"], name)
    frozen = subprocess.check_output(
        [
            "git",
            "-C",
            str(ROOT),
            "show",
            manifest["runner_git_sha"] + ":checks/peixinho_standin.py",
        ]
    )
    assert (
        hashlib.sha256(frozen).hexdigest()
        == manifest["versions"]["peixinho_standin.py"]
    )
    changed = []
    for case in cases("heldout"):
        trace = json.loads((directory / f"{case.task_id}-trial1.json").read_text())
        case.store = Domain.restore(trace["final"])
        actual = grader.grade(
            case,
            trace["initial"],
            trace["phases"],
            trace["final_answers"],
            trace["messages"],
            trace["error"],
        )
        if actual != trace["grade"]:
            changed.append(
                {
                    "task": case.task_id,
                    "recorded": trace["grade"],
                    "current_diagnostic": actual,
                }
            )
    report["models"].append(
        {
            "model": entry["model"],
            "run": entry["household_run"],
            "measured_source": manifest["runner_git_sha"],
            "tasks_checked": 12,
            "changed_grades": changed,
        }
    )
report["all_unchanged"] = all(not item["changed_grades"] for item in report["models"])
(OUT / "reference-grader-impact.json").write_text(json.dumps(report, indent=2) + "\n")
print(
    json.dumps(
        {
            "models": len(report["models"]),
            "tasks_checked": sum(x["tasks_checked"] for x in report["models"]),
            "all_unchanged": report["all_unchanged"],
        }
    )
)
assert report["all_unchanged"], (
    "Review any changed reference grade before declaring it unaffected"
)
