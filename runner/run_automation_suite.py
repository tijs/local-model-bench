"""Real isolated Python automation, reported separately from household workflows."""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import math
import signal
import tempfile
import time
import uuid
from http.client import HTTPException
from pathlib import Path
from typing import Any

from automation_tasks import SCOPE, SYSTEM, TASK_IDS, Task, tasks, visible_input
from bench_common import REPO, git_sha, supervision_id
from llama_provenance import verify_llama_runtime
from mei_provenance import verify_mei_runtime
from run_prompt import StreamStall, call_backend_streaming
from run_standin_suite import (
    Client,
    EpisodeFailure,
    admission,
    append_row,
    committed_config,
    conversation,
    digest,
    empty_trace,
    expected_request_model,
    generation,
    validate_config,
    verify_endpoint_identity,
    write_json,
)
from standin_domain import DomainError, Json, tool, validate

BUDGETS = {
    "max_turns": 8,
    "max_tokens": 4096,
    "task_seconds": 480,
    "turn_seconds": 180,
    "connect_seconds": 30,
    "first_progress_seconds": 90,
    "idle_seconds": 30,
}
TOOLS = [
    tool(
        "read_file",
        "Read an available synthetic input file or solution.py. No other paths are available.",
        {
            "name": {
                "type": "string",
                "enum": ["input.csv", "input.json", "solution.py"],
            }
        },
        ["name"],
    ),
    tool(
        "write_script",
        "Replace solution.py with complete Python source, up to 32768 UTF-8 bytes. Input files cannot be edited.",
        {"source": {"type": "string", "minLength": 1}},
        ["source"],
    ),
    tool(
        "run_script",
        "Execute current solution.py against the visible input filename. Real isolated Python, no network, subprocess or file writes. Returns bounded stdout/stderr and exit status; repair execution errors with write_script.",
        {},
        [],
    ),
]
SCHEMAS = {x["function"]["name"]: x["function"]["parameters"] for x in TOOLS}


def isolation_identity(execution: Json) -> Json:
    identity = execution["isolation"]
    return {
        key: identity[key]
        for key in (
            "policy_version",
            "profile_template_sha256",
            "limit_bootstrap_sha256",
            "python_sha256",
            "python_full_version",
            "host_os",
            "host_arch",
        )
    }


def verify_isolation(execution: Json, expected: Json | None) -> None:
    if expected is not None and isolation_identity(execution) != expected:
        raise RuntimeError(
            "Python execution isolation/runtime identity changed during run"
        )


