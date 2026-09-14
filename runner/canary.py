#!/usr/bin/env python3
"""Deterministic quantisation canary for the local-model-bench harness.

A small, bounded CLI that replays a FIXED suite of prompts against one or more
ALREADY-RUNNING OpenAI-compatible endpoints and records, per task per trial:
outcome / pass-fail / error, response-text hash, canonical tool-call hash,
usage, elapsed time, and endpoint/model identity. Its purpose is to compare
quantisations of the same model family (e.g. the Qwen3.6 variants) on a small,
stable, cheap surface: greedy (temperature=0), explicit max_tokens, identical
request bytes per trial, so any difference between repeated trials or between
two endpoints serving the same model is itself the measured signal.

Deliberately does NOT launch, reconfigure, or stop any server, and never
appends to results/log.jsonl. Output lands in a caller-specified (or
timestamped default) JSONL artifact under artifacts/ — see "Artifact format".

Suite (fixed order; task TEXT is loaded verbatim from tasks/*.yaml so the
canary never drifts from the real benchmark's semantics):

  1. sanity-basic                — reasoning/arithmetic (regex ^42$ grader,
                                   verbatim from tasks/sanity.yaml)
  2. hermes_ops-chaining         — tool sequencing (chained_tool_calls
                                   web_search -> write_file, full 41-tool
                                   manifest + 26K system prompt from
                                   fixtures/hermes_ops/, verbatim)
  3. hermes_ops-noisy-result     — noisy-result handling (search_files mock
                                   with decoys; session.ts, verbatim)
  4. kiem_mini-feature           — KNOWN QWEN3.6 FAILURE PROMPT #1 (the two
                                   OptiQ evidence legs failed feature +
                                   testwrite; see artifacts/optiq-*-20260914.md).
                                   Real prompt text; canary-response-only check
                                   (no fixture, so no cargo gate — documented).
  5. kiem_mini-testwrite         — KNOWN QWEN3.6 FAILURE PROMPT #2 (the only
                                   failure in the full OptiQ coding run,
                                   a302b78). Real prompt text; canary-
                                   response-only check (no fixture — the real
                                   mutation gate needs checks/kiem_mini/...).
  6. canary-multi-turn           — multi-turn continuation: fixed two-user-turn
                                   history (system marker prefix, turn 1, a
                                   SCRIPTED assistant reply, turn 2 — the
                                   scripted reply plays the role the harness's
                                   mocked tool results do, keeping the request
                                   bytes stable across trials). Mirrors
                                   probe_mei.py's growing-transcript cache
                                   pattern (same "reply cache-reuse-ok" turn-2
                                   phrasing).

Known-limitation note on tasks 4-5: a fixture-less canary cannot run the real
graders (cargo/swift test, mutation kills). Their checks here are explicit
response-sanity checks (non-empty, task identifiers present) and are recorded
as such (`grading: canary_response_only` in the task row) — a PASS means the
model produced a substantive on-topic response, NOT that it passes the real
benchmark gate for that task.

Logprobs are an OPTIONAL observable: pass --logprobs [N] to add
`logprobs: true, top_logprobs: N` to every request. If the backend returns
token-level logprobs, the record carries top-token data and per-position
top-1/top-2 margins for positions with numeric data. Both wire shapes of
top_logprobs are handled: OpenAI-style LIST-shaped
(`[{"token": "42", "logprob": -0.1, "bytes": [...]}, ...]`) and dict-shaped
(`{"42": -0.1}` or its `{"token": {"logprob": f}}` variant). If the backend
returns nothing usable (missing field, null, or non-numeric values), the
record carries an explicit `unsupported`/`unavailable` status with a reason —
margins are NEVER fabricated, coerced, or defaulted.

Reasoning is recorded, never graded: when a backend exposes thinking text
(message `reasoning_content` / `reasoning`), the last (graded) exchange's
reasoning is stored SEPARATELY as `reasoning_content` plus its own
`reasoning_content_sha256`, so thinking-mode runs are auditable and can be
diffed across quantisations WITHOUT changing what grade_prompt sees (final_text
stays the visible answer only). Same policy as logprobs: the last exchange's
reasoning only; intermediate tool-call turns are not the graded observable.

Timeout semantics: --timeout is a socket read/inactivity timeout (urllib's
own semantics), NOT a hard total per-request deadline — the canary makes no
total-deadline claim it does not implement. It defaults to 1800s to match the
pinned llama-server's 30-minute request cap, so a long thinking-mode exchange
with the 26K hermes_ops system prompt is not cut off client-side while the
server would still have accepted it.

Tool tasks replay run_prompt.py's agent loop (--max-turns, default 6 —
deliberately run_prompt.py's CLI default, NOT hermes_ops's 40; see
DEFAULT_CANARY_MAX_TURNS): the task's own mock_tool_responses /
force_tool_error from tasks/*.yaml script every tool result, and the loop
continues until the model stops calling tools. That is what makes the real
chained_tool_calls / tool_call_then_response graders meaningful — a
single-exchange canary could never exercise a dependent tool chain. Tasks
without a mock table (the fixture-derived prompts, the multi-turn
continuation) are a single exchange; a tool call there is undeclared by
definition and graded accordingly.

Failures (HTTP error, malformed JSON body, connection refused, mid-request
disconnect, timeout, or an UNVERIFIED endpoint identity) are recorded per
task-trial as explicit `error` rows with an error_kind, and the run keeps
going so the remaining surface is still measured. Endpoint identity is
verified (GET /v1/models) BEFORE any request: if the endpoint's served model
ids cannot be fetched, or the requested model is not among them, every
task/trial for that endpoint becomes an explicit `error_kind: "identity"`
row with stable prompt hashes and NO model request is sent — an unverified
request would defeat the canary's whole purpose. The artifact is written
append-only to a temp file and atomically
renamed into place on completion — a crash mid-run still leaves the partial
artifact (as .tmp.<pid>) intact and valid JSONL.

No network by default: the CLI offers three offline modes
(--list-tasks / --show-suite / --hash-suite) that only read the repo, and a
run REQUIRES at least one --endpoint (plus --model for bare URLs).

Usage:
  uv run --locked python runner/canary.py --list-tasks
  uv run --locked python runner/canary.py --hash-suite
  uv run --locked python runner/canary.py \
      --endpoint http://127.0.0.1:8024/v1 --model mlx-community/Qwen3.6-35B-A3B-OptiQ-4bit \
      --trials 3 --max-tokens 8192 --output artifacts/canary-qwen36-optiq.jsonl
  uv run --locked python runner/canary.py \
      --endpoint mlx-community/Qwen3.6-35B-A3B-4bit@http://127.0.0.1:8024/v1 \
      --endpoint EigenLabs/Qwen3.6-35B-A3B-MLX-mixed-4bit@http://127.0.0.1:8025/v1 \
      --trials 5 --logprobs 5 --output artifacts/canary-qwen36-compare.jsonl

Artifact format (JSONL):
  {"kind": "run",  "canary_version": ..., "runner_git_sha": ..., "endpoints": [...],
   "trials": N, "max_tokens": N, "temperature": 0,
   "logprobs": int|"not_requested", "max_turns": N, ...}
  {"kind": "trial", "task_id": ..., "endpoint": {"base_url": ..., "model": ..., "served_ids": [...]},
   "trial": N, "prompt_sha256": ..., "outcome": "passed"|"failed"|"error",
   "passed": bool|null, "error": str|null, "error_kind": str|null,
   "grading": "full"|"canary_response_only",
   "final_text": ..., "final_text_sha256": ...,
   "reasoning_content": ...|null, "reasoning_content_sha256": ...|null,
   "tool_calls": [...], "tool_calls_sha256": ...,
   "finish_reason": ..., "usage": {...}, "elapsed_seconds": ...,
   "logprobs": {...}|null, "check_reason": ...}
  {"kind": "summary", "tasks_total": N, "passed": N, "failed": N, "errors": N,
   "determinism": {...per endpoint/task...}, "completed": bool, "error": ...}
"""
from __future__ import annotations

