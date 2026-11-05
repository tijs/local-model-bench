"""Guarded short/loaded decode observations from a pinned llama.cpp server.

Uses the same owned-process resource supervisor as Mei qualification. This is
diagnostic timing evidence, never a household/Python score or native admission.
The server's native decode rate is retained; no wall-time TPS is substituted.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import yaml
from capacity_admission import capacity_plan
from llama_provenance import verify_llama_runtime
from mei_provenance import sha256
from qualify_mei_release import request_json
from run_mei_acceptance import (
    REPO,
    committed_native_config,
    monitor_child,
    split_launch_command,
    wait_ready,
)
from run_standin_suite import write_json

SHORT_PROMPT = "List the integers from 1 to 100, separated by commas:\n"


def settings(cfg: dict[str, Any]) -> dict[str, int]:
    value = cfg.get("context_speed_qualification")
    if (
        not isinstance(value, dict)
        or value.keys() != {"repeats", "loaded_tokens", "decode_tokens"}
        or value.get("repeats") != 5
        or type(value.get("repeats")) is not int
        or value.get("decode_tokens") != 128
        or type(value.get("decode_tokens")) is not int
        or type(value.get("loaded_tokens")) is not int
        or not 1024 <= value["loaded_tokens"] <= 60000
        or value["loaded_tokens"] + 128 > cfg["context_cap"]
    ):
        raise ValueError(
            "declare five repeats,128 output tokens and a fitting loaded length"
        )
    return value


def observed(response: dict[str, Any], prompt_tokens: int) -> dict[str, Any]:
    timings = response["timings"]
    count = response["tokens_predicted"]
    speed = timings["predicted_per_second"]
    if (
        type(count) is not int
        or count != 128
        or type(response.get("tokens_evaluated")) is not int
        or response["tokens_evaluated"] != prompt_tokens
        or type(timings.get("prompt_n")) is not int
        or timings["prompt_n"] != prompt_tokens
        or timings.get("cache_n", 0) != 0
        or response.get("truncated") is not False
        or response.get("stop_type") != "limit"
        or not isinstance(response.get("content"), str)
        or not response["content"]
        or not isinstance(speed, (int, float))
        or isinstance(speed, bool)
        or not math.isfinite(speed)
        or speed <= 0
    ):
        raise ValueError(
            "invalid counts, cached/truncated input, finish or native decode rate"
        )
    return {
        "text": response["content"],
        "text_sha256": hashlib.sha256(response["content"].encode()).hexdigest(),
        "prompt_tokens": prompt_tokens,
        "completion_tokens": count,
        "finish_reason": response["stop_type"],
    }


def prepare_prompts(base: str, loaded: int) -> dict[str, list[int]]:
    def tokenize(text: str) -> list[int]:
        tokens = request_json(
            base + "/tokenize",
            {"content": text, "add_special": True, "parse_special": False},
        )["tokens"]
        if not tokens or any(type(t) is not int for t in tokens):
            raise ValueError("native tokenizer did not return token IDs")
        return tokens

    short = tokenize(SHORT_PROMPT)
    suffix = "\n\n" + SHORT_PROMPT
    count = loaded - len(tokenize(suffix))
    for _ in range(3):
        if count <= 0:
            break
        tokens = tokenize(" hello" * count + suffix)
        if len(tokens) == loaded:
            return {"short": short, "loaded": tokens}
        count += loaded - len(tokens)
    raise ValueError(
        "could not construct the exact loaded prompt using native tokenizer"
    )


def succeeded(output: Path) -> bool:
    try:
        q = json.loads((output / "qualification.json").read_text())
        cfg = yaml.safe_load((output / "config.yaml").read_text())
        declared = settings(cfg)
        prompts = json.loads((output / "prompts.json").read_text())
        if (
            prompts.keys() != {"short", "loaded"}
            or any(
                not isinstance(tokens, list) or any(type(t) is not int for t in tokens)
                for tokens in prompts.values()
            )
            or not 0 < len(prompts["short"]) < len(prompts["loaded"])
            or len(prompts["loaded"]) != declared["loaded_tokens"]
            or q["settings"] != declared
            or q["prompt_sha256"]
            != {
                name: hashlib.sha256(json.dumps(tokens).encode()).hexdigest()
                for name, tokens in prompts.items()
            }
        ):
            return False
        expected = {
            (context, phase, repeat)
            for context in ("short", "loaded")
            for phase, repeats in (
                ("cold", (0,)),
                ("warmup", (0,)),
                ("measured", range(1, 6)),
            )
            for repeat in repeats
        }
        rows = q["rows"]
        reference = {
            row["context"]: row["observable"] for row in rows if row["phase"] == "cold"
        }
        return (
            q["status"] == "passed"
            and q["server_stopped"] is True
            and q["expected_model_sha256"] == cfg["model_sha256"]
            and all(
                q["runtime_identity"][key] == cfg["runtime"][key]
                for key in ("binary_sha256", "revision", "shared_libraries")
            )
            and q["pre_run_model_sha256"] == q["expected_model_sha256"]
            and q["post_run_model_sha256"] == q["expected_model_sha256"]
            and {k: v for k, v in q["runtime_identity"].items() if k != "verification"}
            == {
                k: v
                for k, v in q["post_run_runtime_identity"].items()
                if k != "verification"
            }
            and len(rows) == len(expected)
            and {(r["context"], r["phase"], r["repeat"]) for r in rows} == expected
            and all(
                type(row["repeat"]) is int
                and observed(row["response"], len(prompts[row["context"]]))
                == row["observable"]
                == reference[row["context"]]
                and row["decode_tps"]
                == row["response"]["timings"]["predicted_per_second"]
                for row in rows
            )
        )
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return False


def child(cfg: dict[str, Any], output: Path) -> int:
    values = settings(cfg)
    command = split_launch_command(cfg["benchmark_launch_command"])
    model = Path(command[command.index("--model") + 1])
    base = cfg["benchmark_endpoint"].removesuffix("/v1").rstrip("/")
    q: dict[str, Any] = {
        "status": "running",
        "rows": [],
        "command": command,
        "expected_model_sha256": cfg["model_sha256"],
        "settings": values,
        "rate_definition": "native timings.predicted_per_second; keep the pinned engine's own first-token convention",
        "parity_scope": "within-profile greedy text/count/finish only; not cross-model/quant equality",
    }
    process = None
    try:
        q["pre_run_model_sha256"] = sha256(model)
        if q["pre_run_model_sha256"] != cfg["model_sha256"]:
            raise ValueError("GGUF hash mismatch before load")
        with (output / "server.log").open("x") as log:
            process = subprocess.Popen(
                command, cwd=REPO, stdout=log, stderr=subprocess.STDOUT
            )
        wait_ready(process, base + "/v1")
        q["runtime_identity"] = verify_llama_runtime(cfg, base_url=base)
        prompts = prepare_prompts(base, values["loaded_tokens"])
        write_json(output / "prompts.json", prompts)
        q["prompt_sha256"] = {
            name: hashlib.sha256(json.dumps(tokens).encode()).hexdigest()
            for name, tokens in prompts.items()
        }
        for phase, repeats in (
            ("cold", (0,)),
            ("warmup", (0,)),
            ("measured", range(1, 6)),
        ):
            for repeat in repeats:
                order = (
                    ("loaded", "short")
                    if repeat and repeat % 2 == 0
                    else ("short", "loaded")
                )
                for context in order:
                    body = {
                        "prompt": prompts[context],
                        "n_predict": 128,
                        "temperature": 0,
                        "top_p": 1,
                        "top_k": 1,
                        "min_p": 0,
                        "repeat_penalty": 1,
                        "presence_penalty": 0,
                        "frequency_penalty": 0,
                        "seed": 1,
                        "stream": False,
                        "cache_prompt": False,
                    }
                    started = time.monotonic()
                    response = request_json(base + "/completion", body)
                    raw = {
                        "context": context,
                        "phase": phase,
                        "repeat": repeat,
                        "response": response,
                    }
                    with (output / "responses.jsonl").open("a") as journal:
                        journal.write(json.dumps(raw) + "\n")
                    row = raw | {
                        "elapsed_seconds": time.monotonic() - started,
                        "observable": observed(response, len(prompts[context])),
                        "decode_tps": response["timings"]["predicted_per_second"],
                    }
                    q["rows"].append(row)
                    write_json(output / "qualification.json", q)
                    print(
                        f"{phase} {context} {repeat}: {row['decode_tps']:.3f} tok/s",
                        flush=True,
                    )
        q["status"] = "passed"
    except KeyboardInterrupt:
        q.update(status="failed", interrupted=True, error="interrupted")
    except (
        OSError,
        ValueError,
        KeyError,
        TypeError,
        RuntimeError,
        subprocess.SubprocessError,
    ) as exc:
        q.update(status="failed", error=f"{type(exc).__name__}: {exc}")
    finally:
        if process is not None:
            try:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=3)
                    q["server_stop_escalated"] = True
                q["server_stopped"] = True
            except (OSError, subprocess.SubprocessError) as exc:
                q.update(status="failed", server_stopped=False, cleanup_error=str(exc))
        # Persist terminal partials before any lengthy rehash. Interrupted runs
        # are reviewed and rehashed externally after the supervisor has exited.
        write_json(output / "qualification.json", q)
        if q.get("server_stopped") and not q.get("interrupted"):
            try:
                q["post_run_model_sha256"] = sha256(model)
                q["post_run_runtime_identity"] = verify_llama_runtime(cfg)
            except (OSError, ValueError, KeyError) as exc:
                q.update(status="failed", preservation_error=str(exc))
        write_json(output / "qualification.json", q)
    return 0 if succeeded(output) else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--deadline", type=int, default=1800)
    parser.add_argument("--child", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    cfg, content = committed_native_config(args.config.resolve())
    if (
        cfg.get("benchmark_scope") != "context-speed-qualification-v1"
        or cfg.get("inference_engine") != "llama.cpp"
        or cfg.get("orchestration", {}).get("rank_eligible") is not False
        or capacity_plan(cfg) is None
    ):
        raise ValueError(
            "require a pinned capacity-budgeted non-ranking context-speed profile"
        )
    settings(cfg)
    verify_llama_runtime(cfg)
    if args.child:

        def interrupt(_signum, _frame):
            signal.signal(signal.SIGTERM, signal.SIG_IGN)
            raise KeyboardInterrupt

        signal.signal(signal.SIGTERM, interrupt)
        return child(cfg, args.output)
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