def grader_module():
    spec = importlib.util.spec_from_file_location(
        "automation_grader", REPO / "checks/python_automation.py"
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("missing automation grader")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def execute_source(source: str, filename: str, data: str, timeout: float = 5) -> Json:
    # Only the synthetic input and submitted source exist inside the read boundary.
    from automation_sandbox import run_python

    with tempfile.TemporaryDirectory(prefix="bench-python-") as folder:
        path = Path(folder)
        (path / "solution.py").write_text(source)
        (path / filename).write_text(data)
        return run_python(path, args=[filename], timeout=timeout)


class Workspace:
    def __init__(
        self,
        task: Task,
        data: str,
        deadline: float | None = None,
        isolation: Json | None = None,
    ):
        self.task = task
        self.data = data
        self.source = task.starter
        self.journal: list[Json] = []
        self.invalid_calls = 0
        self.successful_runs: set[str] = set()
        self.deadline = deadline
        self.isolation = isolation

    def execute(self, name: str, args: Any) -> Json:
        try:
            if name not in SCHEMAS:
                raise DomainError("unknown tool")
            validate(SCHEMAS[name], args)
            if name == "read_file":
                if args["name"] == self.task.filename:
                    result = {"name": args["name"], "content": self.data}
                elif args["name"] == "solution.py" and self.source is not None:
                    result = {"name": "solution.py", "content": self.source}
                else:
                    raise DomainError("file is not available")
            elif name == "write_script":
                source = args["source"]
                try:
                    source_bytes = source.encode("utf-8")
                except UnicodeError as exc:
                    raise DomainError("source must be valid UTF-8") from exc
                if len(source_bytes) > 32768 or "\x00" in source:
                    raise DomainError("source exceeds limit or contains NUL")
                self.source = source
                result = {
                    "saved": "solution.py",
                    "sha256": hashlib.sha256(source.encode()).hexdigest(),
                }
            else:
                if self.source is None:
                    raise DomainError("write solution.py first")
                remaining = (
                    5
                    if self.deadline is None
                    else min(5, self.deadline - time.monotonic())
                )
                if remaining <= 0:
                    raise EpisodeFailure("task_timeout")
                result = execute_source(
                    self.source, self.task.filename, self.data, remaining
                )
                verify_isolation(result, self.isolation)
                result["script_sha256"] = hashlib.sha256(
                    self.source.encode()
                ).hexdigest()
                if (
                    result["returncode"] == 0
                    and not result.get("timed_out")
                    and not result.get("limit_reason")
                ):
                    self.successful_runs.add(result["script_sha256"])
        except DomainError as exc:
            self.invalid_calls += 1
            result = {"error": str(exc)}
        self.journal.append(
            {
                "tool": name,
                "arguments": copy.deepcopy(args),
                "result": copy.deepcopy(result),
            }
        )
        return result


def strict_json(text: str) -> Any:
    def bad_constant(value):
        raise ValueError(f"non-finite JSON: {value}")

    def object_pairs(pairs):
        value = {}
        for key, item in pairs:
            if key in value:
                raise ValueError("duplicate JSON key")
            value[key] = item
        return value

    def finite_float(value):
        number = float(value)
        if not math.isfinite(number):
            raise ValueError("non-finite JSON number")
        return number

    return json.loads(
        text,
        parse_constant=bad_constant,
        parse_float=finite_float,
        object_pairs_hook=object_pairs,
    )


def run_task(
    task: Task,
    partition: str,
    client: Client,
    base_url: str,
    model: str,
    sampler: Json,
    isolation: Json | None = None,
) -> Json:
    data = visible_input(task.task_id, partition)
    start = time.monotonic()
    workspace = Workspace(task, data, start + BUDGETS["task_seconds"], isolation)
    trace = empty_trace()
    messages = [
        {"role": "system", "content": SYSTEM},
        {
            "role": "user",
            "content": task.instruction + "\nAvailable input: " + task.filename,
        },
    ]
    trace["messages"] = copy.deepcopy(messages)
    error = None
    failure = None
    final = None
    checks: Json = {}
    validations = []
    try:
        final = conversation(
            messages,
            TOOLS,
            workspace.execute,
            client,
            base_url,
            model,
            sampler,
            start + BUDGETS["task_seconds"],
            trace,
            BUDGETS,
        )
    except EpisodeFailure as exc:
        error = str(exc)
        failure = {
            "token_limit": "truncation",
            "turn_limit": "turn_limit",
            "task_timeout": "task_budget",
        }.get(error, "protocol_error")
    except StreamStall as exc:
        error = str(exc)
        failure = "timeout"
        trace["timeout_phase"] = exc.phase
    except KeyboardInterrupt:
        error = "interrupted"
        failure = "interrupted"
    except (
        HTTPException,
        OSError,
        ValueError,
        TypeError,
        RuntimeError,
        KeyError,
        IndexError,
    ) as exc:
        error = f"{type(exc).__name__}: {exc}"
        failure = "harness_error"
    checks["finished_with_final_answer"] = final is not None and error is None
    checks["no_invalid_tool_calls"] = workspace.invalid_calls == 0
    checks["submitted_script"] = workspace.source is not None
    script_hash = hashlib.sha256((workspace.source or "").encode()).hexdigest()
    checks["final_script_executed_successfully"] = (
        script_hash in workspace.successful_runs
    )
    # Held-out data and expected results are evaluated only after the model has finished.
    if workspace.source is not None and failure not in (
        "harness_error",
        "interrupted",
        "timeout",
    ):
        try:
            oracle = grader_module()
            inputs = oracle.variants(task.task_id, partition)
            for index, variant_data in enumerate(inputs):
                execution = execute_source(
                    workspace.source, task.filename, variant_data
                )
                verify_isolation(execution, isolation)
                wanted = oracle.expected(task.task_id, variant_data)
                equal = False
                parse_error = None
                try:
                    actual = strict_json(execution["stdout"])
                    equal = json.dumps(
                        actual, sort_keys=True, ensure_ascii=False
                    ) == json.dumps(wanted, sort_keys=True, ensure_ascii=False)
                except (ValueError, TypeError, RecursionError) as exc:
                    parse_error = str(exc)
                passed = (
                    execution["returncode"] == 0
                    and not execution.get("timed_out")
                    and not execution.get("limit_reason")
                    and equal
                )
                validations.append(
                    {
                        "variant": index,
                        "input_sha256": hashlib.sha256(
                            variant_data.encode()
                        ).hexdigest(),
                        "expected": wanted,
                        "execution": execution,
                        "parse_error": parse_error,
                        "pass": passed,
                    }
                )
            checks["visible_output_correct"] = validations[0]["pass"]
            checks["unseen_outputs_correct"] = all(v["pass"] for v in validations[1:])
        except KeyboardInterrupt:
            error = "interrupted"
            failure = "interrupted"
        except (OSError, ValueError, RuntimeError, TypeError) as exc:
            error = f"{type(exc).__name__}: {exc}"
            failure = "harness_error"
    checks.setdefault("visible_output_correct", False)
    checks.setdefault("unseen_outputs_correct", False)
    passed = all(checks.values()) and error is None
    trace.update(
        final_answer=final,
        script=workspace.source,
        script_sha256=script_hash,
        input_sha256=hashlib.sha256(data.encode()).hexdigest(),
        journal=workspace.journal,
        validation=validations,
        wall_seconds=time.monotonic() - start,
        error=error,
        failure_class=None if passed else failure or "task_failure",
        grade={
            "pass": passed,
            "checks": checks,
            "failed_checks": [k for k, v in checks.items() if not v],
            "invalid_tool_calls": workspace.invalid_calls,
        },
    )
    return trace


def validate_automation_config(cfg: Json) -> None:
    validate_config(cfg)
    if cfg.get("python_automation") is not True:
        raise ValueError("Python automation requires explicit python_automation: true")


def run_suite(
    cfg: Json,
    content: bytes,
    base_url: str,
    model: str,
    trials: int,
    partition: str,
    root: Path = REPO,
    client: Client = call_backend_streaming,
    *,
    _test_skip_admission: bool = False,
):
    validate_automation_config(cfg)
    if partition not in ("development", "heldout") or not 1 <= trials <= 20:
        raise ValueError("invalid partition or trial count")
    if _test_skip_admission and root.resolve() == REPO.resolve():
        raise ValueError("test-only runs cannot write canonical evidence")
    # Fail before model interaction if execution isolation is unavailable.
    isolation = execute_source('print("isolation ready")\n', "input.csv", "")
    if isolation["returncode"] != 0 or isolation.get("limit_reason"):
        raise RuntimeError("isolated Python preflight failed")
    runtime = (
        None if _test_skip_admission else verify_mei_runtime(cfg, base_url=base_url)
    )
    if not _test_skip_admission and cfg.get("inference_engine") == "llama.cpp":
        runtime = verify_llama_runtime(cfg, base_url=base_url)
    profile, sampler = generation(cfg)
    rid = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()) + "-" + uuid.uuid4().hex[:8]
    run_dir = root / "results/automation/runs" / rid
    run_dir.mkdir(parents=True)
    (run_dir / "config.yaml").write_bytes(content)
    version_paths = [
        Path(__file__),
        Path(__file__).with_name("automation_tasks.py"),
        Path(__file__).with_name("automation_sandbox.py"),
        Path(__file__).with_name("run_standin_suite.py"),
        Path(__file__).with_name("run_prompt.py"),
        Path(__file__).with_name("standin_domain.py"),
        Path(__file__).with_name("bench_common.py"),
        Path(__file__).with_name("mei_provenance.py"),
        Path(__file__).with_name("llama_provenance.py"),
        Path(__file__).with_name("owned_process.py"),
        Path(__file__).with_name("build_automation_report.py"),
        REPO / "checks/python_automation.py",
    ]
    manifest = {
        "run_id": rid,
        "supervision_id": supervision_id(),
        "started_at": time.time(),
        "benchmark_scope": SCOPE,
        "model": cfg["model"],
        "inference_engine": cfg["inference_engine"],
        "config_hash": hashlib.sha256(content).hexdigest()[:12],
        "runner_git_sha": git_sha(),
        "runtime_identity": runtime,
        "versions": {p.name: digest(p) for p in version_paths},
        "partition": partition,
        "generation_profile": profile,
        "generation_overrides": sampler,
        "cache_policy": cfg["standin_cache_policy"],
        "budgets": BUDGETS,
        "isolation": isolation_identity(isolation),
        "isolation_preflight": isolation["isolation"],
        "test_only": _test_skip_admission,
        "real_app_evidence": False,
        "task_selection": list(TASK_IDS),
        "planned": [
            {"task_id": tid, "trial": n}
            for tid in TASK_IDS
            for n in range(1, trials + 1)
        ],
        "rows_completed": 0,
        "status": "admitting",
    }
    write_json(run_dir / "manifest.json", manifest)
    rows = []
    try:
        gate = (
            {"status": "test-only skipped"}
            if _test_skip_admission
            else admission(client, base_url, model, sampler)
        )
        write_json(run_dir / "admission.json", gate)
        if gate["status"] not in ("passed", "test-only skipped"):
            manifest["status"] = "admission_failed"
            return rows, run_dir
        manifest["status"] = "running"
        write_json(run_dir / "manifest.json", manifest)
        for task in tasks():
            for trial in range(1, trials + 1):
                result = run_task(
                    task,
                    partition,
                    client,
                    base_url,
                    model,
                    sampler,
                    manifest["isolation"],
                )
                artifact = run_dir / f"{task.task_id}-trial{trial}.json"
                write_json(artifact, result)
                row = {
                    k: manifest[k]
                    for k in (
                        "run_id",
                        "benchmark_scope",
                        "model",
                        "inference_engine",
                        "config_hash",
                        "runner_git_sha",
                        "runtime_identity",
                        "versions",
                        "partition",
                        "generation_profile",
                        "cache_policy",
                        "isolation",
                        "supervision_id",
                    )
                }
                row.update(
                    task_id=task.task_id,
                    trial=trial,
                    **result["grade"],
                    error=result["error"],
                    failure_class=result["failure_class"],
                    harness_error=result["failure_class"]
                    in ("harness_error", "interrupted"),
                    wall_seconds=result["wall_seconds"],
                    turns=result["turns"],
                    prompt_tokens=result["prompt_tokens"],
                    completion_tokens=result["completion_tokens"],
                    ttft_seconds=result["ttft_seconds"],
                    result_path=str(artifact.relative_to(root)),
                )
                append_row(root / "results/automation/log.jsonl", row)
                rows.append(row)
                manifest["rows_completed"] = len(rows)
                write_json(run_dir / "manifest.json", manifest)
                print(
                    f"{task.task_id} trial{trial}: {'PASS' if row['pass'] else 'FAIL'} {row['failed_checks']}",
                    flush=True,
                )
                if result["failure_class"] in (
                    "harness_error",
                    "interrupted",
                    "timeout",
                ):
                    manifest["status"] = (
                        "interrupted"
                        if result["failure_class"] == "interrupted"
                        else "infrastructure_stopped"
                    )
                    return rows, run_dir
        manifest["status"] = "completed"
        return rows, run_dir
    except KeyboardInterrupt:
        manifest["status"] = "interrupted"
        return rows, run_dir
    finally:
        manifest["finished_at"] = time.time()
        write_json(run_dir / "manifest.json", manifest)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--source-config", type=Path)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--request-model", required=True)
    parser.add_argument("--trials", type=int, default=1)
    parser.add_argument(
        "--partition", choices=("development", "heldout"), default="development"
    )
    parser.add_argument("--summary-out", type=Path)
    args = parser.parse_args()
    cfg, content = committed_config(args.config, args.source_config)
    validate_automation_config(cfg)
    from urllib.parse import urlsplit

    endpoint = urlsplit(args.base_url)
    if (
        endpoint.scheme != "http"
        or endpoint.hostname not in ("127.0.0.1", "localhost", "::1")
        or endpoint.username
        or endpoint.password
    ):
        parser.error("only local HTTP endpoints without credentials are supported")
    expected = expected_request_model(cfg, content)
    if expected != args.request_model:
        parser.error("request-model must match exact configured identity")
    verify_endpoint_identity(args.base_url, expected)

    def interrupt(_signum, _frame):
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, interrupt)
    rows, directory = run_suite(
        cfg, content, args.base_url, args.request_model, args.trials, args.partition
    )
    if args.summary_out:
        write_json(args.summary_out, rows)
    from build_automation_report import build_report

    build_report(REPO)
    if json.loads((directory / "manifest.json").read_text())["status"] != "completed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
