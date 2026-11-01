"""Full task coverage after failed admission, strictly outside scored comparisons.

Uses unmodified v8.1 task/tool/isolation implementations. No canonical log rows,
admission retries, or rank-eligible scores are written. Commit driver/profile
before --run. --validate-draft does not load a model or create output.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shlex
import shutil
import signal
import subprocess
import sys
import time
import uuid
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "runner"))
import run_bench as bench
from automation_tasks import tasks as python_tasks
from bench_common import git_sha
from build_agent_leaderboard import TRACKS, source_path
from capacity_admission import capacity_fits, capacity_plan
from mei_provenance import verify_mei_runtime
from owned_process import OwnedSession
from run_automation_suite import TOOLS as PYTHON_TOOLS
from run_automation_suite import execute_source, isolation_identity
from run_automation_suite import run_task as python_task
from run_prompt import call_backend_streaming
from run_standin_suite import (
    committed_config,
    generation,
    run_task,
    verify_endpoint_identity,
    write_json,
)
from standin_tasks import cases
from supervise_bench import baseline_ready, gate_reason, now, sample

RELEASE = "19c9584b71e30ceea8d8c4c29070d1781ce60854"
PROFILE = Path(__file__).with_name("flint-full-diagnostic-v8p1.yaml")
FAILED_DIAGNOSTIC = Path(__file__).with_name("flint-full-diagnostic-v8p3p1-20261101")


def replay_prefix(task: str) -> list[dict[str, Any]]:
    if task not in ("expense-summary", "reminder-repair"):
        raise ValueError("only the two preserved empty-final requests may be replayed")
    path = FAILED_DIAGNOSTIC / f"python-{task}.json"
    if path.read_bytes() != subprocess.check_output(
        ["git", "show", f"HEAD:{path.relative_to(REPO)}"], cwd=REPO
    ):
        raise ValueError("commit original diagnostic evidence before replay")
    result = json.loads(path.read_text())
    if (
        result["error"] != "empty_final"
        or result["messages"][-1]["role"] != "assistant"
    ):
        raise ValueError("expected the preserved reasoning-only terminal response")
    return result["messages"][:-1]


def fingerprint(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate(draft: bool = False) -> tuple[dict[str, Any], bytes, dict[str, str]]:
    import yaml

    content = PROFILE.read_bytes()
    cfg = yaml.safe_load(content)
    if not draft:
        _, admitted = committed_config(PROFILE)
        if content != admitted:
            raise ValueError("diagnostic profile changed")
        actual = subprocess.check_output(
            ["git", "show", f"HEAD:{Path(__file__).relative_to(REPO)}"], cwd=REPO
        )
        if actual != Path(__file__).read_bytes():
            raise ValueError("commit the diagnostic driver before running")
    if (
        cfg.get("diagnostic_only") is not True
        or cfg.get("model") != "OsaurusAI/Flint-40B-A2.5B-JANGH2"
    ):
        raise ValueError("this driver is only for the unranked pinned Flint diagnostic")
    canonical = yaml.safe_load(
        subprocess.check_output(
            ["git", "show", f"{RELEASE}:configs/capacity-v8-20261101/flint.yaml"],
            cwd=REPO,
        )
    )
    allowed = {
        "required_runner_environment",
        "benchmark_launch_command",
        "diagnostic_only",
        "benchmark_status",
        "canonical_admission_run",
    }
    if {
        key
        for key in cfg.keys() | canonical.keys()
        if cfg.get(key) != canonical.get(key)
    } - allowed:
        raise ValueError(
            "diagnostic must preserve the exact released model, sampler, context and budget profile"
        )
    runtime = cfg["required_runner_environment"]["MEI_RUNTIME_BASE"]
    canonical_runtime = canonical["required_runner_environment"]["MEI_RUNTIME_BASE"]
    if runtime != canonical_runtime + "-diagnostic" or cfg[
        "benchmark_launch_command"
    ] != canonical["benchmark_launch_command"].replace(canonical_runtime, runtime):
        raise ValueError("unexpected diagnostic launch command")
    admission_dir = REPO / cfg["canonical_admission_run"]
    admission = json.loads((admission_dir / "admission.json").read_text())
    manifest = json.loads((admission_dir / "manifest.json").read_text())
    if (
        admission["status"] != "failed"
        or manifest["status"] != "admission_failed"
        or manifest["model"] != cfg["model"]
    ):
        raise ValueError("expected preserved failed native admission")
    paths = {source_path(name) for value in TRACKS.values() for name in value[3]}
    paths.update(
        "runner/" + name
        for name in (
            "run_bench.py",
            "supervise_bench.py",
            "capacity_admission.py",
            "probe_mei.py",
        )
    )
    versions = {}
    for path in sorted(paths):
        released = subprocess.check_output(
            ["git", "show", f"{RELEASE}:{path}"], cwd=REPO
        )
        if (REPO / path).read_bytes() != released:
            raise ValueError(f"task/runtime helper differs from released v8.1: {path}")
        versions[path] = hashlib.sha256(released).hexdigest()
    verify_mei_runtime(cfg)
    capacity_plan(cfg)
    if not re.fullmatch("[0-9a-f]{12,40}", git_sha()):
        raise ValueError("benchmark source must be clean")
    return cfg, content, versions


def worker(output: Path):
    cfg, _, _ = validate()
    invocation = json.loads((output / "invocation.json").read_text())
    if os.environ.get("FLINT_DIAGNOSTIC_NONCE") != invocation["id"]:
        raise ValueError("worker requires its parent supervisor")
    runtime = Path(cfg["required_runner_environment"]["MEI_RUNTIME_BASE"])
    base = cfg["benchmark_endpoint"]
    model = cfg["orchestration"]["served_model_id"]
    _, sampler = generation(cfg)
    manifest = {
        "status": "starting",
        "qualified": False,
        "diagnostic_only": True,
        "canonical_admission_run": cfg["canonical_admission_run"],
        "planned_household": 12,
        "planned_python": 3,
        "completed": [],
    }
    write_json(output / "diagnostic.json", manifest)
    server = None
    try:
        with (output / "server-launch.log").open("w") as log:
            server = subprocess.Popen(
                shlex.split(cfg["benchmark_launch_command"]),
                cwd=REPO,
                stdout=log,
                stderr=subprocess.STDOUT,
            )
        if not bench.wait_for_health(base.rstrip("/") + "/models", proc=server):
            raise RuntimeError("diagnostic server health failed")
        endpoint = verify_endpoint_identity(base, model)
        manifest["endpoint_identity"] = endpoint
        if not bench.assert_plain_completion(base, model, timeout=900):
            raise RuntimeError("diagnostic plain completion failed")
        manifest.update(
            status="running", runtime_identity=verify_mei_runtime(cfg, base_url=base)
        )
        write_json(output / "diagnostic.json", manifest)
        if invocation.get("replay_terminations"):
            manifest.update(planned_household=0, planned_python=0, planned_replays=2)
            for name in ("expense-summary", "reminder-repair"):
                messages = replay_prefix(name)
                before = set((output / "stream-timing").glob("*.json"))
                response, ttft, decode = call_backend_streaming(
                    base,
                    model,
                    messages,
                    PYTHON_TOOLS,
                    timeout=180,
                    max_tokens=4096,
                    connect_timeout=90,
                    first_progress_timeout=90,
                    stream_idle_timeout=30,
                    **sampler,
                )
                timing = sorted(set((output / "stream-timing").glob("*.json")) - before)
                if len(timing) != 1:
                    raise RuntimeError(
                        "expected exactly one termination trace per replay"
                    )
                record = {
                    "request_messages": messages,
                    "response": response,
                    "ttft": ttft,
                    "decode": decode,
                    "termination": json.loads(timing[0].read_text()),
                    "qualified": False,
                    "limits": "New stochastic continuation of the saved prefix; not the original sampled token sequence or a benchmark retry.",
                }
                write_json(output / f"termination-{name}.json", record)
                manifest["completed"].append(
                    {"track": "termination_replay", "task": name}
                )
                write_json(output / "diagnostic.json", manifest)
                print(
                    "TERMINATION",
                    name,
                    record["termination"]["termination_cause"],
                    flush=True,
                )
            manifest["status"] = "completed"
            write_json(output / "diagnostic.json", manifest)
            return
        # Deliberately do NOT rerun native admission or call run_suite's test bypass.
        for case in cases("heldout"):
            result = run_task(case, call_backend_streaming, base, model, sampler)
            write_json(output / f"household-{case.task_id}.json", result)
            manifest["completed"].append(
                {
                    "track": "household",
                    "task": case.task_id,
                    "pass": result["grade"]["pass"],
                }
            )
            write_json(output / "diagnostic.json", manifest)
            print(
                "HOUSEHOLD", case.task_id, result["grade"]["failed_checks"], flush=True
            )
            if result["failure_class"] == "interrupted":
                raise KeyboardInterrupt
        isolation = execute_source('print("isolation ready")\n', "input.csv", "")
        if isolation["returncode"] != 0 or isolation.get("limit_reason"):
            raise RuntimeError("Python isolation preflight failed")
        identity = isolation_identity(isolation)
        manifest["isolation"] = identity
        for task in python_tasks():
            result = python_task(
                task, "heldout", call_backend_streaming, base, model, sampler, identity
            )
            write_json(output / f"python-{task.task_id}.json", result)
            manifest["completed"].append(
                {
                    "track": "python",
                    "task": task.task_id,
                    "pass": result["grade"]["pass"],
                }
            )
            write_json(output / "diagnostic.json", manifest)
            print("PYTHON", task.task_id, result["grade"]["failed_checks"], flush=True)
            if result["failure_class"] == "interrupted":
                raise KeyboardInterrupt
        manifest["status"] = "completed"
    except BaseException as exc:
        manifest.update(
            status="interrupted"
            if isinstance(exc, (KeyboardInterrupt, SystemExit))
            else "failed",
            error=f"{type(exc).__name__}: {exc}",
        )
        raise
    finally:
        write_json(output / "diagnostic.json", manifest)
        subprocess.run(
            [
                "bash",
                str(REPO / "runner/stop_mei_server.sh"),
                "--runtime-base",
                str(runtime),
            ],
            cwd=REPO,
            timeout=45,
            check=False,
        )
        if server is not None:
            server.wait(timeout=20)


def supervise(output: Path, replay_terminations: bool = False):
    cfg, content, versions = validate()
    if replay_terminations:
        for task in ("expense-summary", "reminder-repair"):
            replay_prefix(task)
    deadline = 900 if replay_terminations else 7200
    output = output.resolve()
    if not output.is_relative_to(REPO / "artifacts"):
        raise ValueError(
            "diagnostic output must be a new repository artifact directory"
        )
    if (
        subprocess.run(
            ["lsof", "-nP", "-iTCP:8024", "-sTCP:LISTEN"],
            capture_output=True,
            check=False,
        ).returncode
        != 1
    ):
        raise RuntimeError("port8024 is occupied; never disrupt another run")
    output.mkdir(parents=True, exist_ok=False)
    (output / "config.yaml").write_bytes(content)
    baseline = []
    with (output / "baseline.jsonl").open("x", buffering=1) as log:
        for index in range(7):
            if index:
                time.sleep(5)
            point = sample(os.getpid(), output)
            baseline.append(point)
            log.write(json.dumps(point) + "\n")
    plan = capacity_plan(cfg)
    assert plan is not None
    if not baseline_ready(baseline, None, 2) or not capacity_fits(plan, baseline):
        write_json(
            output / "outcome.json",
            {"status": "preflight_declined", "model_started": False},
        )
        return 2
    identifier = uuid.uuid4().hex
    write_json(
        output / "invocation.json",
        {
            "id": identifier,
            "time": now(),
            "release": RELEASE,
            "source_sha": git_sha(),
            "profile_sha256": hashlib.sha256(content).hexdigest(),
            "driver_sha256": fingerprint(Path(__file__)),
            "versions": versions,
            "initial": baseline[-1],
            "capacity_plan": plan,
            "deadline_seconds": deadline,
            "replay_terminations": replay_terminations,
            "diagnostic_only": True,
            "qualified": False,
        },
    )
    env = os.environ.copy()
    env.update(cfg["required_runner_environment"])
    env["FLINT_DIAGNOSTIC_NONCE"] = identifier
    if replay_terminations:
        env["VMLX_STREAM_TIMING_DIR"] = str(output / "stream-timing")
    process = session = None
    reason = None
    end = time.monotonic() + deadline
    low = warnings = 0
    try:
        with (
            (output / "worker.log").open("w") as log,
            (output / "resources.jsonl").open("x", buffering=1) as telemetry,
        ):
            process = subprocess.Popen(
                [
                    sys.executable,
                    str(Path(__file__).resolve()),
                    "--worker",
                    "--output",
                    str(output),
                ],
                cwd=REPO,
                env=env,
                stdout=log,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
            session = OwnedSession(process)
            write_json(
                output / "process.json",
                {"pid": process.pid, "supervisor_pid": os.getpid()},
            )
            while not session.leader_exited():
                point = sample(process.pid, output)
                telemetry.write(json.dumps(point) + "\n")
                warnings = warnings + 1 if point["kernel_pressure_level"] >= 2 else 0
                reason = gate_reason(
                    point, baseline[-1], low, warnings, percent_stop=False
                )
                if reason is None and time.monotonic() >= end:
                    reason = "deadline"
                if reason is None and (output / "stop.request").exists():
                    reason = "requested teardown"
                if reason:
                    break
                time.sleep(5)
    except BaseException as exc:  # noqa: BLE001 - terminal monitor boundary records signals/errors before teardown
        reason = f"{type(exc).__name__}: {exc}"
    finally:
        if session is not None:
            try:
                session.stop(grace_seconds=15)
            except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
                reason = f"{reason or 'cleanup'}; {type(exc).__name__}: {exc}"
        runtime = Path(cfg["required_runner_environment"]["MEI_RUNTIME_BASE"])
        try:
            cleanup = subprocess.run(
                [
                    "bash",
                    str(REPO / "runner/stop_mei_server.sh"),
                    "--runtime-base",
                    str(runtime),
                ],
                cwd=REPO,
                capture_output=True,
                timeout=45,
                check=False,
            )
            if cleanup.returncode:
                reason = (
                    f"{reason or 'cleanup'}; server stop returned {cleanup.returncode}"
                )
        except (OSError, subprocess.SubprocessError) as exc:
            reason = f"{reason or 'cleanup'}; {type(exc).__name__}: {exc}"
        code = process.returncode if process is not None else None
        write_json(
            output / "outcome.json",
            {
                "time": now(),
                "returncode": code,
                "stop_reason": reason,
                "diagnostic_only": True,
                "qualified": False,
            },
        )
        runtime = Path(cfg["required_runner_environment"]["MEI_RUNTIME_BASE"])
        if (runtime / "logs").exists():
            shutil.copytree(runtime / "logs", output / "backend-logs")
    return 0 if code == 0 and reason is None else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--validate-draft", action="store_true")
    parser.add_argument("--worker", action="store_true")
    parser.add_argument("--replay-terminations", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    def interrupted(_signal, _frame):
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, interrupted)
    if args.validate_draft:
        validate(draft=True)
        print(
            "Draft profile and all helper source bytes match released v8.1; no model loaded"
        )
    elif args.output is None:
        parser.error("--output required")
    elif args.worker:
        worker(args.output)
    else:
        raise SystemExit(supervise(args.output, args.replay_terminations))
