"""Audit API arguments against simulator events and extract bad-turn histories."""

import copy
import datetime
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "runner"))
from standin_domain import TOOLS

OUT = Path(__file__).resolve().parent
RUNS = ROOT / "results/standin/runs"
QWEN = "20261029T070419Z-2e68d320"
FLINT_RUNS = (
    "20261028T195303Z-f44d6fd6",
    "20261028T201346Z-09b0f775",
    "20261028T204516Z-d4e79199",
)
flint = [RUNS / rid for rid in FLINT_RUNS]


def write_frozen(path, value):
    content = json.dumps(value, indent=2) + "\n"
    if path.exists() and path.read_text() != content:
        raise RuntimeError(f"Refusing to overwrite divergent frozen evidence: {path}")
    path.write_text(content)


report = []
inputs = {"qwen": [], "flint": []}
for run in [RUNS / QWEN, *flint]:
    family = "qwen" if run.name == QWEN else "flint"
    for path in sorted(run.glob("*-trial1.json")):
        data = json.loads(path.read_text())
        calls = []
        malformed = []
        for response in data["responses"]:
            for choice in response.get("choices", []):
                for call in choice.get("message", {}).get("tool_calls") or []:
                    f = call["function"]
                    try:
                        args = (
                            json.loads(f["arguments"])
                            if isinstance(f["arguments"], str)
                            else f["arguments"]
                        )
                        calls.append((f["name"], args))
                    except (ValueError, TypeError) as error:
                        malformed.append(str(error))
        journal = [(j["tool"], j["arguments"]) for j in data["final"]["journal"]]
        row = {
            "run_id": run.name,
            "task": path.stem,
            "pass": data["grade"]["pass"],
            "failed_checks": data["grade"]["failed_checks"],
            "api_calls": len(calls),
            "journal_events": len(journal),
            "api_arguments_equal_executed_arguments": calls == journal,
            "malformed": malformed,
        }
        report.append(row)
        # Extract the first model-produced ID conflict in this task. Stop at the
        # assistant turn before simulator feedback; keep the actual entire history.
        messages = data["messages"]
        for index, message in enumerate(messages):
            if message.get(
                "role"
            ) != "tool" or "operation ID already used" not in message.get(
                "content", ""
            ):
                continue
            assistant = max(
                i for i in range(index) if messages[i]["role"] == "assistant"
            )
            system = max(i for i in range(assistant) if messages[i]["role"] == "system")
            output = messages[assistant]
            request = {
                "model": json.loads((run / "manifest.json").read_text())["model"],
                "messages": copy.deepcopy(messages[system:assistant]),
                "tools": TOOLS,
                "temperature": 0.0,
                "top_p": 1.0,
                "top_k": 0,
                "max_tokens": 1536,
                "stream": False,
            }
            name = path.stem.removesuffix("-trial1")
            # Preserve the parsed assistant object. Swift renders it using
            # this model's native tool format, with an exact prompt-prefix proof.
            inputs[family].append(
                {
                    "name": name + "-" + run.name,
                    "source": str(path.relative_to(ROOT)),
                    "source_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                    "request": request,
                    "assistant": output,
                    "canonicalized_continuation": True,
                }
            )
            break
for family, cases in inputs.items():
    write_frozen(OUT / (family + "-inputs.json"), cases)
write_frozen(OUT / "api-journal-audit.json", report)
timing = []
for rid, folder in [
    ("20261029T065141Z-fd31a521", "full-supervision"),
    (QWEN, "corrected-full-supervision"),
]:
    parent = ROOT / "artifacts/qwen36-appclosure-retry-20261029" / folder
    begin = json.loads((parent / "invocation.json").read_text())["initial"]["time"]
    end = json.loads((parent / "outcome.json").read_text())["time"]
    total = (
        datetime.datetime.fromisoformat(end) - datetime.datetime.fromisoformat(begin)
    ).total_seconds()
    task_times = [
        json.loads(p.read_text())["wall_seconds"]
        for p in (RUNS / rid).glob("*-trial1.json")
    ]
    timing.append(
        {
            "run_id": rid,
            "tasks": len(task_times),
            "end_to_end_seconds": total,
            "task_seconds": sum(task_times),
            "startup_admission_teardown_seconds": total - sum(task_times),
        }
    )
flint_parent = ROOT / "artifacts/flint-failure-investigation-20261028/rerun"
start = json.loads((flint_parent / "invocation.json").read_text())["initial"]["time"]
end = json.loads((flint_parent / "outcome.json").read_text())["time"]
seconds = (
    datetime.datetime.fromisoformat(end) - datetime.datetime.fromisoformat(start)
).total_seconds()
flint_times = [
    json.loads(p.read_text())["wall_seconds"]
    for p in (RUNS / FLINT_RUNS[0]).glob("*-trial1.json")
]
timing.append(
    {
        "run_id": FLINT_RUNS[0],
        "model": "Flint JANGH2",
        "tasks": len(flint_times),
        "end_to_end_seconds": seconds,
        "task_seconds": sum(flint_times),
        "startup_admission_teardown_seconds": seconds - sum(flint_times),
    }
)
write_frozen(OUT / "benchmark-durations.json", timing)
print(
    "audited",
    len(report),
    "tasks;",
    sum(r["api_arguments_equal_executed_arguments"] for r in report),
    "exact API/journal matches",
)
print("Qwen conflict inputs", len(inputs["qwen"]), "Flint", len(inputs["flint"]))
print(
    "mismatches",
    [
        (r["run_id"], r["task"])
        for r in report
        if not r["api_arguments_equal_executed_arguments"]
    ],
)
