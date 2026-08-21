#!/usr/bin/env python3
"""local-model-bench's own copy of the LFM2.5 textual-tool-call OpenAI-
compatibility shim (forked from ~/.hermes/profiles/fitness/mara_local_proxy.py
2026-08-19). Deliberately separate from that file, and NOT the fitness
profile's shared instance, for two reasons:

  1. That proxy unconditionally filters every caller's `tools` array down to
     a lean ~12-tool allowlist tuned for the fitness/Kiri profile's own
     needs. The benchmark needs the FULL tool manifest to actually reach the
     model — that's the entire point of hermes_ops's tool-selection-under-
     load tasks. Silently sharing that proxy gave false-passing results
     (discovered live 2026-08-19: web_search/terminal were being dropped
     before ever reaching the model, and the model can still emit a text
     tool-call for a name it was never given — no schema validation on the
     way out — which further masked the filtering).
  2. Isolation from Tijs's live daily-driver profile: a benchmark run
     shouldn't share a request queue with his actual assistant traffic.

The MLX SimpleEngine accepts one generation at a time.  This proxy therefore
uses one bounded FIFO worker for POST requests so short request bursts wait at
the proxy instead of racing each other into the upstream's busy response.

Still shares the underlying vllm_mlx.server engine (UPSTREAM, port 8012) with
whatever else is running — see AGENTS.md for the resource-contention caveat
that implies during a real benchmark run.
"""
from __future__ import annotations

import ast
from collections import deque
from dataclasses import dataclass, field
import json
import logging
import os
import re
import select
import socket
import threading
import time
import uuid
from collections.abc import Callable
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

UPSTREAM = os.environ.get("BENCH_PROXY_UPSTREAM", "http://127.0.0.1:8012")
LISTEN = ("127.0.0.1", int(os.environ.get("BENCH_PROXY_PORT", "8015")))
THINK_BLOCK = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)
STRAY_TOOL_CALL_TAG = re.compile(r"</?tool_call>", re.IGNORECASE)
LOG = logging.getLogger("bench_local_proxy")

# Different model families emit tool calls as different raw-text formats —
# vllm-mlx has no server-side --tool-call-parser (confirmed: not in
# `vllm_mlx.server --help`, only --reasoning-parser exists, for <think>-style
# extraction). So every family needs its own parser here. Select which one a
# given model needs via BENCH_TOOL_PARSER (see configs/<model>/*.yaml,
# `tool_call_parser:` — cite the model card / creator docs there, same as
# every other setting).
TOOL_CALL_PARSER = os.environ.get("BENCH_TOOL_PARSER", "lfm")

LFM_TOOL_BLOCK = re.compile(r"<\|tool_call_start\|>(.*?)<\|tool_call_end\|>", re.DOTALL)
LFM_SPLIT_MARKER = "<|tool_call_start|>"

# Hermes-style JSON tool-call block (<tool_call>{"name":...,"arguments":{...}}
# </tool_call>) — the format Qwen-family models are commonly trained/fine-
# tuned to emit (used by e.g. vLLM's "hermes" tool-call-parser). NOT YET
# VERIFIED against a real Qwen response from this stack — confirm against an
# actual loaded Qwen model's raw output before trusting this for a real run,
# and correct/replace if its real format differs.
HERMES_TOOL_BLOCK = re.compile(r"<tool_call>\s*(.*?)\s*</tool_call>", re.DOTALL)
HERMES_SPLIT_MARKER = "<tool_call>"

