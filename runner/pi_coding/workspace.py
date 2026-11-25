"""A bounded synthetic project and an external oracle for Pi coding tasks."""

import json
import tempfile
import time
from pathlib import Path
from threading import Lock

from automation_sandbox import run_python


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def check(task, files, *, hidden):
    cases = task["visible"] + (task["hidden"] if hidden else [])
    # The sandbox receives inputs and candidate files. Expected values are
    # compared by the parent process and are never copied into that directory.
    driver = (
        """import json, sys
sys.path.insert(0, '.')
"""
        + task["imports"]
        + """
observed = []
for expression in EXPRESSIONS:
    try:
        observed.append({"value": eval(expression)})
    except Exception as error:
        observed.append({"raises": type(error).__name__, "message": str(error)})
print(json.dumps(observed, allow_nan=False))
"""
    )
    driver = driver.replace(
        "in EXPRESSIONS:", "in " + repr([c["expression"] for c in cases]) + ":"
    )
    with tempfile.TemporaryDirectory() as tmp:
        workspace = Path(tmp)
        for name, source in files.items():
            (workspace / name).write_text(source)
        (workspace / "_probe.py").write_text(driver)
        result = run_python(workspace, "_probe.py")
    if result["returncode"]:
        return {
            "passed": False,
            "error": result["stderr"][-1800:],
            "limit": result["limit_reason"],
        }
    try:
        actual = json.loads(result["stdout"])
    except ValueError:
        actual = None
    if not isinstance(actual, list) or len(actual) != len(cases):
        return {"passed": False, "error": "Invalid probe output"}
    failures = []
    for case, observed in zip(cases, actual, strict=True):
        expected = case["expected"]
        if isinstance(expected, dict) and "raises" in expected:
            ok = isinstance(observed, dict) and all(
                observed.get(k) == v for k, v in expected.items()
            )
        else:
            ok = json.dumps({"value": expected}, sort_keys=True) == json.dumps(
                observed, sort_keys=True
            )
        if not ok:
            failures.append(
                {
                    "expression": case["expression"],
                    "expected": expected,
                    "observed": observed,
                }
            )
    return {"passed": not failures, "cases": len(cases), "failures": failures}


class TaskWorkspace:
    def __init__(self, task, out, start, output_tokens):
        self.task = task
        self.files = task["files"].copy()
        self.out = out
        self.start = start
        self.output_tokens = output_tokens
        self.snapshots = []
        self.requests = 0
        self.visible_tests = 0
        self.inject_failure = task.get("transient_first_write", False)
        self.lock = Lock()
        self.infrastructure_error = None

    def apply(self, action, args):
        with self.lock:
            result = self._apply(action, args)
            with (self.out / "tools.jsonl").open("a") as journal:
                journal.write(
                    json.dumps(
                        {
                            "elapsed": time.monotonic() - self.start,
                            "action": action,
                            "args": args,
                            "result": result,
                        }
                    )
                    + "\n"
                )
            return result

    def _apply(self, action, args):
        if action == "request":
            if args.get("max_tokens") != self.output_tokens:
                raise RuntimeError("Pi wire output budget differs from the protocol")
            if {t["function"]["name"] for t in args.get("tools", [])} != {
                "read_file",
                "edit_file",
                "write_file",
                "run_tests",
            }:
                raise RuntimeError("Unexpected Pi tool set")
            self.requests += 1
            return {"ok": True}
        if action == "run_tests":
            self.visible_tests += 1
            return check(self.task, self.files, hidden=False)
        name = args.get("path")
        if name not in self.files:
            return {"error": "Use an exact task filename"}
        if action == "read_file":
            return {"content": self.files[name]}
        if action == "edit_file":
            old = args.get("old")
            if not old or self.files[name].count(old) != 1:
                return {"error": "The old text must have exactly one match"}
            content = self.files[name].replace(old, args["replacement"], 1)
        elif action == "write_file":
            content = args["content"]
        else:
            return {"error": "Unknown tool"}
        if not isinstance(content, str) or len(content.encode()) > 32768:
            return {"error": "Source must fit in 32 KiB"}
        if self.inject_failure:
            self.inject_failure = False
            return {"error": "Temporary workspace lock. Retry this write."}
        self.files[name] = content
        self.snapshots.append((time.monotonic() - self.start, self.files.copy()))
        return {"ok": True}
