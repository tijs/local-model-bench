"""Client-observed timing for a single, fully consumed Mei chat stream."""

import contextlib
import json
import time
import urllib.request
from typing import Any

from run_prompt import _read_sse_events


def measure_chat_stream(
    base_url: str, payload: dict[str, Any], *, timeout: float = 300
) -> dict[str, Any]:
    """Keep first reasoning/text, first visible text and wall time separate.

    Use a single request with no automatic retry. Require the terminal usage,
    finish reason and DONE frame so a broken stream cannot contribute timing.
    """
    body = {**payload, "stream": True, "stream_options": {"include_usage": True}}
    request = urllib.request.Request(
        base_url.rstrip("/") + "/chat/completions",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "Accept": "text/event-stream"},
    )
    started = time.monotonic()
    first_generated = first_visible = wall = None
    reasoning_parts: list[str] = []
    content_parts: list[str] = []
    finish = usage = None
    with urllib.request.urlopen(request, timeout=timeout) as response:
        headers = time.monotonic() - started
        if response.headers.get_content_type() != "text/event-stream":
            raise ValueError("Mei did not return an SSE stream")
        events = _read_sse_events(response, started + timeout, timeout, 30)
        with contextlib.closing(events):
            for data, _ in events:
                arrived = time.monotonic() - started
                if data == "[DONE]":
                    wall = arrived
                    break
                event = json.loads(data)
                if not isinstance(event, dict) or event.get("error") is not None:
                    raise ValueError("Mei returned an invalid stream event")
                if event.get("usage") is not None:
                    if usage is not None:
                        raise ValueError("Mei returned multiple usage trailers")
                    usage = event["usage"]
                choices = event.get("choices") or []
                if not choices:
                    continue
                if len(choices) != 1:
                    raise ValueError("timing requires exactly one choice")
                choice = choices[0]
                delta = choice.get("delta") or {}
                reasoning = delta.get("reasoning_content") or ""
                content = delta.get("content") or ""
                if delta.get("tool_calls") or not all(
                    isinstance(value, str) for value in (reasoning, content)
                ):
                    raise ValueError("timing requires an ordinary text response")
                if (reasoning or content) and first_generated is None:
                    first_generated = arrived
                if reasoning:
                    reasoning_parts.append(reasoning)
                if content:
                    if first_visible is None:
                        first_visible = arrived
                    content_parts.append(content)
                if choice.get("finish_reason"):
                    finish = choice["finish_reason"]
    if (
        first_generated is None
        or wall is None
        or not isinstance(finish, str)
        or not isinstance(usage, dict)
        or any(
            type(usage.get(key)) is not int
            for key in ("prompt_tokens", "completion_tokens")
        )
    ):
        raise ValueError("Mei stream ended without text, finish, usage or DONE")
    return {
        "headers_seconds": headers,
        "first_generated_seconds": first_generated,
        "first_visible_seconds": first_visible,
        "wall_seconds": wall,
        "finish_reason": finish,
        "reasoning": "".join(reasoning_parts),
        "content": "".join(content_parts),
        "usage": usage,
    }