# Qwen3-Coder's "qwen3_xml" format: <tool_call><function=NAME><parameter=ARG>
# VALUE</parameter>...</function></tool_call>. Confirmed live 2026-08-20 by
# reading the ground-truth vLLM parser the model's own HF repo ships
# (qwen3coder_tool_parser.py, registered as "qwen3_xml") — vllm-mlx has no
# server-side tool-call parser at all (only --reasoning-parser), so this is
# reimplemented here rather than assumed from a single raw sample. The
# reference parser tolerates a missing opening <tool_call> tag (back-off:
# treat the whole output as one candidate block if the tag isn't found) —
# matched here too, since a raw spot-check saw exactly that: content ending
# in a stray "</tool_call>" with no opening tag.
QWEN3_CODER_TOOL_CALL_REGEX = re.compile(r"<tool_call>(.*?)</tool_call>|<tool_call>(.*?)$", re.DOTALL)
QWEN3_CODER_FUNCTION_REGEX = re.compile(r"<function=(.*?)</function>|<function=(.*)$", re.DOTALL)
QWEN3_CODER_PARAMETER_REGEX = re.compile(r"<parameter=(.*?)</parameter>|<parameter=(.*?)$", re.DOTALL)
QWEN3_CODER_SPLIT_MARKER = "<function="


def _qwen3_coder_convert_value(value: str) -> object:
    """No tool schema is threaded through to this parser (unlike the
    reference implementation, which uses each parameter's declared JSON
    type) — best-effort numeric/bool coercion, string otherwise. Good
    enough for grading purposes: task checks compare argument values, not
    their Python type."""
    if value.lower() == "true":
        return True
    if value.lower() == "false":
        return False
    if value.lower() == "null":
        return None
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        pass
    return value


def _parse_qwen3_coder_tool_calls(text: str) -> list[dict]:
    if QWEN3_CODER_SPLIT_MARKER not in (text or ""):
        return []
    tool_call_matches = QWEN3_CODER_TOOL_CALL_REGEX.findall(text)
    raw_tool_calls = [match[0] if match[0] else match[1] for match in tool_call_matches]
    if not raw_tool_calls:
        raw_tool_calls = [text]
    raw_function_calls: list[str] = []
    for block in raw_tool_calls:
        raw_function_calls.extend(QWEN3_CODER_FUNCTION_REGEX.findall(block))
    function_calls = [match[0] if match[0] else match[1] for match in raw_function_calls]

    calls: list[dict] = []
    for function_call_str in function_calls:
        if ">" not in function_call_str:
            continue
        end_index = function_call_str.index(">")
        name = function_call_str[:end_index].strip()
        parameters_text = function_call_str[end_index + 1:]
        param_matches = QWEN3_CODER_PARAMETER_REGEX.findall(parameters_text)
        args: dict[str, object] = {}
        for match in param_matches:
            match_text = match[0] if match[0] else match[1]
            if ">" not in match_text:
                continue
            idx = match_text.index(">")
            param_name = match_text[:idx].strip()
            param_value = match_text[idx + 1:]
            if param_value.startswith("\n"):
                param_value = param_value[1:]
            if param_value.endswith("\n"):
                param_value = param_value[:-1]
            args[param_name] = _qwen3_coder_convert_value(param_value)
        calls.append({
            "id": f"call_{uuid.uuid4().hex[:16]}",
            "type": "function",
            "function": {"name": name, "arguments": json.dumps(args, ensure_ascii=False)},
        })
    return calls


POOLSIDE_V1_TOOL_CALL_BLOCK = re.compile(r"<tool_call>(.*?)</tool_call>", re.DOTALL)
POOLSIDE_V1_ARG_PAIR = re.compile(r"<arg_key>(.*?)</arg_key>\s*<arg_value>(.*?)</arg_value>", re.DOTALL)
POOLSIDE_V1_SPLIT_MARKER = "<tool_call>"


