"""Run isolated Mei acceptance probes sequentially from benchmark configs.

Launches each mei config's benchmark_launch_command, waits for health, runs
runner/probe_mei.py, and records probe JSON + launcher logs under
~/.local/share/local-model-bench/results-mei/<model>/<config-stem>-<stamp>/.
Historical results are never overwritten. The CLI requires a committed,
capacity-budgeted config and owns the complete launcher/probe/server session.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shlex
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import yaml
from bench_common import git_sha
from capacity_admission import capacity_fits, capacity_plan
from mei_provenance import verify_mei_runtime
from model_storage import model_root
from owned_process import OwnedSession
from run_standin_suite import write_json
from supervise_bench import admission_settings, baseline_ready, gate_reason, sample

REPO = Path(__file__).resolve().parent.parent


def committed_native_config(path: Path) -> tuple[dict[str, Any], bytes]:
    """Verify exact committed config bytes without requiring a scored-task scope."""
    relative = path.resolve().relative_to(REPO.resolve())
    expected = subprocess.run(
        ["git", "show", f"HEAD:{relative.as_posix()}"],
        cwd=REPO,
        capture_output=True,
        check=False,
    )
    content = path.read_bytes()
    if expected.returncode or expected.stdout != content:
        raise ValueError(
            "native acceptance requires exact config bytes committed at HEAD"
        )
    cfg = yaml.safe_load(content)
    if not isinstance(cfg, dict):
        raise TypeError("native config must be a mapping")
    return cfg, content


def split_launch_command(command: str) -> list[str]:
    # YAML |-blocks keep the trailing line-continuation backslashes; strip
    # backslash-newline before shlex, otherwise they become literal "\n"
    # arguments (same handling as the retired oMLX acceptance runner).
    return shlex.split(re.sub(r"\\[ \t]*\n", " ", command))


def get_json(url: str, timeout: float = 10) -> dict[str, Any]:
    with urllib.request.urlopen(url, timeout=timeout) as response:
        return json.loads(response.read())


def wait_ready(process: subprocess.Popen, base_url: str, timeout: float = 900) -> None:
    models_url = f"{base_url.rstrip('/')}/models"
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(
                f"launcher exited before health, rc={process.returncode}"
            )
        try:
            get_json(models_url)
            return
        except (urllib.error.URLError, OSError, ValueError):
            time.sleep(1.0)
    raise TimeoutError(f"Mei /v1/models was not ready after {timeout}s")


def run_config(
    config_path: Path, args: argparse.Namespace, cfg: dict[str, Any] | None = None
) -> dict[str, Any]:
    cfg = cfg if cfg is not None else yaml.safe_load(config_path.read_text()) or {}
    orch = cfg.get("orchestration") or {}
    model = orch.get("served_model_id")
    if cfg.get("inference_engine") != "mei" or not model:
        raise ValueError(f"not a Mei served-model config: {config_path}")

    command = split_launch_command(str(cfg["benchmark_launch_command"]))
    base_url = str(cfg.get("benchmark_endpoint", "http://127.0.0.1:8024/v1"))
    # The launch command's --model-dir is the authoritative tokenizer/model
    # path. Failing that (defensive), try the served-id-name convention:
    # full hub id (mlx-community/Qwen3.8-27B-4bit) then its basename.
    # Staging dir names do NOT always equal the served-id basename
    # (e.g. Qwen3.8-27B-Uncensored-MLX-4bit), so guess-and-check is not
    # reliable — --model-dir is.
    tokenizer_args = [
        command[i + 1] for i, a in enumerate(command) if a == "--model-dir"
    ]
    tokenizer: Path | None = (
        Path(tokenizer_args[0]).expanduser() if tokenizer_args else None
    )
    if tokenizer is None or not (tokenizer / "config.json").exists():
        model_store = model_root("mei")
        candidates = [model_store / model, model_store / model.split("/")[-1]]
        tokenizer = next(
            (p for p in candidates if (p / "config.json").exists()), candidates[1]
        )
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    output_root = getattr(args, "output", None) or (
        Path("~/.local/share/local-model-bench/results-mei").expanduser()
        / model
        / f"{config_path.stem}-{stamp}"
    )
    output_root.mkdir(parents=True, exist_ok=True)
    launch_log = output_root / "launcher.log"
    started = time.time()
    record: dict[str, Any] = {
        "config": str(config_path.relative_to(REPO)),
        "model": model,
        "source_model": cfg.get("model"),
        "command": command,
        "started_epoch": started,
        "output_root": str(output_root),
    }
    environment = dict(os.environ, **cfg.get("required_runner_environment", {}))
    runtime_base = environment["MEI_RUNTIME_BASE"]
    process: subprocess.Popen | None = None
    try:
        with launch_log.open("w") as launch_stream:
            process = subprocess.Popen(
                command,
                cwd=REPO,
                env=environment,
                stdout=launch_stream,
                stderr=subprocess.STDOUT,
                text=True,
            )
            wait_ready(process, base_url)
            record["runtime_identity"] = verify_mei_runtime(cfg, base_url=base_url)
            probe_path = output_root / "probe.json"
            probe_program = (
                Path(command[command.index("--mei-repo") + 1]) / "tools/probe_mei.py"
            )
            record["probe_program"] = str(probe_program)
            record["probe_sha256"] = hashlib.sha256(
                probe_program.read_bytes()
            ).hexdigest()
            probe_cmd = [
                sys.executable,
                str(probe_program),
                "--base-url",
                base_url,
                "--model",
                model,
                "--tokenizer",
                str(tokenizer),
                "--output",
                str(probe_path),
                "--context-cap",
                str(cfg.get("context_cap", 65536)),
            ]
            if args.skip_context:
                probe_cmd.append("--skip-context")
            if args.skip_cache:
                probe_cmd.append("--skip-cache")
            probe = subprocess.run(
                probe_cmd, capture_output=True, text=True, timeout=3600, check=False
            )
            record["probe_rc"] = probe.returncode
            record["probe_stdout"] = probe.stdout[-4000:]
            record["probe_stderr"] = probe.stderr[-2000:]
            record["status"] = "passed" if probe.returncode == 0 else "failed"
    except (
        OSError,
        ValueError,
        RuntimeError,
        KeyboardInterrupt,
        subprocess.SubprocessError,
    ) as exc:
        record["status"] = "error"
        record["error"] = f"{type(exc).__name__}: {exc}"
    finally:
        # Stop the real server FIRST, while the launcher (start_mei_server.sh
        # wrapper) is still alive and its pid file still exists. Terminating
        # the wrapper first triggers its EXIT trap, which deletes the pid
        # file, turning stop_mei_server.sh into a no-op and ORPHANING the Mei
        # server (observed live: leaked ~19-24 GB Metal heaps per run).
        try:
            stopped = subprocess.run(
                [
                    "bash",
                    str(REPO / "runner" / "stop_mei_server.sh"),
                    "--runtime-base",
                    runtime_base,
                ],
                env=environment,
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
            if stopped.returncode != 0:
                raise RuntimeError(f"isolated teardown exited {stopped.returncode}")
            if process is not None:
                process.terminate()
                try:
                    process.wait(timeout=30)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=3)
        except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
            record["status"] = "error"
            record["cleanup_error"] = str(exc)
        finally:
            record["finished_epoch"] = time.time()
            write_json(output_root / "record.json", record)
    return record


def validate_owned_config(cfg: dict[str, Any]) -> dict[str, Any]:
    """Decline legacy/unisolated launchers before starting any process."""
    if cfg.get("inference_engine") != "mei":
        raise ValueError("native acceptance requires a pinned Mei config")
    for key in ("mei_source_commit", "vmlx_commit"):
        if not re.fullmatch(r"[0-9a-f]{40}", str(cfg.get(key, ""))):
            raise ValueError(f"native acceptance requires an exact {key}")
    if not isinstance(cfg.get("orchestration", {}).get("served_model_id"), str):
        raise TypeError("native acceptance requires an exact served-model ID")
    plan = capacity_plan(cfg)
    if plan is None:
        raise ValueError("native acceptance requires capacity admission")
    environment = cfg.get("required_runner_environment", {})
    if not isinstance(environment, dict) or not all(
        isinstance(key, str) and isinstance(value, str)
        for key, value in environment.items()
    ):
        raise ValueError("runner environment must contain strings")
    runtime_base = environment.get("MEI_RUNTIME_BASE", "")
    argv = split_launch_command(cfg["benchmark_launch_command"])
    if (
        not Path(runtime_base).is_absolute()
        or argv.count("--runtime-base") != 1
        or argv.index("--runtime-base") + 1 >= len(argv)
        or argv[argv.index("--runtime-base") + 1] != runtime_base
    ):
        raise ValueError(
            "declare one matching isolated runtime base in command and environment"
        )
    verify_mei_runtime(cfg)
    return plan


def probe_succeeded(output: Path, *, skip_context: bool, skip_cache: bool) -> bool:
    """A zero child exit alone is not native acceptance evidence."""
    try:
        record = json.loads((output / "record.json").read_text())
        result = json.loads((output / "probe.json").read_text())
        probes = result["probes"]
        required = {
            "models_identity",
            "mei_status",
            "plain_completion",
            "tool_nonstreaming",
            "tool_streaming",
            "tool_call_history_replay",
            "parity_stream_vs_nonstream",
        }
        if not skip_cache:
            required |= {
                "cache_repeat_1",
                "cache_repeat_2",
                "cache_growing_turn1",
                "cache_growing_turn2_reuses_slot",
            }
        if not skip_context:
            required |= {"context_exact_cap", "context_over_cap_rejected"}
        return (
            record.get("status") == "passed"
            and result.get("status") == "passed"
            and required <= probes.keys()
            and all(value.get("status") == "passed" for value in probes.values())
        )
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return False


def monitor_child(
    cfg: dict[str, Any], content: bytes, args: argparse.Namespace, command: list[str],
    *, diagnostic_check: Callable[[Path], bool] | None = None,
) -> int:
    """Supervise one unreaped session with the benchmark's actual resource policy."""
    if not 30 <= args.deadline <= 3600:
        raise ValueError("native deadline must be 30..3600 seconds")
    count, spread = admission_settings(cfg, args.deadline, 1)
    if count < 7:
        raise ValueError("native acceptance requires at least seven baseline samples")
    plan = capacity_plan(cfg)
    if plan is None:
        raise ValueError("native acceptance requires a capacity plan")
    output = args.output
    output.mkdir(parents=True, exist_ok=False)
    (output / "config.yaml").write_bytes(content)
    write_json(
        output / "invocation.json",
        {
            "command": command,
            "config_sha256": hashlib.sha256(content).hexdigest(),
            "deadline_seconds": args.deadline,
            "capacity_plan": plan,
            "skip_context": args.skip_context,
            "skip_cache": args.skip_cache,
            "runner_git_sha": git_sha(),
            "diagnostic_only": diagnostic_check is not None,
        },
    )
    baseline = []
    try:
        with (output / "baseline.jsonl").open("x", buffering=1) as stream:
            for index in range(count):
                if index:
                    time.sleep(5)
                point = sample(os.getpid(), output)
                baseline.append(point)
                stream.write(json.dumps(point) + "\n")
    except (
        OSError,
        ValueError,
        RuntimeError,
        subprocess.SubprocessError,
        KeyboardInterrupt,
    ) as exc:
        write_json(
            output / "outcome.json",
            {
                "status": "declined",
                "stop_reason": f"resource preflight error: {exc}",
                "runner_started": False,
                "full_native_admission": False,
            },
        )
        return 2
    if not baseline_ready(baseline, None, spread) or not capacity_fits(plan, baseline):
        write_json(
            output / "outcome.json",
            {
                "status": "declined",
                "stop_reason": "resource preflight declined",
                "runner_started": False,
                "full_native_admission": False,
            },
        )
        return 2
    environment = dict(os.environ, **cfg.get("required_runner_environment", {}))
    environment["BENCH_ADMITTED_CONFIG_SHA256"] = hashlib.sha256(content).hexdigest()
    session = None
    process = None
    reason = None
    warnings = 0
    started = time.monotonic()
    try:
        with (
            (output / "child.log").open("x") as log,
            (output / "resources.jsonl").open("x", buffering=1) as telemetry,
        ):
            process = subprocess.Popen(
                command,
                cwd=REPO,
                env=environment,
                stdout=log,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
            session = OwnedSession(process)
            write_json(
                output / "process.json", {"pid": process.pid, "pgid": process.pid}
            )
            while not session.leader_exited():
                point = sample(process.pid, output)
                telemetry.write(json.dumps(point) + "\n")
                warnings = warnings + 1 if point["kernel_pressure_level"] >= 2 else 0
                reason = gate_reason(
                    point, baseline[-1], 0, warnings, percent_stop=False
                )
                if reason is None and time.monotonic() - started >= args.deadline:
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
        RuntimeError,
        KeyError,
        TypeError,
        subprocess.SubprocessError,
    ) as exc:
        reason = f"monitor error: {type(exc).__name__}: {exc}"
    finally:
        try:
            if session is not None:
                session.stop(grace_seconds=15)
            elif process is not None:
                # Popen created this still-unreaped session. If ownership setup
                # failed, stop its group before releasing the leader's PID.
                os.killpg(process.pid, signal.SIGTERM)
                try:
                    process.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait(timeout=3)
        except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
            reason = f"{reason or 'cleanup'}: {exc}"
        try:
            evidence_passed = (
                diagnostic_check(output) if diagnostic_check is not None else
                probe_succeeded(output, skip_context=args.skip_context, skip_cache=args.skip_cache)
            )
        except (OSError, ValueError, KeyError, TypeError, RuntimeError) as exc:
            reason = f"{reason or 'qualification'}: evidence error: {exc}"
            evidence_passed = False
        passed = bool(
            process is not None
            and process.returncode == 0
            and reason is None
            and evidence_passed
        )
        write_json(
            output / "outcome.json",
            {
                "status": "passed" if passed else "failed",
                "stop_reason": reason,
                "returncode": process.returncode if process is not None else None,
                "elapsed_seconds": time.monotonic() - started,
                "full_native_admission": passed
                and diagnostic_check is None
                and not args.skip_context
                and not args.skip_cache,
                "diagnostic_only": diagnostic_check is not None,
            },
        )
    return 0 if passed else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, help="configs/<model>/mei*.yaml")
    parser.add_argument("--skip-context", action="store_true")
    parser.add_argument("--skip-cache", action="store_true")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--deadline", type=int, default=3600)
    parser.add_argument("--_child", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    config_path = (REPO / args.config).resolve()
    cfg, content = committed_native_config(config_path)
    if not re.fullmatch(r"[0-9a-f]{12,40}", git_sha()):
        raise ValueError("commit benchmark helpers/configs before native acceptance")
    validate_owned_config(cfg)
    if args.output is None:
        model = cfg.get("orchestration", {}).get("served_model_id")
        if not model:
            raise TypeError("native acceptance requires an exact served-model ID")
        stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
        args.output = (
            Path("~/.local/share/local-model-bench/results-mei").expanduser()
            / model
            / f"{config_path.stem}-{stamp}"
        )
    args.output = args.output.resolve()

    def interrupt(_signum, _frame):
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, interrupt)
    if args._child:
        if (
            os.environ.get("BENCH_ADMITTED_CONFIG_SHA256")
            != hashlib.sha256(content).hexdigest()
        ):
            raise ValueError("native child lacks matching parent admission")
        record = run_config(config_path, args, cfg)
        print(json.dumps(record, indent=2, sort_keys=True))
        return 0 if record.get("status") == "passed" else 1

    endpoint = urlparse(cfg["benchmark_endpoint"])
    if endpoint.hostname not in ("127.0.0.1", "localhost") or endpoint.port is None:
        raise ValueError("native acceptance requires an explicit loopback endpoint")
    for port in {8017, 8024, endpoint.port}:
        with socket.socket() as connection:
            connection.settimeout(0.5)
            if connection.connect_ex(("127.0.0.1", port)) == 0:
                raise RuntimeError(f"port {port} is occupied; no model started")
    command = [
        sys.executable,
        str(Path(__file__).resolve()),
        "--_child",
        "--config",
        str(config_path),
        "--output",
        str(args.output),
        "--deadline",
        str(args.deadline),
    ]
    if args.skip_context:
        command.append("--skip-context")
    if args.skip_cache:
        command.append("--skip-cache")
    return monitor_child(cfg, content, args, command)


if __name__ == "__main__":
    raise SystemExit(main())