import argparse
import hashlib
import http.client
import json
import math
import os
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

import yaml

import bench_common
import grade_prompt

CANARY_VERSION = "0.1.0"
REPO = bench_common.REPO
SHA256_EMPTY = hashlib.sha256(b"").hexdigest()

# The two currently known Qwen3.6 failure-task prompts (committed evidence:
# ac72c83 OptiQ kiem_mini leg 3/5 with feature + testwrite failing, then
# a302b78 full OptiQ coding run where testwrite remained the only failure).
# Task ids are loaded from the real suite files so the canary cannot drift.
QWEN36_FAILURE_TASK_IDS = ("kiem_mini-feature", "kiem_mini-testwrite")

# (suite file stem, task id) in fixed canary order.
SUITE_ORDER: list[tuple[str, str]] = [
    ("sanity", "sanity-basic"),
    ("hermes_ops", "hermes_ops-chaining"),
    ("hermes_ops", "hermes_ops-noisy-result"),
    ("kiem_mini", "kiem_mini-feature"),
    ("kiem_mini", "kiem_mini-testwrite"),
    ("canary", "canary-multi-turn"),
]

DEFAULT_TOP_LOGPROBS = 5
# The repo's established safe defensive completion cap (see every config's
# "RUNAWAY BOUND: --max-tokens 32768 -> 8192" convention: 8192 cannot truncate
# legitimate work, p99 is 2933 tokens). The previous 512 was far too low for
# thinking-mode Qwen3.6, whose reasoning trace alone exceeds it, and turned
# normal answers into truncation noise.
DEFAULT_MAX_TOKENS = 8192
# urllib's timeout is a socket READ/INACTIVITY timeout, NOT a hard total
# per-request deadline (a true total deadline would need its own wall-clock
# timer and is deliberately NOT implemented — see request_json). 1800s matches
# the pinned llama-server's own 30-minute request cap: a thinking-mode exchange
# carrying the 26K hermes_ops system prompt must never be killed client-side
# while the server would still have accepted the request.
DEFAULT_TIMEOUT = 1800.0

# Response-sanity checks for the two fixture tasks (see module docstring).
_FIXTURE_TASK_CANARY_CHECKS: dict[str, dict[str, Any]] = {
    "kiem_mini-feature": {
        "type": "contains_any",
        "phrases": ["filter_by_tag", "filter by tag", "--tag"],
    },
    "kiem_mini-testwrite": {
        "type": "contains_any",
        "phrases": ["pin_behavior.rs", "pin_behavior", "ordered_pinned_first"],
    },
}

# Synthetic multi-turn continuation task. The assistant turn is SCRIPTED (not
# the model's own turn-1 output) so the request bytes — and therefore the
# prompt hash — are identical across trials, exactly like the harness's mocked
# tool results. Semantics mirror probe_mei.py's growing-transcript pattern:
# identical system prefix, a short first exchange, then a second user
# instruction the model must actually follow.
MULTI_TURN_TASK: dict[str, Any] = {
    "id": "canary-multi-turn",
    "title": "Multi-turn continuation across a scripted assistant turn",
    "type": "continuation",
    "system_prompt": "system stability marker " * 256,
    "messages": [
        {"role": "user", "content": "First instruction: answer nothing yet."},
        {"role": "assistant", "content": "Acknowledged.", "scripted": True},
        {"role": "user", "content": "Second instruction: reply cache-reuse-ok."},
    ],
    "check": {"type": "contains", "text": "cache-reuse-ok"},
}


class CanaryError(Exception):
    """A canary-level error (missing suite file, bad endpoint spec, ...)."""


class RequestError(Exception):
    """A transport failure with an explicit kind: http|connect|timeout|

    malformed_response|server_disconnect|api_error.
    """

    def __init__(self, kind: str, message: str):
        self.kind = kind
        super().__init__(message)


# ---------------------------------------------------------------------------
# Deterministic hashing / canonicalisation
# ---------------------------------------------------------------------------