def _parse_poolside_v1_tool_calls(text: str) -> list[dict]:
    """poolside's Laguna-XS/S tool-call format: <tool_call>NAME<arg_key>KEY
    </arg_key><arg_value>VALUE</arg_value>...</tool_call>. Confirmed live
    2026-08-20 via a raw spot-check against llama-server (no native
    llama.cpp support for this format — the whole block lands in
    reasoning_content, not content or tool_calls, so this proxy is needed
    for the GGUF leg too, not just MLX). vllm-mlx 0.4.1 registers a
    'poolside_v1' native parser, but its CLI's --tool-call-parser choices=
    list omits it (only reachable via --tool-call-parser auto there) —
    this proxy parser is independent of that and used for both backends."""
    calls: list[dict] = []
    for match in POOLSIDE_V1_TOOL_CALL_BLOCK.finditer(text or ""):
        block = match.group(1)
        first_arg_idx = block.find("<arg_key>")
        name = (block[:first_arg_idx] if first_arg_idx >= 0 else block).strip()
        if not name:
            continue
        args: dict[str, object] = {}
        for key, value in POOLSIDE_V1_ARG_PAIR.findall(block):
            args[key.strip()] = value.strip()
        calls.append({
            "id": f"call_{uuid.uuid4().hex[:16]}",
            "type": "function",
            "function": {"name": name, "arguments": json.dumps(args, ensure_ascii=False)},
        })
    return calls


def _parse_lfm_tool_calls(text: str) -> list[dict]:
    """LFM's format: <|tool_call_start|>[fn(a=1, b=2)]<|tool_call_end|> —
    Python-call syntax, one or more calls in a bracketed list."""
    calls: list[dict] = []
    for match in LFM_TOOL_BLOCK.finditer(text or ""):
        raw = match.group(1).strip()
        try:
            expr = ast.parse(raw, mode="eval").body
            nodes = expr.elts if isinstance(expr, ast.List) else [expr]
            for node in nodes:
                if not isinstance(node, ast.Call):
                    continue
                if isinstance(node.func, ast.Name):
                    name = node.func.id
                elif isinstance(node.func, ast.Attribute):
                    name = node.func.attr
                else:
                    continue
                args: dict[str, object] = {}
                for index, arg in enumerate(node.args):
                    args[f"arg{index}"] = ast.literal_eval(arg)
                for keyword in node.keywords:
                    if keyword.arg is not None:
                        args[keyword.arg] = ast.literal_eval(keyword.value)
                calls.append({
                    "id": f"call_{uuid.uuid4().hex[:16]}",
                    "type": "function",
                    "function": {"name": name, "arguments": json.dumps(args, ensure_ascii=False)},
                })
        except (SyntaxError, ValueError, TypeError):
            continue
    return calls


def _parse_hermes_style_tool_calls(text: str) -> list[dict]:
    """Hermes/Qwen-style format: <tool_call>{"name": "fn", "arguments":
    {...}}</tool_call> — one JSON object per block, not Python-call syntax."""
    calls: list[dict] = []
    for match in HERMES_TOOL_BLOCK.finditer(text or ""):
        raw = match.group(1).strip()
        try:
            obj = json.loads(raw)
            name = obj.get("name")
            if not name:
                continue
            args = obj.get("arguments", {})
            if isinstance(args, str):
                # some variants double-encode arguments as a JSON string
                try:
                    args = json.loads(args)
                except json.JSONDecodeError:
                    pass
            calls.append({
                "id": f"call_{uuid.uuid4().hex[:16]}",
                "type": "function",
                "function": {"name": name, "arguments": json.dumps(args, ensure_ascii=False)},
            })
        except (json.JSONDecodeError, TypeError):
            continue
    return calls


PARSERS = {
    "lfm": (_parse_lfm_tool_calls, LFM_SPLIT_MARKER),
    "hermes_style": (_parse_hermes_style_tool_calls, HERMES_SPLIT_MARKER),
    "qwen3_coder": (_parse_qwen3_coder_tool_calls, QWEN3_CODER_SPLIT_MARKER),
    "poolside_v1": (_parse_poolside_v1_tool_calls, POOLSIDE_V1_SPLIT_MARKER),
}

if TOOL_CALL_PARSER not in PARSERS:
    raise SystemExit(
        f"Unknown BENCH_TOOL_PARSER={TOOL_CALL_PARSER!r}. "
        f"Known parsers: {sorted(PARSERS)}. Add a new one in bench_local_proxy.py "
        f"(research the model's real tool-call format from its model card first)."
    )
_active_parser, _active_split_marker = PARSERS[TOOL_CALL_PARSER]


