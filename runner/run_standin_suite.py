"""Run synthetic household workflows through a real local model; no app claims."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import signal
import subprocess
import time
import uuid
from collections.abc import Callable
from http.client import HTTPException
from pathlib import Path
from typing import Any

import yaml
from bench_common import REPO, git_sha
from run_prompt import (
    StreamStall,
    call_backend_streaming,
    normalize_generation_overrides,
)
from standin_domain import SCOPE, TOOLS, DomainError, Json, dumps, tool, validate
from standin_tasks import SMOKE_IDS, SYSTEM, TASK_IDS, Case, cases, event_before

Client = Callable[..., tuple[Json, float | None, float | None]]
BUDGETS = {
    "max_turns": 12,
    "max_tokens": 1536,
    "task_seconds": 300,
    "turn_seconds": 120,
    "connect_seconds": 30,
    "first_progress_seconds": 90,
    "idle_seconds": 30,
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    temp.replace(path)


def append_row(path: Path, row: Json) -> None:
    import fcntl

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as stream:
        fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
        stream.write(dumps(row) + "\n")
        stream.flush()
        os.fsync(stream.fileno())
        fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def committed_config(path: Path, source: Path | None = None) -> tuple[Json, bytes]:
    source = (source or path).resolve()
    relative = source.relative_to(REPO.resolve())
    result = subprocess.run(
        ["git", "show", f"HEAD:{relative.as_posix()}"],
        cwd=REPO,
        capture_output=True,
        check=False,
    )
    content = path.read_bytes()
    if result.returncode or result.stdout != content:
        raise ValueError(
            "stand-in runs require the exact config bytes committed at HEAD"
        )
    cfg = yaml.safe_load(content)
    if not isinstance(cfg, dict) or cfg.get("benchmark_scope") != SCOPE:
        raise ValueError(f"config benchmark_scope must be {SCOPE}")
    return cfg, content


def verify_endpoint_identity(base_url: str, expected: str) -> Json:
    """Verify the endpoint itself, not merely the requested model alias."""
    import urllib.request

    with urllib.request.urlopen(
        base_url.rstrip("/") + "/models", timeout=15
    ) as response:
        payload = json.load(response)
    if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
        raise TypeError("model endpoint returned malformed identity")
    ids = [item.get("id") for item in payload["data"] if isinstance(item, dict)]
    if expected not in ids:
        raise ValueError(
            f"model endpoint is not serving expected identity {expected!r}"
        )
    return payload


def validate_config(cfg: Json) -> None:
    if cfg.get("benchmark_scope") != SCOPE:
        raise ValueError(f"config benchmark_scope must be {SCOPE}")
    if cfg.get("standin_partition", "development") not in ("development", "heldout"):
        raise ValueError("standin_partition must be development or heldout")
    if not isinstance(cfg.get("standin_smoke", False), bool):
        raise TypeError("standin_smoke must be a literal boolean")
    if (
        not isinstance(cfg.get("standin_cache_policy"), str)
        or not cfg["standin_cache_policy"].strip()
    ):
        raise ValueError("declare standin_cache_policy explicitly")
    generation(cfg)
    selected_task_ids(cfg, cfg.get("standin_smoke", False))


def selected_task_ids(cfg: Json, smoke: bool = False) -> tuple[str, ...]:
    """Explicit committed subsets are diagnostics with their own planned coverage."""
    if "standin_task_ids" not in cfg:
        return SMOKE_IDS if smoke else TASK_IDS
    values = cfg["standin_task_ids"]
    if (
        not isinstance(values, list)
        or not values
        or any(not isinstance(value, str) or value not in TASK_IDS for value in values)
        or len(set(values)) != len(values)
    ):
        raise ValueError(
            "standin_task_ids must be a nonempty unique list of known tasks"
        )
    if smoke or cfg.get("standin_smoke", False):
        raise ValueError(
            "explicit task subsets cannot be combined with smoke selection"
        )
    return tuple(task for task in TASK_IDS if task in values)


def generation(cfg: Json) -> tuple[str, Json]:
    name = cfg.get("standin_generation_profile")
    profiles = cfg.get("generation_profiles", {})
    if not isinstance(name, str) or name not in profiles:
        raise ValueError(
            "declare standin_generation_profile in generation_profiles explicitly"
        )
    return name, normalize_generation_overrides(profiles[name])


def request(
    client: Client,
    base_url: str,
    model: str,
    messages: list[Json],
    tools: list[Json],
    sampler: Json,
    remaining: float,
) -> tuple[Json, float | None, float | None]:
    return client(
        base_url,
        model,
        messages,
        tools,
        timeout=min(BUDGETS["turn_seconds"], remaining),
        max_tokens=BUDGETS["max_tokens"],
        connect_timeout=BUDGETS["connect_seconds"],
        first_progress_timeout=BUDGETS["first_progress_seconds"],
        stream_idle_timeout=BUDGETS["idle_seconds"],
        no_response_retries=0,
        temperature=sampler.get("temperature"),
        **{key: value for key, value in sampler.items() if key != "temperature"},
    )


class EpisodeFailure(ValueError):
    pass


def conversation(
    messages: list[Json],
    tools: list[Json],
    execute: Callable[[str, Any], Json],
    client: Client,
    base_url: str,
    model: str,
    sampler: Json,
    deadline: float,
    trace: Json,
) -> str:
    while trace["turns"] < BUDGETS["max_turns"]:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise EpisodeFailure("task_timeout")
        response, ttft, decode = request(
            client, base_url, model, messages, tools, sampler, remaining
        )
        if not isinstance(response, dict):
            raise EpisodeFailure("malformed_response")
        usage_value = response.get("usage", {})
        if not isinstance(usage_value, dict) or any(
            not isinstance(usage_value.get(key, 0), int)
            or isinstance(usage_value.get(key, 0), bool)
            or usage_value.get(key, 0) < 0
            for key in ("prompt_tokens", "completion_tokens")
        ):
            raise EpisodeFailure("malformed_usage")
        trace["turns"] += 1
        trace["responses"].append(copy.deepcopy(response))
        if trace["ttft_seconds"] is None:
            trace["ttft_seconds"] = ttft
        trace["decode_window_seconds"] += decode or 0
        usage = response.get("usage") or {}
        trace["prompt_tokens"] += usage.get("prompt_tokens", 0)
        trace["completion_tokens"] += usage.get("completion_tokens", 0)
        trace["usage_estimated"] |= bool(response.get("usage_estimated"))
        try:
            choice = response["choices"][0]
            message = choice["message"]
            if (
                isinstance(message, dict)
                and message.get("content") is not None
                and not isinstance(message["content"], str)
            ):
                raise TypeError("invalid assistant content")
            if not isinstance(message, dict) or message.get("role") != "assistant":
                raise ValueError("invalid assistant message")
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise EpisodeFailure("malformed_response") from exc
        messages.append(copy.deepcopy(message))
        trace["messages"].append(copy.deepcopy(message))
        if choice.get("finish_reason") == "length":
            raise EpisodeFailure("token_limit")
        calls = message.get("tool_calls")
        if calls is not None and not isinstance(calls, list):
            raise EpisodeFailure("malformed_tool_calls")
        reason = choice.get("finish_reason")
        if calls and reason != "tool_calls":
            raise EpisodeFailure("unfinished_tool_calls")
        if not calls:
            if reason != "stop":
                raise EpisodeFailure(f"invalid_finish_reason:{reason}")
            final = message.get("content")
            if not isinstance(final, str) or not final.strip():
                raise EpisodeFailure("empty_final")
            return final
        if not isinstance(calls, list) or len(calls) > 8:
            raise EpisodeFailure("malformed_tool_calls")
        ids = [call.get("id") for call in calls if isinstance(call, dict)]
        if (
            len(ids) != len(calls)
            or any(not isinstance(i, str) or not i for i in ids)
            or len(set(ids)) != len(ids)
        ):
            raise EpisodeFailure("malformed_tool_ids")
        for call in calls:
            try:
                function = call["function"]
                name = function["name"]
                args = json.loads(function["arguments"])
                if not isinstance(name, str):
                    raise TypeError("invalid name")
            except (KeyError, TypeError, ValueError) as exc:
                raise EpisodeFailure("malformed_tool_arguments") from exc
            result = execute(name, args)
            tool_message = {
                "role": "tool",
                "tool_call_id": call["id"],
                "content": dumps(result),
            }
            messages.append(tool_message)
            trace["messages"].append(copy.deepcopy(tool_message))
    raise EpisodeFailure("turn_limit")


def empty_trace() -> Json:
    return {
        "messages": [],
        "responses": [],
        "turns": 0,
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "ttft_seconds": None,
        "decode_window_seconds": 0.0,
        "usage_estimated": False,
    }


def admission(client: Client, base_url: str, model: str, sampler: Json) -> Json:
    """Small unscored structured-call/dependent-continuation/grounding gate."""
    trace = empty_trace()
    code = "probe-" + uuid.uuid4().hex[:8]
    stages: list[str] = []

    def execute(name: str, args: Any) -> Json:
        if name != "admission_probe" or not isinstance(args, dict):
            return {"error": "unknown probe"}
        try:
            validate(tools[0]["function"]["parameters"], args)
        except DomainError:
            return {"error": "invalid probe arguments"}
        if args["stage"] == "begin" and not stages:
            stages.append("begin")
            return {
                "code": code,
                "instruction": "call admission_probe stage verify with this code",
            }
        if args == {"stage": "verify", "code": code} and stages == ["begin"]:
            stages.append("verify")
            return {"verified": code}
        return {"error": "unexpected stage or code"}

    tools = [
        tool(
            "admission_probe",
            "Begin, then verify using the code returned by begin.",
            {
                "stage": {"type": "string", "enum": ["begin", "verify"]},
                "code": {
                    "type": "string",
                    "description": "Code returned by begin, required for verify; ignored during begin.",
                },
            },
            ["stage"],
        )
    ]
    messages = [
        {
            "role": "user",
            "content": "Call admission_probe with stage begin, then verify using its returned code. Finally repeat the verified code in your answer.",
        }
    ]
    trace["messages"] = copy.deepcopy(messages)
    try:
        final = conversation(
            messages,
            tools,
            execute,
            client,
            base_url,
            model,
            sampler,
            time.monotonic() + BUDGETS["task_seconds"],
            trace,
        )
        passed = stages == ["begin", "verify"] and code in final
        trace.update(status="passed" if passed else "failed", final_text=final)
    except StreamStall as exc:
        trace.update(status="failed", error=str(exc), timeout_phase=exc.phase)
    except (
        HTTPException,
        OSError,
        TypeError,
        ValueError,
        RuntimeError,
        KeyError,
        IndexError,
    ) as exc:
        # Admission is an unscored boundary: preserve failure evidence, never pass it.
        trace.update(status="failed", error=f"{type(exc).__name__}: {exc}")
    except KeyboardInterrupt:
        trace.update(status="interrupted", error="interrupted")
    return trace


def load_grader():
    import importlib.util

    path = Path(__file__).resolve().parents[1] / "checks/peixinho_standin.py"
    spec = importlib.util.spec_from_file_location("peixinho_standin_checks", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("stand-in validator module unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.grade


def run_task(
    case: Case, client: Client, base_url: str, model: str, sampler: Json
) -> Json:
    start = time.monotonic()
    initial = case.store.snapshot()
    trace = empty_trace()
    phases: list[Json] = []
    finals: list[str] = []
    error: str | None = None
    classification = "task_failure"
    try:
        for index, text in enumerate(case.segments):
            approved = event_before(case, index)
            case.store.phase = index
            if index == 0 or (
                index < len(case.events) and case.events[index] == "restart"
            ):
                messages = [
                    {"role": "system", "content": SYSTEM + "\n" + case.context()}
                ]
                trace["messages"].append(copy.deepcopy(messages[0]))
            user_message = {"role": "user", "content": text}
            messages.append(user_message)
            trace["messages"].append(copy.deepcopy(user_message))
            trace.setdefault("trusted_events", []).append(
                {
                    "phase": index,
                    "event": case.events[index] if index < len(case.events) else "",
                    "approved_preview_ids": approved,
                }
            )
            finals.append(
                conversation(
                    messages,
                    TOOLS,
                    case.store.execute,
                    client,
                    base_url,
                    model,
                    sampler,
                    start + BUDGETS["task_seconds"],
                    trace,
                )
            )
            phases.append(case.store.snapshot())
        if case.task_id == "routine-occurrence":
            case.store.advance_day("2026-10-26", 1)
            case.store.advance_day("2026-10-28", 3)
            trace["simulator_contract_observations"] = {
                "occurrence_count": len(case.store.occurrences)
            }
    except EpisodeFailure as exc:
        error = str(exc)
        classification = {
            "token_limit": "truncation",
            "turn_limit": "turn_limit",
            "task_timeout": "timeout",
        }.get(
            error, "protocol_error" if error.startswith("malformed") else "task_failure"
        )
    except StreamStall as exc:
        error, classification = str(exc), "timeout"
        trace["timeout_phase"] = exc.phase
    except (
        HTTPException,
        OSError,
        TypeError,
        ValueError,
        RuntimeError,
        KeyError,
        IndexError,
    ) as exc:
        # Preserve the task's accepted state and completed messages on any client
        # or simulator fault. This is unusable harness evidence, never a pass.
        error, classification = f"{type(exc).__name__}: {exc}", "harness_error"
    except KeyboardInterrupt:
        error, classification = "interrupted", "interrupted"
    finally:
        trace.update(
            initial=initial,
            final=case.store.snapshot(),
            phases=phases,
            final_answers=finals,
            error=error,
            failure_class=classification,
            wall_seconds=time.monotonic() - start,
        )
    # Held-out validators are only imported after model execution. No filesystem
    # or Python tools are exposed to the model, including these checks.
    grade = load_grader()

    trace["grade"] = grade(case, initial, phases, finals, trace["messages"], error)
    if trace["grade"]["pass"]:
        trace["failure_class"] = None
    return trace


def run_suite(
    cfg: Json,
    config_bytes: bytes,
    base_url: str,
    model: str,
    trials: int,
    partition: str,
    smoke: bool,
    root: Path = REPO,
    client: Client = call_backend_streaming,
    *,
    _test_skip_admission: bool = False,
) -> tuple[list[Json], Path]:
    validate_config(cfg)
    if _test_skip_admission and root.resolve() == REPO.resolve():
        raise ValueError("test-only reference runs cannot write canonical results")
    if not 1 <= trials <= 20:
        raise ValueError("trials must be between 1 and 20")
    selected_ids = selected_task_ids(cfg, smoke)
    selected = [case for case in cases(partition) if case.task_id in selected_ids]
    profile, sampler = generation(cfg)
    run_id = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()) + "-" + uuid.uuid4().hex[:8]
    run_dir = root / "results/standin/runs" / run_id
    run_dir.mkdir(parents=True)
    config_hash = hashlib.sha256(config_bytes).hexdigest()[:12]
    (run_dir / "config.yaml").write_bytes(config_bytes)
    versions = {
        path.name: digest(path)
        for path in [
            Path(__file__),
            Path(__file__).resolve().parents[1] / "checks/peixinho_standin.py",
            Path(__file__).resolve().parents[1] / "tasks/peixinho_standin.json",
            *[
                Path(__file__).with_name(n)
                for n in (
                    "standin_domain.py",
                    "standin_tasks.py",
                    "build_standin_report.py",
                    "run_prompt.py",
                    "bench_common.py",
                )
            ],
        ]
    }
    manifest: Json = {
        "run_id": run_id,
        "benchmark_scope": SCOPE,
        "synthetic_data": True,
        "test_only": _test_skip_admission,
        "smoke": smoke,
        "task_selection": list(selected_ids),
        "trials": trials,
        "real_app_evidence": False,
        "model": cfg["model"],
        "request_model": model,
        "inference_engine": cfg["inference_engine"],
        "config_hash": config_hash,
        "runner_git_sha": git_sha(),
        "versions": versions,
        "partition": partition,
        "generation_profile": profile,
        "generation_overrides": sampler,
        "budgets": BUDGETS,
        "cache_policy": cfg.get("standin_cache_policy", "unspecified"),
        "planned": [
            {"task_id": case.task_id, "domain": case.domain, "trial": trial}
            for case in selected
            for trial in range(1, trials + 1)
        ],
        "status": "admitting",
        "rows_completed": 0,
    }
    write_json(run_dir / "manifest.json", manifest)
    rows: list[Json] = []
    try:
        gate = (
            {"status": "test-only skipped"}
            if _test_skip_admission
            else admission(client, base_url, model, sampler)
        )
        write_json(run_dir / "admission.json", gate)
        if gate["status"] not in ("passed", "test-only skipped"):
            manifest["status"] = (
                "interrupted" if gate["status"] == "interrupted" else "admission_failed"
            )
            return rows, run_dir
        for template in selected:
            for trial in range(1, trials + 1):
                # Each trial has fresh synthetic state. Backend cache policy is
                # separate and explicitly recorded; statistical independence is not claimed.
                case = copy.deepcopy(template)
                result = run_task(case, client, base_url, model, sampler)
                artifact = run_dir / f"{case.task_id}-trial{trial}.json"
                write_json(artifact, result)
                g = result["grade"]
                row = {
                    key: manifest[key]
                    for key in (
                        "run_id",
                        "benchmark_scope",
                        "model",
                        "inference_engine",
                        "config_hash",
                        "runner_git_sha",
                        "partition",
                        "generation_profile",
                        "versions",
                        "cache_policy",
                    )
                }
                row.update(
                    task_id=case.task_id,
                    domain=case.domain,
                    references=case.references,
                    trial=trial,
                    **{"pass": g["pass"]},
                    critical_safety_failure=g["critical_safety_failure"],
                    unsafe_attempts=g["unsafe_attempts"],
                    invalid_tool_calls=g["invalid_tool_calls"],
                    unauthorized_mutations=g["unauthorized_mutations"],
                    failed_checks=g["failed_checks"],
                    failure_class=result["failure_class"],
                    error=result["error"],
                    harness_error=result["failure_class"]
                    in ("harness_error", "interrupted"),
                    rank_eligible=False,
                    result_path=str(artifact.relative_to(root)),
                    wall_seconds=result["wall_seconds"],
                    prompt_tokens=result["prompt_tokens"],
                    completion_tokens=result["completion_tokens"],
                    tokens_per_second=result["completion_tokens"]
                    / max(result["wall_seconds"], 1e-9),
                    ttft_seconds=result["ttft_seconds"],
                    turns=result["turns"],
                    usage_estimated=result["usage_estimated"],
                )
                append_row(root / "results/standin/log.jsonl", row)
                rows.append(row)
                manifest["rows_completed"] = len(rows)
                write_json(run_dir / "manifest.json", manifest)
                print(
                    f"{case.task_id} trial {trial}: {'PASS' if row['pass'] else 'FAIL'} {row['failed_checks']}",
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
        write_json(run_dir / "manifest.json", manifest)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--source-config", type=Path)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--request-model", required=True)
    parser.add_argument("--trials", type=int, default=1)
    parser.add_argument(
        "--partition", choices=("development", "heldout"), default="development"
    )
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--summary-out", type=Path)
    args = parser.parse_args()
    try:
        cfg, config_content = committed_config(args.config, args.source_config)
        validate_config(cfg)
        from urllib.parse import urlsplit

        endpoint = urlsplit(args.base_url)
        if (
            endpoint.scheme != "http"
            or endpoint.hostname not in ("localhost", "127.0.0.1", "::1")
            or endpoint.username
            or endpoint.password
        ):
            raise ValueError(
                "stand-in v1 supports only local HTTP model endpoints without embedded credentials"
            )
        expected = (cfg.get("orchestration") or {}).get("served_model_id", cfg["model"])
        if args.request_model != expected:
            raise ValueError("request-model must match exact config served identity")
        verify_endpoint_identity(args.base_url, expected)
    except (OSError, TypeError, ValueError) as exc:
        parser.error(str(exc))

    def interrupt(_signum: int, _frame: Any) -> None:
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, interrupt)
    rows, run_dir = run_suite(
        cfg,
        config_content,
        args.base_url,
        args.request_model,
        args.trials,
        args.partition,
        args.smoke,
    )
    if args.summary_out:
        write_json(args.summary_out, rows)
    from build_standin_report import build_report

    build_report(REPO)
    status = json.loads((run_dir / "manifest.json").read_text())["status"]
    if status != "completed":
        raise SystemExit(130 if status == "interrupted" else 1)


if __name__ == "__main__":
    main()
