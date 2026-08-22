#!/usr/bin/env python3
"""Black-box acceptance and performance probes for one isolated oMLX model.

The artifact is intentionally JSON: it retains exact /v1/models identity,
non-streaming and streaming tool-call shapes, oMLX timing/cache metrics, and an
exact-token 65,536 success / 65,537 rejection context-cap gate.
"""
from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


def request_json(url: str, payload: dict[str, Any] | None = None, timeout: float = 900) -> tuple[dict[str, Any], float]:
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST" if payload is not None else "GET",
    )
    started = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            response_payload = json.loads(response.read())
            # Some long-prefill rejection paths in oMLX 0.6.2 return a
            # JSON OpenAI error envelope with HTTP 200 after JSON keepalive
            # handling. Treat that as a request failure, never as a completion.
            if isinstance(response_payload, dict) and response_payload.get("error"):
                raise RuntimeError(
                    f"HTTP {response.status} error payload: {json.dumps(response_payload, sort_keys=True)}"
                )
            return response_payload, time.monotonic() - started
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code}: {body}") from exc


def request_stream(url: str, payload: dict[str, Any], timeout: float = 900) -> tuple[dict[str, Any], float, float | None]:
    body = dict(payload, stream=True, stream_options={"include_usage": True})
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    started = time.monotonic()
    first_delta = None
    content: list[str] = []
    tool_calls: dict[int, dict[str, Any]] = {}
    finish_reason = None
    usage: dict[str, Any] = {}
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            for raw in response:
                line = raw.decode("utf-8", errors="replace").strip()
                if not line.startswith("data:"):
                    continue
                encoded = line[5:].strip()
                if encoded == "[DONE]":
                    break
                event = json.loads(encoded)
                if event.get("usage"):
                    usage = event["usage"]
                choices = event.get("choices") or []
                if not choices:
                    continue
                choice = choices[0]
                delta = choice.get("delta") or {}
                if (delta.get("content") or delta.get("tool_calls")) and first_delta is None:
                    first_delta = time.monotonic() - started
                if delta.get("content"):
                    content.append(delta["content"])
                for part in delta.get("tool_calls") or []:
                    index = int(part.get("index", 0))
                    call = tool_calls.setdefault(
                        index,
                        {"id": None, "type": "function", "function": {"name": "", "arguments": ""}},
                    )
                    if part.get("id"):
                        call["id"] = part["id"]
                    function = part.get("function") or {}
                    call["function"]["name"] += function.get("name") or ""
                    call["function"]["arguments"] += function.get("arguments") or ""
                if choice.get("finish_reason"):
                    finish_reason = choice["finish_reason"]
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code}: {body}") from exc
    message: dict[str, Any] = {"role": "assistant", "content": "".join(content) or None}
    if tool_calls:
        message["tool_calls"] = [tool_calls[i] for i in sorted(tool_calls)]
    return {
        "choices": [{"message": message, "finish_reason": finish_reason}],
        "usage": usage,
    }, time.monotonic() - started, first_delta


def validate_add_call(response: dict[str, Any]) -> dict[str, Any]:
    choices = response.get("choices") or []
    message = (choices[0].get("message") or {}) if choices else {}
    calls = message.get("tool_calls") or []
    if len(calls) != 1:
        raise AssertionError(f"expected one structured tool call, got {calls!r}")
    function = calls[0].get("function") or {}
    if function.get("name") != "add_numbers":
        raise AssertionError(f"unexpected tool name: {function.get('name')!r}")
    arguments = json.loads(function.get("arguments") or "{}")
    if arguments != {"a": 15, "b": 27}:
        raise AssertionError(f"schema/argument mismatch: {arguments!r}")
    finish_reason = choices[0].get("finish_reason")
    if finish_reason != "tool_calls":
        raise AssertionError(f"unexpected finish_reason: {finish_reason!r}")
    return {"name": function["name"], "arguments": arguments, "finish_reason": finish_reason}


def exact_prompt(tokenizer_path: Path, target: int) -> str:
    from transformers import AutoTokenizer  # type: ignore[import-not-found]

    tokenizer = AutoTokenizer.from_pretrained(tokenizer_path, trust_remote_code=False)
    unit = " hello"
    if len(tokenizer.encode(unit, add_special_tokens=False)) != 1:
        raise RuntimeError("the exact-token prompt unit is not one token for this tokenizer")
    prompt = unit * target
    measured = len(tokenizer.encode(prompt, add_special_tokens=False))
    if measured != target:
        raise RuntimeError(f"exact-token prompt measured {measured}, expected {target}")
    return prompt