def _filter_tools(tools: list) -> list:
    # No filtering — the benchmark always wants the full tools array it was
    # given to reach the model unmodified. Kept as a pass-through function
    # (rather than removing the call site) so this file stays a close diff
    # against the original, in case that one changes and this needs re-sync.
    return tools


def _queue_capacity() -> int:
    """Return a conservative queue size without making startup fragile."""
    try:
        return max(1, int(os.environ.get("MARA_PROXY_MAX_QUEUE", "8")))
    except ValueError:
        return 8


@dataclass
class QueuedRequest:
    """One request admitted to the local generation worker."""

    work: Callable[[], tuple[int, dict, bytes]]
    done: threading.Event = field(default_factory=threading.Event)
    result: tuple[int, dict, bytes] | None = None
    started: bool = False


class QueueUnavailableError(RuntimeError):
    """Raised only while the local queue is shutting down."""


class GenerationQueue:
    """A bounded FIFO queue with one worker for the serialized MLX backend.

    ``capacity`` bounds waiting requests, not the single request currently in
    progress.  A cancelled queued request is removed immediately, freeing its
    slot; an already-started upstream HTTP request is deliberately allowed to
    finish because urllib has no safe cancellation API.
    """

    def __init__(self, capacity: int) -> None:
        self.capacity = capacity
        self._pending: deque[QueuedRequest] = deque()
        self._condition = threading.Condition()
        self._worker: threading.Thread | None = None
        self._stopping = False
        self._active = 0
        self._metrics = {
            "accepted_total": 0,
            "started_total": 0,
            "completed_total": 0,
            "cancelled_total": 0,
            "rejected_full_total": 0,
            "upstream_exception_total": 0,
        }

    def start(self) -> None:
        with self._condition:
            if self._worker is not None:
                return
            self._worker = threading.Thread(
                target=self._run, name="mara-generation-queue", daemon=True
            )
            self._worker.start()

    def submit(self, work: Callable[[], tuple[int, dict, bytes]]) -> QueuedRequest | None:
        """Admit work in FIFO order, or return None if the waiting queue is full."""
        self.start()
        ticket = QueuedRequest(work=work)
        with self._condition:
            if self._stopping:
                raise QueueUnavailableError("local generation queue is stopping")
            if len(self._pending) >= self.capacity:
                self._metrics["rejected_full_total"] += 1
                self._log_locked("full")
                return None
            self._pending.append(ticket)
            self._metrics["accepted_total"] += 1
            self._log_locked("accepted")
            self._condition.notify()
        return ticket

    def cancel(self, ticket: QueuedRequest) -> bool:
        """Cancel a request that is still waiting; never interrupt active MLX work."""
        with self._condition:
            if ticket.started or ticket.done.is_set():
                return False
            try:
                self._pending.remove(ticket)
            except ValueError:
                return False
            self._metrics["cancelled_total"] += 1
            ticket.done.set()
            self._log_locked("cancelled")
            return True

    def snapshot(self) -> dict[str, int]:
        """Safe, fixed-name queue metrics suitable for local observability."""
        with self._condition:
            return {
                "capacity": self.capacity,
                "queued": len(self._pending),
                "active": self._active,
                **self._metrics,
            }

    def shutdown(self, timeout: float = 1.0) -> None:
        """Test/support helper; production uses the daemon worker for process life."""
        with self._condition:
            self._stopping = True
            self._condition.notify_all()
            worker = self._worker
        if worker is not None:
            worker.join(timeout)

    def _log_locked(self, event: str) -> None:
        # Event names and labels are fixed; never include URL, headers, or body.
        LOG.info(
            "proxy_queue event=%s queue_depth=%d active_requests=%d",
            event,
            len(self._pending),
            self._active,
        )

    def _run(self) -> None:
        while True:
            with self._condition:
                while not self._pending and not self._stopping:
                    self._condition.wait()
                if self._stopping and not self._pending:
                    return
                ticket = self._pending.popleft()
                ticket.started = True
                self._active = 1
                self._metrics["started_total"] += 1
                self._log_locked("started")
            try:
                ticket.result = ticket.work()
            except Exception:
                # Do not expose/log exception strings: they can contain request data.
                ticket.result = (
                    502,
                    {"Content-Type": "application/json"},
                    b'{"error":{"message":"local upstream request failed","type":"upstream_error"}}',
                )
                with self._condition:
                    self._metrics["upstream_exception_total"] += 1
            finally:
                with self._condition:
                    self._active = 0
                    self._metrics["completed_total"] += 1
                    ticket.done.set()
                    self._log_locked("completed")


