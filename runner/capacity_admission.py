"""Profile byte-budget feasibility and diagnostic context-load validation.

A byte budget is an estimate, not a reservation. Actual host pressure and swap
remain independently monitored by the parent supervisor throughout loading.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

from probe_mei import exact_prompt, request_json

COMPONENTS = (
    "model_bytes",
    "context_cache_bytes",
    "retained_cache_bytes",
    "allocator_cache_bytes",
    "workspace_allowance_bytes",
    "host_reserve_bytes",
)


def capacity_plan(cfg: dict[str, Any]) -> dict[str, Any] | None:
    mode = cfg.get("resource_monitor_policy", {}).get(
        "admission_mode", "legacy_percent"
    )
    if mode == "legacy_percent":
        return None
    if mode != "capacity":
        raise ValueError("unknown resource admission mode")
    plan = cfg.get("capacity_plan")
    if not isinstance(plan, dict):
        raise TypeError("capacity admission requires an explicit byte plan")
    for key in COMPONENTS:
        value = plan.get(key)
        if type(value) is not int or not 0 <= value <= 2**50:
            raise ValueError(f"invalid capacity component {key}")
    if plan["model_bytes"] != cfg.get("model_bytes") or plan["model_bytes"] <= 0:
        raise ValueError("capacity model bytes must match pinned model size")
    if plan.get("context_tokens") != cfg.get("context_cap"):
        raise ValueError("capacity context must match configured context cap")
    if (
        plan["context_cache_bytes"] <= 0
        or plan["workspace_allowance_bytes"] <= 0
        or plan["host_reserve_bytes"] <= 0
    ):
        raise ValueError("capacity cache, workspace and host reserve must be positive")
    if not isinstance(plan.get("derivation"), str) or not plan["derivation"].strip():
        raise ValueError("capacity plan requires derivation and uncertainty")
    return dict(plan, total_bytes=sum(plan[key] for key in COMPONENTS))


def capacity_fits(plan: dict[str, Any], samples: list[dict[str, Any]]) -> bool:
    # Physical feasibility only. Do not label this an available-memory estimate.
    return bool(samples) and all(
        type(point.get("physical_memory_bytes")) is int
        and point["physical_memory_bytes"] >= plan["total_bytes"]
        for point in samples
    )


def validate_context(cfg: dict[str, Any], base_url: str, model: str) -> None:
    """Opt-in diagnostic only; persist each completed ramp step before the next."""
    ramp = cfg.get("capacity_context_probe")
    if ramp is None:
        return
    if cfg.get("resource_probe") is not True or cfg.get("diagnostic_only") is not True:
        raise ValueError("context capacity ramp requires a diagnostic resource probe")
    output_env = os.environ.get("BENCH_SUPERVISION_OUTPUT")
    if not output_env:
        raise ValueError("context capacity ramp requires supervisor output")
    targets = ramp.get("prompt_tokens")
    cap = cfg["context_cap"]
    if (
        not isinstance(targets, list)
        or not targets
        or any(
            type(target) is not int or not 1 <= target <= cap - 16 for target in targets
        )
        or targets != sorted(set(targets))
        or targets[-1] != cap - 16
    ):
        raise ValueError("context ramp must increase to context_cap minus16")
    # A declared local tokenizer is verified against actual server usage at each step.
    tokenizer = (
        Path(ramp["tokenizer_directory"]) if ramp.get("tokenizer_directory") else None
    )
    output = Path(output_env) / "context-capacity.json"
    if output.exists():
        raise FileExistsError(output)
    result: dict[str, Any] = {
        "status": "running",
        "context_cap": cap,
        "steps": [],
        "scope": "synthetic prefill/decode allocation test, not long-context quality",
    }

    def save():
        temporary = output.with_suffix(".tmp")
        temporary.write_text(json.dumps(result, indent=2) + "\n")
        temporary.replace(output)

    save()
    try:
        for target in targets:
            if tokenizer is not None:
                # Tokenizer-only operation; do not import a second ML runtime.
                os.environ.setdefault("USE_TORCH", "0")
                os.environ.setdefault("USE_TF", "0")
                prompt = exact_prompt(tokenizer, target)
            elif cfg.get("inference_engine") == "llama.cpp":
                prompt = " hello" * target
                tokenized, _ = request_json(
                    base_url.removesuffix("/v1") + "/tokenize",
                    {
                        "content": prompt,
                        "add_special": False,
                    },
                    timeout=60,
                )
                if len(tokenized.get("tokens", [])) != target:
                    raise ValueError(
                        "server tokenizer did not confirm exact ramp prompt"
                    )
            else:
                raise ValueError("context probe requires a local tokenizer")
            print(f"CAPACITY prompt_tokens={target} max_tokens=16", flush=True)
            started = time.monotonic()
            response, elapsed = request_json(
                base_url.rstrip("/") + "/completions",
                {
                    "model": model,
                    "prompt": prompt,
                    "temperature": 0,
                    "max_tokens": 16,
                    "stream": False,
                },
                timeout=1800,
            )
            usage = response.get("usage") or {}
            result["steps"].append(
                {
                    "target_prompt_tokens": target,
                    "usage": usage,
                    "elapsed_seconds": elapsed,
                    "wall_seconds": time.monotonic() - started,
                }
            )
            save()
            if (
                usage.get("prompt_tokens") != target
                or usage.get("completion_tokens", 0) < 1
            ):
                raise ValueError(
                    "server usage did not confirm context prefill and decode"
                )
            if cfg.get("inference_engine") == "mei":
                status, _ = request_json(
                    base_url.rstrip("/") + "/mei/status", timeout=15
                )
                result["steps"][-1]["backend_status"] = status
                save()
        result["status"] = "passed"
    except BaseException as exc:
        result.update(
            status="interrupted"
            if isinstance(exc, (KeyboardInterrupt, SystemExit))
            else "failed",
            error=f"{type(exc).__name__}: {exc}",
        )
        raise
    finally:
        save()