def probe(name: str, output: dict[str, Any], fn) -> None:
    started = time.monotonic()
    try:
        detail = fn()
        output["probes"][name] = {"status": "passed", "elapsed_seconds": time.monotonic() - started, **detail}
    except BaseException as exc:
        output["probes"][name] = {
            "status": "failed",
            "elapsed_seconds": time.monotonic() - started,
            "error": f"{type(exc).__name__}: {exc}",
        }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8020/v1")
    parser.add_argument("--model", required=True)
    parser.add_argument("--tokenizer", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--context-cap", type=int, default=65536)
    parser.add_argument("--timeout", type=float, default=1800)
    parser.add_argument("--skip-context", action="store_true")
    parser.add_argument("--skip-cache", action="store_true")
    args = parser.parse_args()

    result: dict[str, Any] = {
        "model": args.model,
        "base_url": args.base_url,
        "context_cap": args.context_cap,
        "started_epoch": time.time(),
        "probes": {},
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    chat_url = f"{args.base_url.rstrip('/')}/chat/completions"
    models_url = f"{args.base_url.rstrip('/')}/models"
    completions_url = f"{args.base_url.rstrip('/')}/completions"

    def identity() -> dict[str, Any]:
        response, elapsed = request_json(models_url, timeout=30)
        ids = [entry.get("id") for entry in response.get("data", [])]
        if args.model not in ids:
            raise AssertionError(f"exact model ID {args.model!r} absent from {ids!r}")
        return {"served_ids": ids, "request_seconds": elapsed}

    probe("models_identity", result, identity)

    def plain() -> dict[str, Any]:
        response, elapsed = request_json(chat_url, {
            "model": args.model,
            "messages": [{"role": "user", "content": "Reply with exactly: ready"}],
            "temperature": 0,
            "max_tokens": 8,
            "stream": False,
        }, timeout=args.timeout)
        choices = response.get("choices") or []
        content = ((choices[0].get("message") or {}).get("content") or "") if choices else ""
        if not content.strip():
            raise AssertionError("plain completion returned empty content")
        return {"content": content, "usage": response.get("usage"), "request_seconds": elapsed}

    probe("plain_completion", result, plain)

    tools = [{
        "type": "function",
        "function": {
            "name": "add_numbers",
            "description": "Adds two numbers and returns the sum.",
            "parameters": {
                "type": "object",
                "properties": {"a": {"type": "number"}, "b": {"type": "number"}},
                "required": ["a", "b"],
                "additionalProperties": False,
            },
        },
    }]
    tool_payload = {
        "model": args.model,
        "messages": [
            {"role": "system", "content": "You are a helpful assistant with access to one tool."},
            {"role": "user", "content": "What is 15 + 27? You must use add_numbers to compute it."},
        ],
        "tools": tools,
        "tool_choice": {"type": "function", "function": {"name": "add_numbers"}},
        "temperature": 0,
        "max_tokens": 256,
        "stream": False,
    }

    def nonstream_tool() -> dict[str, Any]:
        response, elapsed = request_json(chat_url, tool_payload, timeout=args.timeout)
        return {"validated_call": validate_add_call(response), "raw_response": response, "request_seconds": elapsed}

    probe("tool_nonstreaming", result, nonstream_tool)

    def stream_tool() -> dict[str, Any]:
        response, elapsed, ttft = request_stream(chat_url, tool_payload, timeout=args.timeout)
        return {"validated_call": validate_add_call(response), "assembled_response": response, "request_seconds": elapsed, "client_ttft_seconds": ttft}

    probe("tool_streaming", result, stream_tool)

    # Repeating an identical 2K-token prefix records hot/SSD behavior through
    # usage.prompt_tokens_details.cached_tokens and oMLX's native PP/TG fields.
    cache_prompt = "Summarize the final instruction only. " + ("stable prefix text " * 2048) + " Final instruction: reply cache-ready."
    if not args.skip_cache:
        for repetition in (1, 2):
            def cache_request(repetition=repetition) -> dict[str, Any]:
                response, elapsed = request_json(chat_url, {
                    "model": args.model,
                    "messages": [{"role": "user", "content": cache_prompt}],
                    "temperature": 0,
                    "max_tokens": 16,
                    "stream": False,
                }, timeout=args.timeout)
                return {"usage": response.get("usage"), "request_seconds": elapsed}
            probe(f"cache_repeat_{repetition}", result, cache_request)

    if not args.skip_context:
        prompt_at_cap = exact_prompt(args.tokenizer, args.context_cap)

        def context_at_cap() -> dict[str, Any]:
            response, elapsed = request_json(completions_url, {
                "model": args.model,
                "prompt": prompt_at_cap,
                "temperature": 0,
                "max_tokens": 1,
                "stream": False,
            }, timeout=args.timeout)
            usage = response.get("usage") or {}
            if int(usage.get("prompt_tokens", -1)) != args.context_cap:
                raise AssertionError(f"usage did not confirm {args.context_cap} prompt tokens: {usage!r}")
            if int(usage.get("completion_tokens", 0)) < 1:
                raise AssertionError(f"no completion at exact context cap: {usage!r}")
            return {"usage": usage, "request_seconds": elapsed}

        probe("context_exact_cap", result, context_at_cap)

        def context_over_cap() -> dict[str, Any]:
            over = exact_prompt(args.tokenizer, args.context_cap + 1)
            try:
                response, elapsed = request_json(completions_url, {
                    "model": args.model,
                    "prompt": over,
                    "temperature": 0,
                    "max_tokens": 1,
                    "stream": False,
                }, timeout=args.timeout)
            except RuntimeError as exc:
                if "HTTP 400" not in str(exc):
                    raise
                return {"rejected_as_expected": True, "error": str(exc)}
            raise AssertionError(f"{args.context_cap + 1}-token prompt unexpectedly succeeded in {elapsed:.3f}s: {response!r}")

        probe("context_over_cap_rejected", result, context_over_cap)

    result["finished_epoch"] = time.time()
    result["status"] = "passed" if all(p["status"] == "passed" for p in result["probes"].values()) else "failed"
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