GENERATION_QUEUE = GenerationQueue(_queue_capacity())


def normalize_response(data: dict) -> dict:
    for choice in data.get("choices", []):
        message = choice.get("message") or {}
        if message.get("tool_calls"):
            continue
        content = message.get("content") or ""
        # llama-server's chat-template-driven reasoning extraction sometimes
        # misclassifies an ENTIRE response (tool-call XML included) as
        # reasoning_content, leaving content empty — confirmed live
        # 2026-08-20 for poolside/Laguna-XS-2.1 (no <think>-style tags in
        # its output at all, just a template quirk). Fall back to
        # reasoning_content as the effective text whenever content is empty,
        # since downstream grading only ever reads `content`.
        source_field = "content"
        if not content and message.get("reasoning_content"):
            content = message["reasoning_content"]
            source_field = "reasoning_content"
        calls = _active_parser(content)
        if calls:
            before = content.split(_active_split_marker, 1)[0]
            before = THINK_BLOCK.sub("", before)
            before = STRAY_TOOL_CALL_TAG.sub("", before).strip() or None
            message["content"] = before
            message["tool_calls"] = calls
            choice["finish_reason"] = "tool_calls"
        elif source_field == "reasoning_content":
            message["content"] = THINK_BLOCK.sub("", content).strip()
        elif isinstance(content, str):
            message["content"] = THINK_BLOCK.sub("", content).strip()
        choice["message"] = message
    return data


