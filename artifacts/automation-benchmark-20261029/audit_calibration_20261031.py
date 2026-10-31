"""Re-audit frozen calibration transcripts without changing benchmark rows."""

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "runner"), str(ROOT / "checks")]
from peixinho_standin import grade
from standin_domain import Domain
from standin_tasks import cases

OUT = Path(__file__).parent
HOUSE = "20261031T073803Z-dd6549a1"
PYTHON = "20261031T074330Z-0e134560"
SUP = OUT / "qwen-calibration-retry2-20261031"
report = {"household_run": HOUSE, "python_run": PYTHON, "household": []}
for case in cases("development"):
    path = ROOT / "results/standin/runs" / HOUSE / (case.task_id + "-trial1.json")
    data = json.loads(path.read_text())
    calls = [
        (c["function"]["name"], json.loads(c["function"]["arguments"]))
        for r in data["responses"]
        for choice in r.get("choices", [])
        for c in choice.get("message", {}).get("tool_calls") or []
    ]
    journal = [(j["tool"], j["arguments"]) for j in data["final"]["journal"]]
    case.store = Domain.restore(data["final"])
    checked = grade(
        case,
        data["initial"],
        data["phases"],
        data["final_answers"],
        data["messages"],
        data["error"],
    )
    assert checked == data["grade"], case.task_id
    assert calls == journal, case.task_id
    report["household"].append(
        {
            "task_id": case.task_id,
            "api_calls": len(calls),
            "api_arguments_equal_executed_arguments": True,
            "regrade_matches": True,
            "grade": checked,
            "transcript_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "wall_seconds": data["wall_seconds"],
        }
    )
for track, rid in [("standin", HOUSE), ("automation", PYTHON)]:
    manifest = json.loads(
        (ROOT / "results" / track / "runs" / rid / "manifest.json").read_text()
    )
    rows = [
        json.loads(x)
        for x in (ROOT / "results" / track / "log.jsonl").read_text().splitlines()
    ]
    rows = [r for r in rows if r["run_id"] == rid]
    assert manifest["status"] == "completed"
    assert manifest["rows_completed"] == len(rows) == len(manifest["planned"])
    assert all(not r.get("harness_error") and not r.get("error") for r in rows)
    assert all(r["runner_git_sha"] == "cc2fc1b0ea7a" for r in rows)
    report[track + "_summary"] = {
        "completed": len(rows),
        "passed": sum(r["pass"] for r in rows),
        "task_seconds": sum(r["wall_seconds"] for r in rows),
        "invalid_tool_calls": sum(r["invalid_tool_calls"] for r in rows),
        "runtime_identity": manifest["runtime_identity"],
    }
telemetry = [json.loads(x) for x in (SUP / "resources.jsonl").read_text().splitlines()]
initial = json.loads((SUP / "invocation.json").read_text())["initial"]
report["resources"] = {
    "initial": initial,
    "minimum_free_percent": min(r["free_percent"] for r in telemetry),
    "maximum_pressure": max(r["kernel_pressure_level"] for r in telemetry),
    "maximum_swap_growth_mib": max(r["swap_used_mib"] for r in telemetry)
    - initial["swap_used_mib"],
    "outcome": json.loads((SUP / "outcome.json").read_text()),
}
report["attribution_limits"] = (
    "Raw API and simulator arguments match, and frozen grades reproduce. Both observed failures are ID choices in API output. Prior native/cache/Python controls support bounded runtime attribution; this audit alone does not distinguish model from quantization/shared MLX kernels or certify every runtime path."
)
path = OUT / "calibration-audit-20261031.json"
content = json.dumps(report, indent=2) + "\n"
if path.exists():
    assert path.read_text() == content
else:
    path.write_text(content)
print(json.dumps({k: v for k, v in report.items() if k.endswith("_summary")}, indent=2))