def canonical_json(value: Any) -> str:
    """Stable byte serialization: sorted keys, compact separators."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_hex(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def canonical_tool_calls(tool_calls: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Canonical, hash-stable representation of a model's tool calls.

    Ordering is by (index, id) so streaming accumulation and any reordering of
    the same calls produce the SAME canonical form; arguments are re-serialized
    with sorted keys and compact separators so key order / whitespace cannot
    change the digest. Accepts arguments as a raw JSON STRING (as delivered on
    the wire, or accumulated from a stream) or as an already-parsed dict (as
    run_task_once normalizes them). Malformed (unparseable) JSON arguments are
    kept verbatim and flagged, never silently 'repaired'. NOTE: numeric
    literals are NOT normalized (15 vs 15.0 stay distinct) — the canonical hash
    is a difference detector, and 15 vs 15.0 IS a difference.
    """
    out: list[dict[str, Any]] = []
    for tc in sorted(tool_calls, key=lambda c: (c.get("index", 0), str(c.get("id") or ""))):
        fn = tc.get("function") or {}
        args_raw = fn.get("arguments")
        malformed = False
        if isinstance(args_raw, str):
            stripped = args_raw.strip()
            try:
                args_canon = canonical_json(json.loads(stripped))
            except (json.JSONDecodeError, TypeError):
                args_canon = stripped
                malformed = True
        elif isinstance(args_raw, dict):
            args_canon = canonical_json(args_raw)
        else:
            args_canon = canonical_json({})
        out.append({
            "name": fn.get("name") or "",
            "arguments_canon": args_canon,
            "malformed_arguments": malformed,
        })
    return out


def tool_calls_sha256(tool_calls: list[dict[str, Any]]) -> str:
    canonical = canonical_tool_calls(tool_calls)
    if not canonical:
        return SHA256_EMPTY
    return sha256_hex(canonical_json(canonical))


def _to_text(content: Any) -> str:
    """Normalise ANY message content value to a string, never dropping data.

    OpenAI-compatible backends may deliver `content` as a list of content
    parts ([{"type": "text", "text": ...}, ...]) or, in exotic cases, as a
    dict. The canary's graded observable and every hash are ALWAYS strings:
    text parts are joined verbatim, non-text parts are serialized canonically
    (so the digest still changes when they change), None/empty become "".
    """
    if isinstance(content, str):
        return content
    if content is None:
        return ""
    if isinstance(content, list):
        parts: list[str] = []
        for part in content:
            if isinstance(part, str):
                parts.append(part)
            elif isinstance(part, dict) and isinstance(part.get("text"), str):
                parts.append(part["text"])
            else:
                parts.append(canonical_json(part))
        return "".join(parts)
    return canonical_json(content)


# ---------------------------------------------------------------------------
# Request building / prompt hash
# ---------------------------------------------------------------------------

def build_request(
    task: dict[str, Any],
    model: str,
    max_tokens: int,
    logprobs: bool = False,
    top_logprobs: int | None = None,
) -> dict[str, Any]:
    """Build the exact request body (temperature always 0, max_tokens always
    explicit, tools only when the task declares them; logprobs keys ONLY when
    requested)."""
    messages: list[dict[str, Any]] = []
    if task.get("system_prompt"):
        messages.append({"role": "system", "content": task["system_prompt"]})
    if task.get("messages"):  # multi-turn task: full pre-built history
        for message in task["messages"]:
            # Internal-only keys (e.g. the "scripted" marker on the fixed
            # assistant turn) never reach the wire: drop them, keep role/content.
            messages.append({k: v for k, v in message.items() if k != "scripted"})
    else:
        messages.append({"role": "user", "content": task["user_prompt"]})

    body: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": 0,  # deterministic canary: greedy, always
        "max_tokens": max_tokens,  # explicit, always
        "stream": False,
    }
    if task.get("tools"):
        body["tools"] = task["tools"]
    if logprobs:
        body["logprobs"] = True
        if top_logprobs:
            body["top_logprobs"] = top_logprobs
    return body


def prompt_sha256(request: dict[str, Any]) -> str:
    """Stable hash over the canonical request bytes (model, messages, tools,
    sampling, caps, logprobs) — identical request => identical hash."""
    return sha256_hex(canonical_json(request))


# ---------------------------------------------------------------------------
# Logprobs extraction
# ---------------------------------------------------------------------------

def _iter_top_candidates(top: Any):
    """Yield (token, candidate) from top_logprobs in EITHER wire shape:

    - OpenAI-style list-shaped: [{"token": "42", "logprob": -0.1, "bytes": [...]}, ...]
    - dict-shaped: {"42": -0.1} or its {"42": {"logprob": -0.1, ...}} variant
      (llama.cpp / older OpenAI responses)
    """
    if isinstance(top, list):
        for entry in top:
            if not isinstance(entry, dict):
                continue
            yield entry.get("token"), entry
    elif isinstance(top, dict):
        for token, candidate in top.items():
            yield token, candidate


