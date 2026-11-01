"""Run one committed benchmark with resource gates and durable interruption evidence."""

from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import os
import re
import shutil
import signal
import struct
import subprocess
import sys
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from bench_common import REPO, git_sha
from capacity_admission import capacity_fits, capacity_plan
from owned_process import OwnedSession
from run_standin_suite import committed_config, write_json


def now() -> str:
    return datetime.now(UTC).isoformat()


def launch_floor(cfg: dict[str, Any]) -> int:
    value = cfg.get("resource_monitor_policy", {}).get("launch_min_free_percent", 85)
    if not isinstance(value, int) or isinstance(value, bool) or not 70 <= value <= 99:
        raise ValueError("launch memory floor must be an integer70..99")
    return value


def admission_settings(
    cfg: dict[str, Any], deadline: int, trials: int
) -> tuple[int, int]:
    """Opt-in stable baselines; probes cannot become unbounded scored runs."""
    policy = cfg.get("resource_monitor_policy", {})
    count = policy.get("launch_baseline_samples", 1)
    spread = policy.get("launch_max_percent_spread", 2)
    for value, lower, upper in ((count, 1, 13), (spread, 0, 5)):
        if type(value) is not int or not lower <= value <= upper:
            raise ValueError("invalid launch baseline bounds")
    plan = capacity_plan(cfg)
    probe = cfg.get("resource_probe", False)
    if type(probe) is not bool:
        raise ValueError("resource_probe must be a literal boolean")
    if probe and (
        cfg.get("diagnostic_only") is not True
        or cfg.get("orchestration", {}).get("rank_eligible") is not False
        or count < 7
        or deadline > (3600 if plan is not None else 900)
        or trials != 1
    ):
        raise ValueError(
            "resource probes require diagnostic/non-ranking identity, "
            "at least7 baseline samples, one trial and bounded deadline"
        )
    return count, spread


def baseline_ready(
    samples: list[dict[str, Any]], floor: int | None, spread: int
) -> bool:
    """Every observation must pass; a transient recovery cannot hide pressure."""
    return (
        bool(samples)
        and all(
            (floor is None or point["free_percent"] >= floor)
            and point["kernel_pressure_level"] == 1
            and point["disk_free_bytes"] >= 10 * 1024**3
            and point["swap_used_mib"] < 16384
            for point in samples
        )
        and (
            (
                floor is None
                or max(point["free_percent"] for point in samples)
                - min(point["free_percent"] for point in samples)
                <= spread
            )
            and max(point["swap_used_mib"] for point in samples)
            - min(point["swap_used_mib"] for point in samples)
            < 64
        )
    )


def gate_reason(
    sample: dict[str, Any],
    initial: dict[str, Any],
    low: int,
    warnings: int,
    *,
    percent_stop: bool = True,
) -> str | None:
    if sample["kernel_pressure_level"] >= 4:
        return "critical memory pressure"
    if warnings >= 2:
        return "sustained warning memory pressure"
    if percent_stop and low >= 2:
        return "sustained memory free <=10%"
    if sample["swap_used_mib"] - initial["swap_used_mib"] >= 2048:
        return "swap growth >=2 GiB"
    if sample["swap_used_mib"] >= 16384:
        return "swap >=16 GiB"
    if sample["disk_free_bytes"] < 10 * 1024**3:
        return "disk below10GiB"
    return None


def sample(pid: int, destination: Path) -> dict[str, Any]:
    def read(argv):
        return subprocess.check_output(argv, text=True, timeout=10)

    pressure = read(["memory_pressure", "-Q"])
    swap = read(["sysctl", "vm.swapusage"])
    free = re.search(r"free percentage: (\d+)", pressure)
    used = re.search(r"used = ([\d.]+)", swap)
    if free is None or used is None:
        raise RuntimeError("cannot parse host memory counters")
    processes = []
    for line in read(["ps", "-axo", "pid=,ppid=,comm="]).splitlines():
        fields = line.strip().split(None, 2)
        if len(fields) == 3:
            processes.append((int(fields[0]), int(fields[1]), fields[2]))
    owned = {pid}
    for _ in range(10):
        expanded = owned | {child for child, parent, _ in processes if parent in owned}
        if expanded == owned:
            break
        owned = expanded
    library = ctypes.CDLL("/usr/lib/libproc.dylib")
    footprints = []
    for child, _, name in processes:
        if child not in owned:
            continue
        buffer = ctypes.create_string_buffer(4096)
        if library.proc_pid_rusage(child, 0, ctypes.byref(buffer)) == 0:
            footprints.append(
                {
                    "pid": child,
                    "comm": name,
                    "phys_footprint_bytes": struct.unpack_from("Q", buffer, 72)[0],
                    "resident_bytes": struct.unpack_from("Q", buffer, 64)[0],
                }
            )
    return {
        "time": now(),
        "physical_memory_bytes": int(read(["sysctl", "-n", "hw.memsize"])),
        "host_vm_stat": read(["vm_stat"]),
        "free_percent": int(free[1]),
        "kernel_pressure_level": int(
            read(["sysctl", "-n", "kern.memorystatus_vm_pressure_level"])
        ),
        "swap_used_mib": float(used[1]),
        "disk_free_bytes": shutil.disk_usage(destination).free,
        "owned_processes": footprints,
    }