def upstream(method: str, path: str, body: bytes | None = None) -> tuple[int, dict, bytes]:
    headers = {"Content-Type": "application/json"}
    request = Request(UPSTREAM + path, data=body, headers=headers, method=method)
    try:
        with urlopen(request, timeout=300) as response:
            raw = response.read()
            return response.status, dict(response.headers), raw
    except HTTPError as error:
        return error.code, dict(error.headers), error.read()
    except URLError:
        # Avoid passing exception text through logs or responses.
        return 502, {"Content-Type": "application/json"}, b'{"error":"local upstream unavailable"}'


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, _format: str, *_args: object) -> None:
        return

    def _send_payload(
        self,
        status: int,
        content_type: str,
        payload: bytes,
        extra_headers: dict[str, str] | None = None,
    ) -> bool:
        """Send one response, quietly tolerating a disconnected client."""
        try:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(payload)))
            if extra_headers:
                for name, value in extra_headers.items():
                    self.send_header(name, value)
            self.end_headers()
            self.wfile.write(payload)
            return True
        except (BrokenPipeError, ConnectionResetError, OSError):
            return False

    def _send_json(self, status: int, data: dict, extra_headers: dict[str, str] | None = None) -> bool:
        return self._send_payload(
            status,
            "application/json",
            json.dumps(data, ensure_ascii=False).encode(),
            extra_headers,
        )

    def _client_disconnected(self) -> bool:
        """Best-effort EOF detection while this handler is waiting in the queue."""
        try:
            readable, _, _ = select.select([self.connection], [], [], 0)
            if not readable:
                return False
            return self.connection.recv(1, socket.MSG_PEEK) == b""
        except (BlockingIOError, OSError, ValueError):
            return False

    def do_GET(self) -> None:
        path = urlsplit(self.path).path
        if path == "/metrics":
            self._send_json(200, {"generation_queue": GENERATION_QUEUE.snapshot()})
            return
        if path == "/healthz":
            # tool_call_parser/upstream added 2026-08-21 (adversarial review
            # finding H2): a stale proxy left bound to an old port answers
            # /healthz just fine, but may be pointed at the WRONG upstream
            # model or configured with the WRONG parser for whatever config
            # is actually being tested right now — health alone can't catch
            # that. A caller should assert both match what it expects before
            # trusting this process.
            self._send_json(200, {
                "status": "ok",
                "generation_queue": GENERATION_QUEUE.snapshot(),
                "tool_call_parser": TOOL_CALL_PARSER,
                "upstream": UPSTREAM,
            })
            return
        status, headers, raw = upstream("GET", self.path)
        self._send_payload(status, headers.get("Content-Type", "application/json"), raw)

    def do_POST(self) -> None:
        try:
            length = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(length)
            request = json.loads(body)
        except (ValueError, json.JSONDecodeError):
            self._send_json(400, {"error": "invalid JSON"})
            return

        if "tools" in request:
            request["tools"] = _filter_tools(request["tools"])

        requested_stream = bool(request.get("stream"))
        request["stream"] = False
        upstream_body = json.dumps(request, ensure_ascii=False).encode()
        try:
            ticket = GENERATION_QUEUE.submit(
                lambda: upstream("POST", self.path, upstream_body)
            )
        except QueueUnavailableError:
            self._send_json(
                503,
                {"error": {"message": "local generation queue is unavailable", "type": "queue_unavailable"}},
            )
            return
        if ticket is None:
            self._send_json(
                429,
                {
                    "error": {
                        "message": "local generation queue is full; retry later",
                        "type": "queue_full",
                        "code": "local_queue_full",
                    }
                },
                {"Retry-After": "1"},
            )
            return

        while not ticket.done.wait(0.25):
            if self._client_disconnected():
                GENERATION_QUEUE.cancel(ticket)
                return
        if ticket.result is None:
            # Only possible for a queued request cancelled after the client left.
            return
        status, _headers, raw = ticket.result
        if status >= 400:
            self._send_payload(status, "application/json", raw)
            return
        try:
            data = normalize_response(json.loads(raw))
        except (json.JSONDecodeError, TypeError):
            self._send_json(502, {"error": "upstream returned invalid JSON"})
            return
        if not requested_stream:
            self._send_json(status, data)
            return
        self._send_stream(data)

    def _send_stream(self, data: dict) -> None:
        choice = (data.get("choices") or [{}])[0]
        message = choice.get("message") or {}
        delta: dict[str, object] = {"role": "assistant"}
        if message.get("content") is not None:
            delta["content"] = message["content"]
        if message.get("tool_calls"):
            delta["tool_calls"] = [
                {"index": i, **call} for i, call in enumerate(message["tool_calls"])
            ]
        chunk_base = {
            "id": data.get("id", f"chatcmpl-{uuid.uuid4().hex[:12]}"),
            "object": "chat.completion.chunk",
            "created": data.get("created", int(time.time())),
            "model": data.get("model", "LiquidAI/LFM2.5-2.6B-MLX-bf16"),
        }
        chunks = [
            {**chunk_base, "choices": [{"index": 0, "delta": delta, "finish_reason": None}]},
            {**chunk_base, "choices": [{"index": 0, "delta": {}, "finish_reason": choice.get("finish_reason", "stop")}]},
        ]
        payload = b"".join(
            b"data: " + json.dumps(chunk, ensure_ascii=False).encode() + b"\n\n"
            for chunk in chunks
        ) + b"data: [DONE]\n\n"
        self._send_payload(
            200,
            "text/event-stream",
            payload,
            {"Cache-Control": "no-cache", "Connection": "close"},
        )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    LOG.info("bench_local_proxy starting: upstream=%s listen=%s:%d tool_call_parser=%s", UPSTREAM, *LISTEN, TOOL_CALL_PARSER)
    GENERATION_QUEUE.start()
    ThreadingHTTPServer(LISTEN, Handler).serve_forever()
