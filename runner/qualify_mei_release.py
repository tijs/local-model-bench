"""Guarded raw-completion measurements for a pinned Mei release candidate.

Uses the native runner's committed-config, provenance, ownership and resource
guards. These are runtime qualification observations, never scored task rows.
Each invocation owns one fresh process/cache. Balance control/candidate process
order externally; keep cold determinism observations and exclude warmups from
timing summaries. Native tools/cache/context admission remains a separate gate.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import signal
import socket
import subprocess
import sys
import threading
import time
import urllib.request
from pathlib import Path
from typing import Any

import yaml
from mei_clean_speed import STOPPER, git_bytes, launch_receipt, verify_receipt
from mei_provenance import verify_mei_runtime
from run_mei_acceptance import (
    REPO,
    committed_native_config,
    monitor_child,
    split_launch_command,
    validate_owned_config,
    wait_ready,
)
from run_standin_suite import write_json
from tokenizers import Tokenizer


def qualification_settings(cfg: dict[str, Any]) -> dict[str, int | float]:
    settings = cfg.get("mei_qualification", {})
    required = {"repeats", "loaded_tokens", "decode_tokens", "status_timeout"}
    if not isinstance(settings, dict) or settings.keys() != required:
        raise ValueError(f"mei_qualification must declare exactly {sorted(required)}")
    for name, lower, upper in (
        ("repeats", 1, 20),
        ("loaded_tokens", 1024, 60000),
        ("decode_tokens", 32, 512),
    ):
        value = settings[name]
        if type(value) is not int or not lower <= value <= upper:
            raise ValueError(f"invalid {name}: expected integer {lower}..{upper}")
    timeout = settings["status_timeout"]
    if type(timeout) not in (int, float) or not 0.1 <= timeout <= 5:
        raise ValueError("status_timeout must be 0.1..5 seconds")
    if settings["loaded_tokens"] + settings["decode_tokens"] > cfg["context_cap"]:
        raise ValueError("qualification prompt plus generation exceeds context cap")
    return settings


def request_json(
    url: str, payload: dict[str, Any] | None = None, timeout: float = 600
) -> dict:
    data = None if payload is None else json.dumps(payload).encode()
    request = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        result = json.load(response)
    if not isinstance(result, dict):
        raise TypeError("expected a JSON response object")
    return result


def observable(response: dict) -> dict:
    """Compare observable output/counts, without claiming hidden token IDs."""
    choice = response["choices"][0]
    usage = response["usage"]
    if "text" in choice and "message" not in choice:
        text = choice["text"]
    elif "message" in choice and "text" not in choice:
        # Published rc.2 uses a chat-shaped envelope for raw completions.
        # Keep that historical control measurable without relabeling its API.
        text = choice["message"]["content"]
    else:
        raise ValueError("unrecognized or ambiguous completion response shape")
    count = usage["completion_tokens"]
    speed = usage.get("tokens_per_second")
    if not isinstance(text, str) or not text or type(count) is not int or count <= 0:
        raise ValueError("completion has no generated text/tokens")
    if type(speed) not in (int, float) or not 0 < speed < float("inf"):
        raise ValueError("completion has no finite positive decode rate")
    return {
        "text": text,
        "text_sha256": hashlib.sha256(text.encode()).hexdigest(),
        "completion_tokens": count,
        "prompt_tokens": usage["prompt_tokens"],
        "finish_reason": choice["finish_reason"],
    }


def prepare_prompts(model_dir: Path, loaded_tokens: int) -> dict[str, str]:
    """Count locally before model load; both contexts end in the same task."""
    tokenizer = Tokenizer.from_file(str(model_dir / "tokenizer.json"))
    short = "List the integers from 1 to 100, separated by commas:\n"
    suffix = "\n\n" + short
    filler_count = loaded_tokens - len(
        tokenizer.encode(suffix, add_special_tokens=False).ids
    )
    for _ in range(3):
        if filler_count <= 0:
            break
        loaded = " hello" * filler_count + suffix
        count = len(tokenizer.encode(loaded, add_special_tokens=False).ids)
        if count == loaded_tokens:
            return {"short": short, "loaded": loaded}
        filler_count += loaded_tokens - count
    raise ValueError(
        "could not construct the declared loaded context with the local tokenizer"
    )


def acceptance_succeeded(returncode: int, log: str, expected_tests: int) -> bool:
    return returncode == 0 and bool(
        re.search(rf"Executed {expected_tests} tests, with 0 failures", log)
    )


def serving_settings(status: dict, command: list[str]) -> dict[str, int]:
    budget = status.get("maxTokens")
    if type(budget) is not int or budget <= 0:
        raise ValueError("server did not advertise a normal output budget")
    result = {"normal_output_budget": budget}
    if "--cache-limit-bytes" in command:
        expected = int(command[command.index("--cache-limit-bytes") + 1])
        memory = status.get("memory")
        actual = memory.get("cacheLimitBytes") if isinstance(memory, dict) else None
        if type(actual) is not int or actual != expected:
            raise ValueError(
                "effective allocator-cache limit differs from the launch profile"
            )
        result["observed_allocator_cache_limit_bytes"] = actual
    if "--memory-limit-bytes" in command:
        expected = int(command[command.index("--memory-limit-bytes") + 1])
        memory = status.get("memory")
        actual = memory.get("memoryLimitBytes") if isinstance(memory, dict) else None
        # Zero requests backend auto policy; a positive limit must take effect.
        if (
            type(actual) is not int
            or actual <= 0
            or (expected > 0 and actual != expected)
        ):
            raise ValueError(
                "effective allocator-memory limit differs from the launch profile"
            )
        result["observed_allocator_memory_limit_bytes"] = actual
    return result


def acceptance_identity(cfg: dict) -> dict | None:
    spec = cfg.get("mei_swift_acceptance")
    if spec is None:
        return None
    if not isinstance(spec, dict) or set(spec) != {
        "bundle",
        "executable_sha256",
        "expected_tests",
    }:
        raise ValueError("invalid pinned Swift acceptance specification")
    bundle = Path(spec["bundle"])
    if (
        not bundle.is_absolute()
        or bundle.suffix != ".xctest"
        or type(spec["expected_tests"]) is not int
        or spec["expected_tests"] < 9
    ):
        raise ValueError(
            "Swift acceptance requires an absolute test bundle and at least nine tests"
        )
    with (bundle / "Contents/MacOS/MeiTests").open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    if digest != spec["executable_sha256"]:
        raise ValueError("Swift acceptance executable changed")
    return dict(spec)


def succeeded(output: Path) -> bool:
    try:
        result = json.loads((output / "qualification.json").read_text())
        config_path = output / "config.yaml"
        config_bytes = config_path.read_bytes() if config_path.exists() else None
        cfg = yaml.safe_load(config_bytes) if config_bytes is not None else {}
        if (
            result.get("clean_speed_launch_required", False)
            or "mei_clean_speed_launch" in cfg
        ):
            if result.get("clean_speed_launch_required") is not True:
                return False
            invocation = json.loads((output / "invocation.json").read_text())
            if config_bytes is None or hashlib.sha256(
                config_bytes
            ).hexdigest() != invocation.get("config_sha256"):
                return False
            receipt = json.loads((output / "clean-speed-launch.json").read_text())
            if result.get("clean_speed_launch") != receipt:
                return False
            verify_receipt(
                REPO,
                cfg,
                split_launch_command(cfg["benchmark_launch_command"]),
                invocation,
                receipt,
                output / "launcher-executed.sh",
                output / "stopper-executed.sh",
            )
        settings = result["settings"]
        measurements = [row for row in result["rows"] if row["phase"] == "measured"]
        expected = {
            (context, repeat)
            for context in ("short", "loaded")
            for repeat in range(1, settings["repeats"] + 1)
        }
        return (
            result["status"] == "passed"
            and len(measurements) == settings["repeats"] * 2
            and {(row["context"], row["repeat"]) for row in measurements} == expected
            and all(
                math.isfinite(row["decode_tps"]) and row["decode_tps"] > 0
                for row in measurements
            )
            and bool(result["status_samples"])
            and any(
                row.get("active_generations", 0) > 0 for row in result["status_samples"]
            )
            and all(row["ok"] for row in result["status_samples"])
            and result["server_stopped"] is True
            and (
                not result.get("clean_speed_launch_required", False)
                or isinstance(result.get("clean_speed_launch"), dict)
            )
            and (
                not result.get("swift_acceptance_required", False)
                or result.get("swift_acceptance", {}).get("passed") is True
            )
        )
    except (OSError, ValueError, KeyError, TypeError, yaml.YAMLError):
        return False


def child(cfg: dict, output: Path) -> int:
    settings = qualification_settings(cfg)
    base = cfg["benchmark_endpoint"].rstrip("/")
    model = cfg["orchestration"]["served_model_id"]
    command = split_launch_command(cfg["benchmark_launch_command"])
    environment = dict(os.environ, **cfg["required_runner_environment"])
    runtime = Path(environment["MEI_RUNTIME_BASE"])
    result: dict[str, Any] = {
        "status": "running",
        "settings": settings,
        "rows": [],
        "status_samples": [],
        "swift_acceptance_required": cfg.get("mei_swift_acceptance") is not None,
        "clean_speed_launch_required": "mei_clean_speed_launch" in cfg,
        "command": command,
        "model": model,
        "parity_scope": "HTTP text bytes, generated count and finish; hidden sampled token IDs are not exposed",
    }
    done = threading.Event()
    process = None
    sampler = None
    clean_receipt = None
    stopper = None
    checkpoint_failed = False

    def checkpoint() -> None:
        nonlocal checkpoint_failed
        try:
            write_json(output / "qualification.json", result)
        except OSError as exc:
            checkpoint_failed = True
            result.update(
                status="failed", evidence_error=f"{type(exc).__name__}: {exc}"
            )

    def status_samples():
        with (output / "status-samples.jsonl").open("x", buffering=1) as stream:
            sample_status(stream)

    def sample_status(stream):
        while not done.is_set():
            started = time.time()
            row: dict[str, Any] = {"started_epoch": started}
            begin = time.monotonic()
            try:
                status = request_json(
                    base + "/mei/status", timeout=float(settings["status_timeout"])
                )
                scheduler = status.get("scheduler")
                if (
                    not isinstance(scheduler, dict)
                    or type(scheduler.get("activeGenerations")) is not int
                ):
                    raise ValueError("status has no valid active-generation counter")
                row.update(
                    ok=status.get("status") == "ok",
                    active_generations=scheduler["activeGenerations"],
                )
                memory = status.get("memory")
                if isinstance(memory, dict):
                    row["memory"] = memory
            except (OSError, ValueError, TypeError) as exc:
                row.update(ok=False, error=f"{type(exc).__name__}: {exc}")
            row["elapsed_seconds"] = time.monotonic() - begin
            result["status_samples"].append(row)
            stream.write(json.dumps(row) + "\n")
            done.wait(0.5)

    def completion(context: str, prompt: str, phase: str, repeat: int):
        body = {
            "model": model,
            "prompt": prompt,
            "temperature": 0,
            "top_p": 1,
            "top_k": 1,
            "max_tokens": settings["decode_tokens"],
            "seed": 1,
            "stream": False,
        }
        started_epoch = time.time()
        start = time.monotonic()
        response = request_json(base + "/completions", body)
        with (output / "responses.jsonl").open("a") as stream:
            stream.write(
                json.dumps(
                    {
                        "context": context,
                        "phase": phase,
                        "repeat": repeat,
                        "started_epoch": started_epoch,
                        "response": response,
                    }
                )
                + "\n"
            )
        fields = observable(response)
        if context == "loaded" and fields["prompt_tokens"] != settings["loaded_tokens"]:
            raise ValueError("tokenizer did not produce the declared loaded context")
        row = {
            "context": context,
            "phase": phase,
            "repeat": repeat,
            "started_epoch": started_epoch,
            "elapsed_seconds": time.monotonic() - start,
            "response": response,
            "observable": fields,
            "decode_tps": response["usage"]["tokens_per_second"],
        }
        result["rows"].append(row)
        write_json(output / "qualification.json", result)
        print(f"{phase} {context} {repeat}: {row['decode_tps']:.3f} tok/s", flush=True)

    try:
        model_dir = Path(command[command.index("--model-dir") + 1])
        prompts = prepare_prompts(model_dir, int(settings["loaded_tokens"]))
        acceptance = acceptance_identity(cfg)
        write_json(output / "prompts.json", prompts)
        result["prompt_sha256"] = {
            name: hashlib.sha256(prompt.encode()).hexdigest()
            for name, prompt in prompts.items()
        }
        with (output / "launcher.log").open("x") as log:
            if "mei_clean_speed_launch" in cfg:
                invocation = json.loads((output / "invocation.json").read_text())
                launcher, receipt = launch_receipt(
                    REPO, cfg, command, invocation, verify_worktree=True
                )
                # Preserve and execute the same Git-object bytes. The child has
                # a deliberately small, declared environment; no inherited
                # Bash functions, trace flags, credentials or shell startup.
                with (output / "launcher-executed.sh").open("xb") as source:
                    source.write(launcher)
                stopper = git_bytes(REPO, invocation["runner_git_sha"], STOPPER)
                with (output / "stopper-executed.sh").open("xb") as source:
                    source.write(stopper)
                with (output / "clean-speed-launch.json").open("x") as metadata:
                    json.dump(receipt, metadata, indent=2)
                    metadata.write("\n")
                result["clean_speed_launch"] = receipt
                clean_receipt = receipt
                process = subprocess.Popen(
                    receipt["actual_command"],
                    cwd=REPO,
                    env=receipt["environment"],
                    stdin=subprocess.PIPE,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                )
                if process.stdin is None:
                    raise RuntimeError("clean-speed launcher stdin unavailable")
                process.stdin.write(launcher)
                process.stdin.close()
            else:
                process = subprocess.Popen(
                    command,
                    cwd=REPO,
                    env=environment,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                )
        wait_ready(process, base)
        result["runtime_identity"] = verify_mei_runtime(cfg, base_url=base)
        profile_status = request_json(base + "/mei/status", timeout=5)
        result.update(serving_settings(profile_status, command))
        normal_budget = result["normal_output_budget"]
        # Only observe status during the first cold long prefill. Performance
        # observations below run without HTTP status polling interference.
        completion("short", prompts["short"], "cold", 0)
        sampler = threading.Thread(target=status_samples, daemon=True)
        sampler.start()
        completion("loaded", prompts["loaded"], "cold_status", 0)
        done.set()
        sampler.join(timeout=6)
        if (
            sampler.is_alive()
            or not result["status_samples"]
            or any(not row["ok"] for row in result["status_samples"])
            or not any(
                row.get("active_generations", 0) > 0 for row in result["status_samples"]
            )
        ):
            raise RuntimeError("status failed during cold loaded-context request")
        for context, prompt in prompts.items():
            completion(context, prompt, "warmup", 0)
        for repeat in range(1, int(settings["repeats"]) + 1):
            order = ("short", "loaded") if repeat % 2 else ("loaded", "short")
            for context in order:
                completion(context, prompts[context], "measured", repeat)
        if acceptance is not None:
            # A prebuilt HTTP client only: never run SwiftPM/builds while a
            # model is loaded. A minimal environment prevents credentials
            # appearing in xctest's automatic diagnostics on a tool error.
            command = [
                "/Applications/Xcode.app/Contents/Developer/usr/bin/xctest",
                "-XCTest",
                "MeiTests.MeiAcceptanceTests",
                acceptance["bundle"],
            ]
            client_env = {
                "PATH": os.defpath,
                "MEI_ACCEPTANCE_BASE_URL": base,
                "MEI_SERVED_MODEL_ID": model,
                "MEI_ACCEPTANCE_TIMEOUT": "600",
                "MEI_ACCEPTANCE_MAX_TOKENS": str(normal_budget),
                "MEI_ACCEPTANCE_JOURNAL": str(output / "swift-live-api.jsonl"),
            }
            with (output / "swift-live-acceptance.log").open("x") as log:
                checked = subprocess.run(
                    command,
                    env=client_env,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    timeout=3600,
                    check=False,
                )
            passed = acceptance_succeeded(
                checked.returncode,
                (output / "swift-live-acceptance.log").read_text(),
                acceptance["expected_tests"],
            )
            journal = output / "swift-live-api.jsonl"
            replies = (
                [json.loads(line) for line in journal.read_text().splitlines()]
                if journal.exists()
                else []
            )
            passed = passed and len(replies) >= acceptance["expected_tests"]
            result["swift_acceptance"] = acceptance | {
                "returncode": checked.returncode,
                "passed": passed,
                "journal_requests": len(replies),
            }
            if not passed:
                raise RuntimeError(
                    "pinned Swift live acceptance did not complete all declared tests"
                )
        result["status"] = "passed"
    except (
        OSError,
        ValueError,
        KeyError,
        TypeError,
        IndexError,
        RuntimeError,
        subprocess.SubprocessError,
        KeyboardInterrupt,
    ) as exc:
        result.update(
            status="failed", error=f"{type(exc).__name__}: {exc}", server_stopped=False
        )
        # Preserve the interruption before any potentially slow teardown.
        checkpoint()
    finally:
        cleanup_interrupted = False

        def defer_interrupt(_signum, _frame):
            nonlocal cleanup_interrupted
            cleanup_interrupted = True

        old_handler = None
        if threading.current_thread() is threading.main_thread():
            old_handler = signal.signal(signal.SIGTERM, defer_interrupt)
        done.set()
        result["server_stopped"] = False
        checkpoint()
        if sampler is not None:
            try:
                sampler.join(timeout=2 if clean_receipt is not None else 6)
            except KeyboardInterrupt:
                cleanup_interrupted = True
        try:
            if process is None:
                raise RuntimeError("server process was not launched")
            if clean_receipt is not None:
                stop = subprocess.run(
                    clean_receipt["stop_command"],
                    input=stopper,
                    env=clean_receipt["environment"],
                    capture_output=True,
                    timeout=7,
                    check=False,
                )
            else:
                stop = subprocess.run(
                    [
                        "bash",
                        str(REPO / "runner/stop_mei_server.sh"),
                        "--runtime-base",
                        str(runtime),
                    ],
                    env=environment,
                    capture_output=True,
                    text=True,
                    timeout=30,
                    check=False,
                )
            if stop.returncode:
                raise RuntimeError(f"server teardown failed: {stop.stderr}")
            result["server_stopped"] = True
        except (
            OSError,
            RuntimeError,
            subprocess.SubprocessError,
            KeyboardInterrupt,
        ) as exc:
            result.update(status="failed", cleanup_error=str(exc), server_stopped=False)
        finally:
            if process is not None:
                try:
                    process.terminate()
                    process.wait(timeout=2 if clean_receipt is not None else 15)
                except (OSError, subprocess.SubprocessError, KeyboardInterrupt) as exc:
                    result.update(
                        status="failed", cleanup_error=str(exc), server_stopped=False
                    )
        if cleanup_interrupted:
            result.update(
                status="failed",
                cleanup_error="interrupted during cleanup",
                server_stopped=False,
            )
        try:
            checkpoint()
        finally:
            if old_handler is not None:
                signal.signal(signal.SIGTERM, old_handler)
    return 0 if not checkpoint_failed and succeeded(output) else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--deadline", type=int, default=3600)
    parser.add_argument("--child", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    cfg, content = committed_native_config(args.config.resolve())
    validate_owned_config(cfg)
    qualification_settings(cfg)
    if cfg.get("benchmark_scope") != "mei-release-qualification-v1":
        raise ValueError("qualification requires its separate diagnostic scope")
    if args.child:

        def interrupt(_signum, _frame):
            raise KeyboardInterrupt

        signal.signal(signal.SIGTERM, interrupt)
        return child(cfg, args.output)
    if Path(cfg["required_runner_environment"]["MEI_RUNTIME_BASE"]).exists():
        raise ValueError("qualification requires a fresh runtime/cache directory")
    for port in (8017, 8024):
        with socket.socket() as connection:
            connection.settimeout(0.5)
            if connection.connect_ex(("127.0.0.1", port)) == 0:
                raise ValueError(f"benchmark port {port} is occupied")
    args.skip_context = True
    args.skip_cache = True
    command = [
        sys.executable,
        str(Path(__file__).resolve()),
        "--config",
        str(args.config.resolve()),
        "--output",
        str(args.output.resolve()),
        "--deadline",
        str(args.deadline),
        "--child",
    ]
    return monitor_child(cfg, content, args, command, diagnostic_check=succeeded)


if __name__ == "__main__":
    raise SystemExit(main())