def extract_logprobs(choice: dict[str, Any]) -> dict[str, Any]:
    """Extract top-token data + adjacent top-1/top-2 margins from a response
    choice. Handles BOTH top_logprobs wire shapes (list-shaped and
    dict-shaped — see _iter_top_candidates). Never fabricates: missing/null
    fields yield status 'unsupported'/'unavailable' with a reason; non-numeric
    values are counted and skipped, never coerced into a margin."""
    lp = choice.get("logprobs") if isinstance(choice, dict) else None
    if lp is None:
        return {"status": "unsupported", "reason": "choices[0].logprobs is absent or null"}
    content = lp.get("content")
    if content is None:
        return {"status": "unsupported", "reason": "logprobs.content is absent or null"}
    if not isinstance(content, list):
        return {
            "status": "unsupported",
            "reason": f"logprobs.content is {type(content).__name__}, expected a list",
        }

    positions: list[dict[str, Any]] = []
    margin_values: list[float] = []
    non_numeric = 0
    no_top_data = 0
    for entry in content:
        if not isinstance(entry, dict):
            continue
        top = entry.get("top_logprobs")
        top_entries = list(_iter_top_candidates(top))
        if not top_entries:
            no_top_data += 1
            continue
        numeric: list[float] = []
        for _token, candidate in top_entries:
            value = candidate.get("logprob") if isinstance(candidate, dict) else candidate
            if value is None:
                non_numeric += 1
                continue
            try:
                numeric_value = float(value)
            except (TypeError, ValueError):
                non_numeric += 1
                continue
            if not math.isfinite(numeric_value):
                # float("NaN")/float("inf") parse fine but carry no usable
                # probability — count them, never turn them into a margin.
                non_numeric += 1
                continue
            numeric.append(numeric_value)
        if not numeric:
            continue
        ranking = sorted(numeric, reverse=True)
        margin = ranking[0] - ranking[1] if len(ranking) >= 2 else None
        positions.append({
            "token": entry.get("token"),
            "top1_logprob": ranking[0],
            "top2_logprob": ranking[1] if len(ranking) >= 2 else None,
            "margin_top1_minus_top2": margin,
        })
        if margin is not None:
            margin_values.append(margin)

    if not positions:
        reason = "no usable top_logprobs numbers in logprob content"
        if no_top_data:
            reason = f"{reason} ({no_top_data} entries with no top_logprobs data)"
        return {
            "status": "unavailable",
            "reason": reason,
            "positions": 0,
            "entries_without_top_data": no_top_data,
            "non_numeric_top_values": non_numeric,
            "margins": None,
        }

    record: dict[str, Any] = {
        "status": "present",
        "positions": len(positions),
        "entries_without_top_data": no_top_data,
        "non_numeric_top_values": non_numeric,
        "top_token_sample": positions[:3] + (positions[-3:] if len(positions) > 6 else []),
    }
    if margin_values:
        record["margins"] = {
            "count": len(margin_values),
            "mean": round(sum(margin_values) / len(margin_values), 6),
            "min": round(min(margin_values), 6),
            "max": round(max(margin_values), 6),
        }
    else:
        record["margins"] = None
    return record


# ---------------------------------------------------------------------------
# Transport
# ---------------------------------------------------------------------------

def request_json(url: str, payload: dict[str, Any], timeout: float) -> tuple[dict[str, Any], float]:
    """POST *payload* to *url*, returning (parsed dict, elapsed seconds).

    *timeout* is urllib's socket READ/INACTIVITY timeout — the maximum a
    single socket read may stall with no bytes. It is NOT a hard total
    per-request deadline (a server that trickles bytes can exceed it
    wall-clock; a true total deadline is deliberately not implemented and is
    never claimed).

    Every failure mode is raised as RequestError with an explicit kind so the
    record can say what actually happened: http error payload, malformed body,
    connect refusal, timeout, or a mid-request disconnect.
    """
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    started = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            raw = response.read()
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")[:500]
        raise RequestError("http", f"HTTP {exc.code}: {body}") from exc
    except urllib.error.URLError as exc:
        reason = getattr(exc, "reason", exc)
        raise RequestError("connect", f"connection failed: {reason}") from exc
    except TimeoutError as exc:
        raise RequestError("timeout", f"request timed out after {timeout:.0f}s") from exc
    except (OSError, http.client.HTTPException) as exc:
        # RemoteDisconnected / IncompleteRead / BadStatusLine mid-request, or a
        # socket-level failure — an explicit server-disconnect row, never a
        # silent generic failure. TimeoutError is an OSError subclass but is
        # caught by the explicit clause above first.
        raise RequestError("server_disconnect", f"{type(exc).__name__}: {exc}") from exc

    elapsed = time.monotonic() - started
    try:
        parsed = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        snippet = raw[:200].decode("utf-8", errors="replace")
        raise RequestError(
            "malformed_response",
            f"response body is not valid JSON: {exc}: {snippet!r}",
        ) from exc
    if not isinstance(parsed, dict):
        raise RequestError(
            "malformed_response",
            f"response is {type(parsed).__name__}, expected an object",
        )
    if parsed.get("error"):
        raise RequestError("api_error", f"error payload in response: {canonical_json(parsed['error'])}")
    return parsed, elapsed