def observed_run_ids(identifier: str, config_hash: str) -> dict[str, list[str]]:
    found = {}
    for folder, scope in [
        ("standin", "peixinho-standin-v1"),
        ("automation", "python-automation-v1"),
    ]:
        ids = []
        for path in (REPO / "results" / folder / "runs").glob("*/manifest.json"):
            try:
                manifest = json.loads(path.read_text())
            except (OSError, ValueError):
                continue
            if (
                isinstance(manifest, dict)
                and manifest.get("supervision_id") == identifier
                and manifest.get("config_hash") == config_hash
                and manifest.get("benchmark_scope") == scope
            ):
                ids.append(manifest["run_id"])
        found[scope] = sorted(ids)
    return found


def supervise(config: Path, output: Path, deadline: int = 7200, trials: int = 1) -> int:
    cfg, content = committed_config(config)
    source_revision = git_sha()
    if not re.fullmatch("[0-9a-f]{12,40}", source_revision):
        raise ValueError(
            "commit benchmark source/config changes before a supervised run"
        )
    baseline_count, baseline_spread = admission_settings(cfg, deadline, trials)
    identifier = uuid.uuid4().hex
    config_sha = hashlib.sha256(content).hexdigest()
    plan = capacity_plan(cfg)
    floor = None if plan is not None else launch_floor(cfg)
    if not 1 <= trials <= 20 or not 1 <= deadline <= 86400:
        raise ValueError("invalid trial/deadline bounds")
    environment = os.environ.copy()
    for key, value in cfg.get("required_runner_environment", {}).items():
        if not isinstance(key, str) or not isinstance(value, str):
            raise TypeError("runner environment must be strings")
        environment[key] = value
    environment["BENCH_SUPERVISION_ID"] = identifier
    environment["BENCH_ADMITTED_CONFIG_SHA256"] = config_sha
    environment["BENCH_SUPERVISION_OUTPUT"] = str(output.resolve())
    output.mkdir(parents=True, exist_ok=False)
    try:
        baseline = []
        with (output / "baseline.jsonl").open("x", buffering=1) as log:
            for index in range(baseline_count):
                if index:
                    time.sleep(5)
                point = sample(os.getpid(), output)
                baseline.append(point)
                log.write(json.dumps(point) + "\n")
        initial = baseline[-1]
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
        write_json(
            output / "outcome.json",
            {
                "time": now(),
                "returncode": None,
                "stop_reason": f"resource preflight error: {exc}",
                "model_started": False,
            },
        )
        return 2
    relative = str(config.resolve().relative_to(REPO.resolve()))
    (output / "config.yaml").write_bytes(content)
    started = time.monotonic()
    argv = [
        sys.executable,
        str(REPO / "runner/run_bench.py"),
        "--config",
        relative,
        "--trials",
        str(trials),
    ]
    policy = {
        "launch_min_free_percent": floor,
        "launch_baseline_samples": baseline_count,
        "launch_max_percent_spread": baseline_spread,
        "launch_max_swap_spread_mib_exclusive": 64,
        "stop_min_free_percent": None if plan is not None else 10,
        "admission_mode": "capacity" if plan is not None else "legacy_percent",
        "capacity_plan": plan,
        "sustained_samples": 2,
        "sample_seconds": 5,
        "critical_pressure_immediate": True,
        "swap_growth_stop_mib": 2048,
        "swap_absolute_stop_mib": 16384,
        "disk_min_gib": 10,
    }
    write_json(
        output / "invocation.json",
        {
            "resource_probe": cfg.get("resource_probe", False),
            "memory_accounting": {
                "free_percent": "kernel memorystatus level; not raw free RAM or available GiB",
                "owned_processes": "OS process counters; incomplete GPU/model accounting; do not sum into an admission budget",
                "backend": cfg.get("inference_engine"),
                "backend_allocator": "not sampled here; inspect backend request telemetry separately; not additive to OS counters",
            },
            "argv": argv,
            "supervision_id": identifier,
            "config_sha256": config_sha,
            "supervisor_git_sha": source_revision,
            "supervisor_versions": {
                name: hashlib.sha256(
                    Path(__file__).with_name(name).read_bytes()
                ).hexdigest()
                for name in (
                    "supervise_bench.py",
                    "owned_process.py",
                    "bench_common.py",
                    "run_standin_suite.py",
                )
                + (
                    ("capacity_admission.py", "probe_mei.py")
                    if plan is not None
                    else ()
                )
            },
            "cwd": str(REPO),
            "initial": initial,
            "deadline_seconds": deadline,
            "resource_policy": policy,
        },
    )
    if not baseline_ready(baseline, floor, baseline_spread) or (
        plan is not None and not capacity_fits(plan, baseline)
    ):
        write_json(
            output / "outcome.json",
            {
                "time": now(),
                "returncode": None,
                "stop_reason": "resource preflight declined",
                "model_started": False,
                "runner_started": False,
                "supervision_id": identifier,
                "run_ids": {},
            },
        )
        print("No model started: resource preflight declined", flush=True)
        return 2
    low = warnings = 0
    reason = None
    process = None
    session = None
    end = time.monotonic() + deadline
    with (
        (output / "child.log").open("w") as log,
        (output / "resources.jsonl").open("x", buffering=1) as telemetry,
    ):
        try:
            process = subprocess.Popen(
                argv,
                cwd=REPO,
                env=environment,
                stdout=log,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
            session = OwnedSession(process)
            write_json(
                output / "process.json",
                {
                    "pid": process.pid,
                    "supervisor_pid": os.getpid(),
                    "pgid": process.pid,
                    "started": now(),
                },
            )
            print("START", process.pid, flush=True)
            while not session.leader_exited():
                current = sample(process.pid, output)
                telemetry.write(json.dumps(current) + "\n")
                low = low + 1 if current["free_percent"] <= 10 else 0
                warnings = warnings + 1 if current["kernel_pressure_level"] >= 2 else 0
                reason = gate_reason(
                    current, initial, low, warnings, percent_stop=plan is None
                )
                if reason is None and time.monotonic() >= end:
                    reason = "deadline"
                if reason is None and (output / "stop.request").exists():
                    reason = "requested teardown"
                if reason:
                    break
                time.sleep(5)
        except KeyboardInterrupt:
            reason = "supervisor interrupted"
        except (
            OSError,
            ValueError,
            TypeError,
            RuntimeError,
            KeyError,
            subprocess.SubprocessError,
        ) as exc:
            reason = f"monitor error: {type(exc).__name__}: {exc}"
        finally:
            if session is not None:
                try:
                    session.stop(grace_seconds=15)
                except (
                    OSError,
                    ValueError,
                    TypeError,
                    RuntimeError,
                    subprocess.SubprocessError,
                ) as exc:
                    reason = f"{reason or 'cleanup'}; {type(exc).__name__}: {exc}"
            returncode = process.returncode if process is not None else None
            registered = observed_run_ids(identifier, config_sha[:12])
            write_json(
                output / "outcome.json",
                {
                    "time": now(),
                    "returncode": returncode,
                    "stop_reason": reason,
                    "runner_started": process is not None,
                    "model_started": True
                    if any(registered.values())
                    else None
                    if process is not None
                    else False,
                    "supervision_id": identifier,
                    "run_ids": registered,
                    "elapsed_seconds": time.monotonic() - started,
                },
            )
    print("DONE", returncode, reason, flush=True)
    return 0 if returncode == 0 and reason is None else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--deadline", type=int, default=7200)
    parser.add_argument("--trials", type=int, default=1)
    args = parser.parse_args()

    def interrupt(_signum, _frame):
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, interrupt)
    raise SystemExit(supervise(args.config, args.output, args.deadline, args.trials))


if __name__ == "__main__":
    main()
