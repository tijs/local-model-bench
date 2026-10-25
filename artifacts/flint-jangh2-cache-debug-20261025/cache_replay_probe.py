"""Exact-pack HTTP cache correctness regression, independent of retired drivers."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "runner"))
from probe_mei import request_json, request_stream

parser = argparse.ArgumentParser()
parser.add_argument("--output", type=Path, required=True)
parser.add_argument("--cache-disabled", action="store_true")
args = parser.parse_args()
model = "OsaurusAI/Flint-40B-A2.5B-JANGH2"
base = "http://127.0.0.1:8024/v1"
results: dict[str, Any] = {}
system = "You are concise. " + "Stable cache prefix. " * 160
messages = [
    {"role": "system", "content": system},
    {"role": "user", "content": "Reply with exactly: ORANGE"},
]


def run(
    name: str,
    conversation: list[dict[str, Any]],
    expected: str,
    *,
    require_cache: bool = False,
    reference: dict[str, Any] | None = None,
    stream: bool = False,
) -> dict[str, Any]:
    payload = {
        "model": model,
        "messages": conversation,
        "temperature": 0,
        "max_tokens": 1024,
        "stream": stream,
    }
    row: dict[str, Any] = {"request": payload}
    response: dict[str, Any] = {}
    try:
        if stream:
            response, seconds, ttft = request_stream(
                base + "/chat/completions", payload, timeout=600
            )
            row["ttft_seconds"] = ttft
        else:
            response, seconds = request_json(
                base + "/chat/completions", payload, timeout=600
            )
        row.update(response=response, seconds=seconds)
        choice = response["choices"][0]
        message = choice["message"]
        assert choice["finish_reason"] == "stop", choice
        assert message["content"] == expected, message
        assert not any(
            marker in message["content"]
            for marker in ["<think>", "</think>", "<|", "<tool_call>"]
        )
        cached = (response["usage"].get("prompt_tokens_details") or {}).get(
            "cached_tokens", 0
        )
        row["cached_tokens"] = cached
        if args.cache_disabled:
            assert cached == 0, f"disabled-cache baseline reported reuse: {cached}"
        elif require_cache:
            assert cached > 500, f"regression must exercise a real prefix hit: {cached}"
        if reference:
            original = reference["choices"][0]["message"]
            assert message["content"] == original["content"]
            if not stream:
                assert message.get("reasoning_content") == original.get(
                    "reasoning_content"
                ), "reasoning changed on identical greedy request"
            assert (
                response["usage"]["completion_tokens"]
                == reference["usage"]["completion_tokens"]
            )
        row["status"] = "passed"
    except (
        AssertionError,
        KeyError,
        TypeError,
        ValueError,
        RuntimeError,
        OSError,
    ) as exc:
        row.update(status="failed", error=str(exc))
    results[name] = row
    args.output.write_text(json.dumps(results, indent=2) + "\n")
    print(
        name,
        row["status"],
        row.get("cached_tokens"),
        row.get("error", "")[:180],
        flush=True,
    )
    return response


cold = run("cold_a", messages, "ORANGE")
run("immediate_repeat", messages, "ORANGE", require_cache=True, reference=cold)
run(
    "diverging_b",
    [messages[0], {"role": "user", "content": "Reply with exactly: PURPLE"}],
    "PURPLE",
)
run("repeat_after_divergence", messages, "ORANGE", require_cache=True, reference=cold)
run(
    "streamed_repeat",
    messages,
    "ORANGE",
    require_cache=True,
    reference=cold,
    stream=True,
)
if cold:
    history = messages + [cold["choices"][0]["message"]]
    run(
        "growing_turn",
        history + [{"role": "user", "content": "Now reply with exactly: GREEN"}],
        "GREEN",
        require_cache=True,
    )
    run(
        "diverging_grown_turn",
        history + [{"role": "user", "content": "Now reply with exactly: BLUE"}],
        "BLUE",
        require_cache=True,
    )
status, _ = request_json(base + "/mei/status")
assert status["cacheReuse"] == (not args.cache_disabled), status
args.output.with_suffix(".status.json").write_text(json.dumps(status, indent=2) + "\n")
sys.exit(0 if all(v["status"] == "passed" for v in results.values()) else 1)