def fetch_served_ids(base_url: str, timeout: float = 30.0) -> list[str]:
    """GET /v1/models for endpoint identity; failure is explicit."""
    try:
        with urllib.request.urlopen(
            urllib.request.Request(f"{base_url.rstrip('/')}/models"), timeout=timeout
        ) as response:
            body = json.loads(response.read())
        return [entry.get("id") for entry in (body.get("data") or [])]
    except urllib.error.HTTPError as exc:
        raise RequestError("http", f"GET /models HTTP {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise RequestError("connect", f"GET /models failed: {getattr(exc, 'reason', exc)}") from exc
    except TimeoutError as exc:
        raise RequestError("timeout", "GET /models timed out") from exc
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise RequestError("malformed_response", f"GET /models: {type(exc).__name__}: {exc}") from exc


# ---------------------------------------------------------------------------
# Suite loading
# ---------------------------------------------------------------------------

@dataclass
class LoadedTask:
    id: str
    title: str
    task: dict[str, Any]  # resolved prompt_spec + check
    grading: str  # "full" (real check from tasks/*.yaml) | "canary_response_only"


def _load_yaml_task(suite_stem: str, task_id: str) -> dict[str, Any]:
    path = REPO / "tasks" / f"{suite_stem}.yaml"
    if not path.exists():
        raise CanaryError(f"suite file {path} not found")
    suite = yaml.safe_load(path.read_text()) or {}
    for task in suite.get("tasks", []):
        if task.get("id") == task_id:
            return task
    raise CanaryError(f"task {task_id!r} not found in {path}")


def resolve_prompt_spec(task: dict[str, Any]) -> dict[str, Any]:
    """Resolve a prompt-based task's prompt_spec the same way
    run_prompt_suite.py does: system_prompt_file / tools_file are relative to
    the repo root and read here, so the canary sends byte-identical prompts."""
    spec = dict(task.get("prompt_spec", {}))
    if "system_prompt_file" in spec:
        spec["system_prompt"] = (REPO / spec.pop("system_prompt_file")).read_text()
    if "tools_file" in spec:
        spec["tools"] = json.loads((REPO / spec.pop("tools_file")).read_text())
    return spec


def load_suite() -> list[LoadedTask]:
    """Build the canary suite in SUITE_ORDER. Verbatim task text + checks from
    the real suite files; fixture tasks get response-sanity checks and a
    grading marker; the synthetic multi-turn task is defined above."""
    loaded: list[LoadedTask] = []
    for suite_stem, task_id in SUITE_ORDER:
        if suite_stem == "canary":
            task = dict(MULTI_TURN_TASK)
            loaded.append(LoadedTask(task_id, task["title"], task, "full"))
            continue
        raw = _load_yaml_task(suite_stem, task_id)
        if task_id in QWEN36_FAILURE_TASK_IDS:
            # Fixture task: verbatim prompt text, no fixture available so no
            # cargo/mutation gate. Explicit response-sanity check only.
            spec = {
                "system_prompt": "",
                "user_prompt": raw["prompt"],
                "expected_tools": raw.get("expected_tools", []),
            }
            task = {"id": task_id, **spec, "check": _FIXTURE_TASK_CANARY_CHECKS[task_id], "tools": None}
            loaded.append(LoadedTask(task_id, raw["title"], task, "canary_response_only"))
        else:
            spec = resolve_prompt_spec(raw)
            check = raw.get("check")
            if not check:
                raise CanaryError(f"task {task_id!r} has no check spec")
            task = {"id": task_id, **spec, "check": check}
            loaded.append(LoadedTask(task_id, raw["title"], task, "full"))
    return loaded


# ---------------------------------------------------------------------------
# Repeated-trial comparison
# ---------------------------------------------------------------------------

def trial_consistency(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Given the trial records for ONE task on ONE endpoint, report whether
    every repeat produced byte-identical observable output (same final text
    hash AND same canonical tool-call hash). Records without output (errors)
    are excluded from the comparison but reported."""
    comparable = [
        r for r in records
        if r.get("final_text") is not None or r.get("tool_calls_sha256") not in (None, SHA256_EMPTY)
    ]
    comparable = [r for r in comparable if r.get("outcome") != "error"]
    if not comparable:
        return {"identical": None, "reason": "no comparable (non-error) trials"}
    keys = [
        (r.get("final_text_sha256"), r.get("tool_calls_sha256"))
        for r in comparable
    ]
    first = keys[0]
    differing = [
        r.get("trial") for r, k in zip(comparable, keys) if k != first
    ]
    return {
        "identical": not differing,
        "trials_compared": len(comparable),
        "differing_trials": differing,
    }


# ---------------------------------------------------------------------------
# Atomic artifact writer
# ---------------------------------------------------------------------------

class AtomicJsonlWriter:
    """Append-only JSONL written to a temp file, fsynced per row, atomically
    renamed into place on commit(). If the process dies before commit the
    partial rows are still on disk at the .tmp.<pid> path — never a torn final
    artifact."""

    def __init__(self, final_path: Path):
        self.final = final_path
        self.tmp = final_path.with_name(f"{final_path.name}.tmp.{os.getpid()}")
        self._fh = open(self.tmp, "a", encoding="utf-8")

    def write_row(self, row: dict[str, Any]) -> None:
        self._fh.write(canonical_json(row) + "\n")
        self._fh.flush()
        os.fsync(self._fh.fileno())

    def commit(self) -> None:
        self._fh.close()
        os.replace(self.tmp, self.final)

    def close(self) -> None:
        try:
            self._fh.close()
        except (OSError, ValueError):
            pass


def build_identity_error_record(
    loaded_task: LoadedTask,
    base_url: str,
    model: str,
    served_ids: list[str] | None,
    max_tokens: int,
    trial: int,
    identity_error: str,
    logprobs_requested: bool = False,
    top_logprobs: int | None = None,
) -> dict[str, Any]:
    """One task/trial factored as an explicit `error_kind: "identity"` row.

    Identity is the canary's guard: if the endpoint's served model ids cannot
    be fetched (GET /v1/models failed) or the requested model is not among
    them, NO model request is sent for any task/trial on that endpoint — an
    unverified request byte would defeat the comparison. The prompt hash is
    still computed with the same builder healthy rows use (stable and
    comparable across runs), elapsed is 0, and every identity row counts as an
    error in the summary, which drives the non-zero exit status.
    """
    request = build_request(
        loaded_task.task, model, max_tokens,
        logprobs=logprobs_requested, top_logprobs=top_logprobs,
    )
    return {
        "kind": "trial",
        "task_id": loaded_task.id,
        "task_title": loaded_task.title,
        "grading": loaded_task.grading,
        "endpoint": {"base_url": base_url, "model": model, "served_ids": served_ids},
        "trial": trial,
        "prompt_sha256": prompt_sha256(request),
        "outcome": "error",
        "passed": False,
        "error": identity_error,
        "error_kind": "identity",
        "check_reason": None,
        "turns": None,
        "final_text": None,
        "final_text_sha256": None,
        "reasoning_content": None,
        "reasoning_content_sha256": None,
        "tool_calls": None,
        "tool_calls_sha256": None,
        "finish_reason": None,
        "usage": None,
        "elapsed_seconds": 0.0,
        "logprobs": None,
    }


# ---------------------------------------------------------------------------
# Task execution
# ---------------------------------------------------------------------------

DEFAULT_CANARY_MAX_TURNS = 6
# Deliberately the run_prompt.py CLI default, NOT the hermes_ops yaml's 40:
# the canary is a bounded spot-check and must not turn a 6-task suite into an
# hour of agentic chatter. Documented here so the divergence is visible.


def _grade_result_shape(
    loaded_task: LoadedTask,
    final_text: str,
    tool_calls: list[dict[str, Any]],
    error: str | None,
) -> dict[str, Any]:
    """Shape the run record's fields the way grade_prompt.grade() expects
    (error / hallucinated_tool_calls / final_text / tool_calls), so the REAL
    graders from tasks/*.yaml apply to canary runs unchanged."""
    declared_names = {
        t["function"]["name"] for t in (loaded_task.task.get("tools") or [])
    }
    hallucinated = [c["name"] for c in tool_calls if c["name"] not in declared_names]
    return {
        "error": error,
        "hallucinated_tool_calls": hallucinated,
        "final_text": final_text,
        "tool_calls": tool_calls,
    }


def _parse_tool_args(tool_calls: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Same normalization run_prompt.py applies: arguments string -> parsed
    dict, or {"_raw": ...} when the JSON is malformed."""
    parsed: list[dict[str, Any]] = []
    for tc in tool_calls:
        fn = tc.get("function") or {}
        try:
            args = json.loads(fn.get("arguments") or "{}")
        except json.JSONDecodeError:
            args = {"_raw": fn.get("arguments")}
        parsed.append({"id": tc.get("id"), "name": fn.get("name") or "", "arguments": args})
    return parsed


def _mock_tool_result(name: str, mock_responses: dict[str, str], force_errors: set[str]) -> str:
    """Scripted tool result, mirroring run_prompt.py's wording exactly (the
    fake-error phrasing deliberately never reveals this is a mock — see
    run_prompt.py's comment on that)."""
    if name in force_errors:
        return json.dumps({"error": f"{name}: request failed (connection reset)"})
    if name in mock_responses:
        return mock_responses[name]
    return json.dumps({"error": f"{name}: service temporarily unavailable"})


def _sum_usage(accumulated: dict[str, Any], response_usage: dict[str, Any]) -> dict[str, Any]:
    """Accumulate usage across loop turns the way run_prompt.py does (sum the
    numeric token counts; keep the LAST response's detailed fields)."""
    for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
        value = response_usage.get(key)
        if isinstance(value, (int, float)):
            accumulated[key] = int(accumulated.get(key, 0)) + int(value)
        elif value is None and key not in accumulated:
            accumulated[key] = None
    for key, value in response_usage.items():
        if key not in ("prompt_tokens", "completion_tokens", "total_tokens"):
            accumulated[key] = value
    return accumulated


def run_task_once(
    loaded_task: LoadedTask,
    base_url: str,
    model: str,
    max_tokens: int,
    logprobs_requested: bool,
    top_logprobs: int | None,
    timeout: float,
    http_post: Callable[[str, dict[str, Any], float], tuple[dict[str, Any], float]] = request_json,
    max_turns: int = DEFAULT_CANARY_MAX_TURNS,
) -> dict[str, Any]:
    """Execute ONE task on ONE endpoint and return the full trial record.

    For tasks that declare mock_tool_responses/force_tool_error (the
    hermes_ops/sanity prompt tasks), this replays run_prompt.py's agent loop:
    send the exchange, script each tool call's result from the task's own
    mock table, append it as a tool message, and continue until the model
    stops calling tools or max_turns is hit — so the REAL chained_tool_calls /
    tool_call_then_response graders from tasks/*.yaml apply unchanged. Tasks
    without mocks (the fixture-derived prompts, the multi-turn continuation)
    are a single exchange: a tool call there is by definition undeclared and
    graded accordingly.

    *http_post* is injectable for no-network tests. Logprobs and reasoning
    (thinking) text are recorded for the LAST (graded) exchange only;
    intermediate tool-call turns are not the graded observable. Reasoning goes
    to `reasoning_content`/`reasoning_content_sha256` and NEVER feeds
    final_text or grade_prompt.
    """
    request = build_request(
        loaded_task.task, model, max_tokens,
        logprobs=logprobs_requested, top_logprobs=top_logprobs,
    )
    record: dict[str, Any] = {
        "task_id": loaded_task.id,
        "task_title": loaded_task.title,
        "grading": loaded_task.grading,
        "prompt_sha256": prompt_sha256(request),
        "outcome": None,
        "passed": None,
        "error": None,
        "error_kind": None,
        "check_reason": None,
        "turns": 1,
        "final_text": None,
        "final_text_sha256": None,
        "reasoning_content": None,
        "reasoning_content_sha256": None,
        "tool_calls": None,
        "tool_calls_sha256": None,
        "finish_reason": None,
        "usage": None,
        "elapsed_seconds": None,
        "logprobs": None,
    }

    messages = list(request["messages"])
    mock_responses = loaded_task.task.get("mock_tool_responses") or {}
    force_errors = set(loaded_task.task.get("force_tool_error") or [])
    loop_enabled = bool(mock_responses or force_errors)

    chat_url = f"{base_url.rstrip('/')}/chat/completions"
    started = time.monotonic()
    all_tool_calls: list[dict[str, Any]] = []
    final_text = ""
    reasoning_text = ""
    finish_reason = None
    last_choice: dict[str, Any] = {}
    usage: dict[str, Any] = {}
    truncated = False
    exceeded_turns = False
    turns_used = 0

    try:
        for turn in range(1, max_turns + 1):
            turns_used = turn
            turn_request = dict(request)
            turn_request["messages"] = messages
            response, _ = http_post(chat_url, turn_request, timeout)
            usage = _sum_usage(usage, response.get("usage") or {})
            choices = response.get("choices") or []
            if not choices:
                raise RequestError(
                    "malformed_response", "response has an empty choices array"
                )
            last_choice = choices[0]
            finish_reason = last_choice.get("finish_reason")
            message = last_choice.get("message") or {}
            content = _to_text(message.get("content") or "")
            if content:
                final_text = content
            # Thinking text is recorded SEPARATELY (auditable, diffable across
            # quantisations) and NEVER feeds the graded final_text.
            reasoning = _to_text(
                message.get("reasoning_content") or message.get("reasoning") or ""
            )
            if reasoning:
                reasoning_text = reasoning
            tool_calls = message.get("tool_calls") or []
            if tool_calls:
                all_tool_calls.extend(_parse_tool_args(tool_calls))
            if finish_reason == "length":
                truncated = True
                break
            if not tool_calls:
                break
            if not loop_enabled:
                # A task with no mock table that still emitted a tool call:
                # stop (grade() will fail it as an undeclared/hallucinated
                # call); never loop without scripted results.
                break
            messages.append(message)
            for call in _parse_tool_args(tool_calls):
                messages.append({
                    "role": "tool",
                    "tool_call_id": call["id"] or call["name"],
                    "content": _mock_tool_result(call["name"], mock_responses, force_errors),
                })
        else:
            exceeded_turns = True
    except RequestError as exc:
        record.update({
            "outcome": "error",
            "passed": False,
            "error": str(exc),
            "error_kind": exc.kind,
            "elapsed_seconds": round(time.monotonic() - started, 4),
            "turns": turns_used or 1,
        })
        return record
    except Exception as exc:  # noqa: BLE001 — injectable transport may raise anything
        record.update({
            "outcome": "error",
            "passed": False,
            "error": f"{type(exc).__name__}: {exc}",
            "error_kind": "transport",
            "elapsed_seconds": round(time.monotonic() - started, 4),
            "turns": turns_used or 1,
        })
        return record

    record.update({
        "elapsed_seconds": round(time.monotonic() - started, 4),
        "usage": usage,
        "finish_reason": finish_reason,
        "turns": turns_used,
        "final_text": final_text,
        "final_text_sha256": sha256_hex(final_text) if final_text else None,
        "reasoning_content": reasoning_text or None,
        "reasoning_content_sha256": sha256_hex(reasoning_text) if reasoning_text else None,
    })
    if all_tool_calls:
        record["tool_calls"] = canonical_tool_calls([
            {"function": {"name": c["name"], "arguments": c["arguments"]}} for c in all_tool_calls
        ])
        record["tool_calls_sha256"] = tool_calls_sha256([
            {"function": {"name": c["name"], "arguments": c["arguments"]}} for c in all_tool_calls
        ])
    if logprobs_requested:
        record["logprobs"] = extract_logprobs(last_choice)

    if truncated:
        record.update({
            "outcome": "error",
            "passed": False,
            "error": (
                f"response truncated (finish_reason=length) before a final answer — "
                f"max_tokens={max_tokens} was likely too low"
            ),
            "error_kind": "truncated",
        })
        return record
    if exceeded_turns:
        record.update({
            "outcome": "error",
            "passed": False,
            "error": f"exceeded max_turns ({max_turns}) without a final non-tool-call response",
            "error_kind": "max_turns",
        })
        return record

    result = _grade_result_shape(loaded_task, final_text, all_tool_calls, error=None)
    ok, reason = grade_prompt.grade(result, loaded_task.task["check"])
    record["outcome"] = "passed" if ok else "failed"
    record["passed"] = ok
    record["check_reason"] = reason or None
    return record


# ---------------------------------------------------------------------------
# Offline modes
# ---------------------------------------------------------------------------

def offline_report(mode: str, suite: list[LoadedTask]) -> str:
    lines: list[str] = []
    if mode == "list":
        lines.append(f"canary suite v{CANARY_VERSION} — {len(suite)} tasks")
        lines.append("")
        for loaded in suite:
            task = loaded.task
            sys_prompt = task.get("system_prompt") or ""
            n_tools = len(task.get("tools") or [])
            lines.append(
                f"{loaded.id:32s} {loaded.task['check']['type']:24s} "
                f"grading={loaded.grading:<22s} sys={len(sys_prompt):6d} tools={n_tools}"
            )
    elif mode == "show":
        for loaded in suite:
            task = loaded.task
            lines.append(f"# {loaded.id}  ({loaded.title})")
            lines.append(f"grading: {loaded.grading}")
            lines.append(f"check:   {canonical_json(task['check'])}")
            if task.get("tools"):
                lines.append(f"tools:   {len(task['tools'])} declared")
            mocks = (task.get("mock_tool_responses") or {}).keys()
            if mocks:
                lines.append(f"mock_tool_responses: {sorted(mocks)}")
            if task.get("force_tool_error"):
                lines.append(f"force_tool_error: {sorted(task['force_tool_error'])}")
            if task.get("system_prompt"):
                lines.append(f"system_prompt: {len(task['system_prompt'])} chars")
            user = task.get("messages") or task.get("user_prompt")
            if user:
                rendered = canonical_json(user) if task.get("messages") else str(user)
                lines.append(f"user:    {rendered[:200]}")
            lines.append("")
    else:  # hash
        for loaded in suite:
            request = build_request(
                loaded.task, model="<model>", max_tokens=DEFAULT_MAX_TOKENS
            )
            lines.append(f"{loaded.id:32s} {prompt_sha256(request)}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_endpoint(spec: str, model_arg: str | None) -> tuple[str, str]:
    """Endpoint specs are MODEL@URL or a bare URL (then --model is required)."""
    if "@" in spec:
        model, _, url = spec.partition("@")
        return model.strip(), url.strip()
    if not model_arg:
        raise CanaryError(
            f"endpoint {spec!r} has no model; pass --model or use MODEL@URL form"
        )
    return model_arg, spec


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="canary.py",
        description="Deterministic quantisation canary — fixed suite over "
                    "already-running OpenAI-compatible endpoints (no server "
                    "launch, no results/log.jsonl writes).",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--list-tasks", action="store_true", help="offline: list the fixed suite")
    mode.add_argument("--show-suite", action="store_true", help="offline: full suite details")
    mode.add_argument("--hash-suite", action="store_true",
                        help="offline: stable prompt hashes (model-independent; "
                             "a placeholder model id is used, so hashes pin the "
                             "prompt structure, not a specific model string)")
    parser.add_argument("--endpoint", action="append", default=[],
                        help="already-running endpoint; repeatable; MODEL@URL or URL+--model")
    parser.add_argument("--model", default=None, help="model id for bare-URL endpoints")
    parser.add_argument("--trials", type=int, default=1, help="identical repeats per task per endpoint")
    parser.add_argument("--max-tokens", type=int, default=DEFAULT_MAX_TOKENS,
                        help=f"explicit per-request completion cap (default {DEFAULT_MAX_TOKENS})")
    parser.add_argument("--logprobs", nargs="?", type=int, const=DEFAULT_TOP_LOGPROBS,
                        default=None, metavar="N",
                        help="optional: request logprobs + top_logprobs N (default 5); "
                             "0 requests logprobs without top_logprobs")
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT,
                        help="socket read/inactivity timeout in seconds — NOT a hard "
                             "total per-request deadline "
                             f"(default {DEFAULT_TIMEOUT:g}, matching the pinned "
                             "llama-server's 30-minute request cap)")
    parser.add_argument("--max-turns", type=int, default=DEFAULT_CANARY_MAX_TURNS,
                        help="tool-loop turn budget for mocked tool tasks "
                             f"(default {DEFAULT_CANARY_MAX_TURNS}, deliberately "
                             "run_prompt.py's CLI default, not hermes_ops's 40)")
    parser.add_argument("--output", type=Path, default=None,
                        help="artifact path (default artifacts/canary-<timestamp>.jsonl)")
    args = parser.parse_args(argv)

    if args.max_tokens <= 0:
        parser.error("--max-tokens must be > 0")
    if args.trials <= 0:
        parser.error("--trials must be >= 1")
    if args.logprobs is not None and args.logprobs < 0:
        parser.error("--logprobs N must be >= 0")
    if args.timeout <= 0:
        parser.error("--timeout must be > 0")
    if args.max_turns <= 0:
        parser.error("--max-turns must be >= 1")

    try:
        suite = load_suite()
    except CanaryError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.list_tasks or args.show_suite or args.hash_suite:
        mode = "list" if args.list_tasks else ("show" if args.show_suite else "hash")
        print(offline_report(mode, suite))
        return 0

    # A run REQUIRES endpoints: no network by default.
    if not args.endpoint:
        parser.error(
            "no --endpoint given. Runs need at least one already-running endpoint "
            "(MODEL@URL, or --model + URL); use --list-tasks/--show-suite/--hash-suite "
            "for offline modes"
        )
    try:
        endpoints = [parse_endpoint(spec, args.model) for spec in args.endpoint]
    except CanaryError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    output = args.output or (
        REPO / "artifacts" / f"canary-{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}.jsonl"
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    writer = AtomicJsonlWriter(output)

    run_record: dict[str, Any] = {
        "kind": "run",
        "canary_version": CANARY_VERSION,
        "runner_git_sha": bench_common.git_sha(),
        "endpoints": [{"base_url": u, "model": m} for m, u in endpoints],
        "trials": args.trials,
        "max_tokens": args.max_tokens,
        "max_turns": args.max_turns,
        "temperature": 0,
        "logprobs": args.logprobs if args.logprobs is not None else "not_requested",
        "suite": [t.id for t in suite],
        "started_epoch": time.time(),
    }
    writer.write_row(run_record)

    totals = {"passed": 0, "failed": 0, "errors": 0}
    determinism: dict[str, Any] = {}
    rows_by_key: dict[tuple[str, str], list[dict[str, Any]]] = {}
    completed = True
    fatal_error: str | None = None

    try:
        for model, base_url in endpoints:
            try:
                served_ids = fetch_served_ids(base_url)
            except RequestError as exc:
                served_ids = None
                identity_error = f"identity check failed: {exc}"
            else:
                identity_error = None
                if model not in served_ids:
                    identity_error = (
                        f"model {model!r} is NOT among served ids {served_ids!r} "
                        f"on {base_url}"
                    )

            for trial in range(1, args.trials + 1):
                for loaded in suite:
                    if identity_error:
                        # Unverified endpoint identity (fetch failed, or the
                        # requested model is not served): emit explicit
                        # identity error rows WITHOUT any model request.
                        record = build_identity_error_record(
                            loaded, base_url, model, served_ids,
                            args.max_tokens, trial, identity_error,
                            logprobs_requested=args.logprobs is not None,
                            top_logprobs=args.logprobs if args.logprobs else None,
                        )
                    else:
                        record = run_task_once(
                            loaded, base_url, model, args.max_tokens,
                            logprobs_requested=args.logprobs is not None,
                            top_logprobs=args.logprobs if args.logprobs else None,
                            timeout=args.timeout,
                            max_turns=args.max_turns,
                        )
                        record["kind"] = "trial"
                        record["endpoint"] = {
                            "base_url": base_url,
                            "model": model,
                            "served_ids": served_ids,
                        }
                        record["trial"] = trial
                    writer.write_row(record)
                    rows_by_key.setdefault((loaded.id, base_url), []).append(record)
                    if record["outcome"] == "passed":
                        totals["passed"] += 1
                    elif record["outcome"] == "failed":
                        totals["failed"] += 1
                    else:
                        totals["errors"] += 1
                    print(
                        f"[{model} @ {base_url}] trial {trial}/{args.trials} "
                        f"{loaded.id}: {record['outcome']}"
                        + (f" — {record['check_reason']}" if record["check_reason"] else "")
                        + (f" — {record['error']}" if record["error"] else ""),
                        file=sys.stderr,
                    )
        for (task_id, base_url), records in sorted(rows_by_key.items()):
            determinism.setdefault(task_id, {})[base_url] = trial_consistency(records)
    except KeyboardInterrupt:
        completed = False
        fatal_error = "interrupted (KeyboardInterrupt); partial artifact committed"
        print(fatal_error, file=sys.stderr)
    except Exception as exc:  # noqa: BLE001 — preserve partial artifacts, report
        completed = False
        fatal_error = f"{type(exc).__name__}: {exc}"
        print(f"run failed: {fatal_error}", file=sys.stderr)

    summary = {
        "kind": "summary",
        "finished_epoch": time.time(),
        "tasks_total": len(suite) * len(endpoints) * args.trials,
        **totals,
        "determinism": determinism,
        "completed": completed,
        "error": fatal_error,
    }
    writer.write_row(summary)
    try:
        writer.commit()
    except OSError as exc:
        print(f"error: could not commit artifact: {exc}", file=sys.stderr)
        writer.close()
        return 1
    print(f"artifact: {output}", file=sys.stderr)
    print(
        f"summary: {totals['passed']} passed, {totals['failed']} failed, "
        f"{totals['errors']} errors, completed={completed}",
        file=sys.stderr,
    )

    if not completed or totals["failed"] or totals["errors"] or fatal_error:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())