#!/usr/bin/env python3
"""
Generic OpenAI-chat-completions harness: sends a system+user prompt (with an
optional tool manifest) to a local model backend, mocks tool execution for
any tool call the caller has a scripted response for, and continues the
conversation until the model stops calling tools or --max-turns is hit.

Used by both the sanity tier (1 tool, minimal prompt) and hermes_ops (Hermes's
real system prompt + tool manifest) — same mechanism, different scale.

Usage:
  run_prompt.py --base-url http://127.0.0.1:8012/v1 --model <name> \
      --spec task_spec.json [--max-turns 6] [--temperature 0]

task_spec.json:
  {
    "system_prompt": "...",
    "user_prompt": "...",
    "tools": [ {"type": "function", "function": {...}}, ... ],   // optional
    "mock_tool_responses": { "tool_name": "<string returned as tool result>" },
    "force_tool_error": ["tool_name", ...]   // optional: return an error string instead
  }

Replicates Hermes's real tool_loop_guardrails (~/.hermes/config.yaml) so a
model gets the same "you're not making progress" nudge a real Hermes session
would inject — testing raw model behavior without this would understate how
the model actually behaves in production, where these nudges exist.
hard_stop_enabled is false in the real config, so this only ever warns, it
never forces a stop — matches that. Thresholds (warn after N calls):
exact_failure=2 (same tool+args, failing), same_tool_failure=3 (same tool,
any args, failing), idempotent_no_progress=2 (same tool, consecutive calls
returning an identical result). Each warning fires once per tool per run.

Prints a single JSON result to stdout:
  {
    "messages": [...],           // full conversation incl. tool turns
    "tool_calls": [{"name":..., "arguments": {...}}, ...],  // all tool calls made, in order
    "final_text": "...",         // last assistant message's text content
    "turns": N,
    "prompt_tokens": N, "completion_tokens": N, "total_tokens": N,
    "wall_seconds": N,
    "tokens_per_second": N,      // completion_tokens / wall_seconds
    "error": null | "message"    // set if the run failed (timeout, HTTP error, etc.)
  }
"""
import argparse
import http.client
import json
import os
import sys
import time
import urllib.request
import urllib.error


GUARDRAIL_WARN_AFTER = {"exact_failure": 2, "same_tool_failure": 3, "idempotent_no_progress": 2}


def guardrail_warning(tool_history, name, args_key, warned):
    """Mirrors ~/.hermes/config.yaml's tool_loop_guardrails (warn-only, hard_stop_enabled=false)."""
    same_name = [h for h in tool_history if h["name"] == name]

    exact_same = [h for h in same_name if h["args_key"] == args_key]
    exact_failures = sum(1 for h in exact_same if h["is_failure"])
    if exact_failures >= GUARDRAIL_WARN_AFTER["exact_failure"] and f"{name}:exact" not in warned:
        warned.add(f"{name}:exact")
        return (
            f"[guardrail] You've called {name} with these exact arguments {exact_failures} times "
            "and it keeps failing the same way. Repeating it again won't change the outcome — "
            "try a different approach, or tell the user it isn't working."
        )

    same_tool_failures = sum(1 for h in same_name if h["is_failure"])
    if same_tool_failures >= GUARDRAIL_WARN_AFTER["same_tool_failure"] and f"{name}:same_tool" not in warned:
        warned.add(f"{name}:same_tool")
        return (
            f"[guardrail] You've called {name} {same_tool_failures} times without success. "
            "Consider a different tool, or report this back to the user instead of continuing to retry."
        )

    idempotent = 0
    prev = None
    for h in same_name:
        if prev is not None and h["result_text"] == prev:
            idempotent += 1
        prev = h["result_text"]
    if idempotent >= GUARDRAIL_WARN_AFTER["idempotent_no_progress"] and f"{name}:idempotent" not in warned:
        warned.add(f"{name}:idempotent")
        return (
            f"[guardrail] Your last few calls to {name} returned the same result — no new "
            "information. Repeating it again won't help; try something else or report back to the user."
        )

    return None


def call_backend_streaming(base_url, model, messages, tools, temperature, timeout, max_tokens, api_key=None):
    """Streams the response so we can measure real time-to-first-token
    (TTFT) — separate from total wall time, since a big fixed system prompt
    mostly costs prefill time, not generation time. Reassembles the stream
    into the same shape a non-streaming call would return, so callers don't
    need to know the difference. Backends that don't send true token-by-
    token deltas (e.g. buffer the whole response into one SSE chunk) will
    just report ttft ~= total generation time, which is itself useful
    signal, not a bug."""
    body = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": True,
        "stream_options": {"include_usage": True},
    }
    if tools:
        body["tools"] = tools
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    req = urllib.request.Request(
        f"{base_url.rstrip('/')}/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers=headers,
        method="POST",
    )

    start = time.time()
    ttft = None
    content_parts = []
    tool_calls_acc = {}
    usage = {}
    finish_reason = None

    with urllib.request.urlopen(req, timeout=timeout) as resp:
        for raw_line in resp:
            line = raw_line.decode("utf-8").strip()
            if not line or not line.startswith("data:"):
                continue
            data = line[len("data:"):].strip()
            if data == "[DONE]":
                break
            chunk = json.loads(data)
            if chunk.get("usage"):
                usage = chunk["usage"]
            choices = chunk.get("choices") or []
            if not choices:
                continue
            delta = choices[0].get("delta", {})
            if delta.get("content") or delta.get("tool_calls"):
                if ttft is None:
                    ttft = time.time() - start
            if delta.get("content"):
                content_parts.append(delta["content"])
            for tc_delta in delta.get("tool_calls") or []:
                # Flagged by a 3rd adversarial review (low finding): if a
                # backend ever streamed TWO parallel tool calls without an
                # "index" field on either delta, both would collapse into
                # tool_calls_acc[0] and their names/arguments would
                # concatenate into one garbled call. Accepted as a known
                # limitation rather than patched: "index" is part of
                # OpenAI's streaming tool_calls delta spec and every
                # backend actually configured in this repo
                # (llama-server/vllm-mlx, proxied or not) includes it —
                # confirmed by inspecting live streamed responses during
                # this session, no index-less parallel-call case observed.
                # A backend that genuinely omits it would ALSO be giving
                # this code no way to tell two calls apart after the fact,
                # so there's no purely-code fix that recovers information
                # the stream never sent.
                idx = tc_delta.get("index", 0)
                if idx not in tool_calls_acc:
                    tool_calls_acc[idx] = {"id": tc_delta.get("id"), "type": "function", "function": {"name": "", "arguments": ""}}
                if tc_delta.get("id"):
                    tool_calls_acc[idx]["id"] = tc_delta["id"]
                fn_delta = tc_delta.get("function") or {}
                if fn_delta.get("name"):
                    tool_calls_acc[idx]["function"]["name"] += fn_delta["name"]
                if fn_delta.get("arguments"):
                    tool_calls_acc[idx]["function"]["arguments"] += fn_delta["arguments"]
            if choices[0].get("finish_reason"):
                finish_reason = choices[0]["finish_reason"]

    message = {"role": "assistant", "content": "".join(content_parts) or None}
    if tool_calls_acc:
        message["tool_calls"] = [tool_calls_acc[i] for i in sorted(tool_calls_acc)]

    usage_estimated = False
    if not usage.get("prompt_tokens") and not usage.get("completion_tokens"):
        # This backend never sends a usage chunk during streaming (confirmed
        # live — stream_options.include_usage is a no-op here), even though
        # the non-streaming endpoint reports it accurately. Fall back to a
        # rough ~4-chars-per-token estimate rather than silently reporting 0.
        usage_estimated = True
        prompt_chars = sum(len(json.dumps(m)) for m in messages)
        if tools:
            prompt_chars += len(json.dumps(tools))
        completion_chars = len("".join(content_parts)) + sum(
            len(tc["function"]["arguments"]) + len(tc["function"]["name"]) for tc in tool_calls_acc.values()
        )
        usage = {
            "prompt_tokens": max(1, prompt_chars // 4),
            "completion_tokens": max(1, completion_chars // 4),
        }

    return {
        "choices": [{"message": message, "finish_reason": finish_reason}],
        "usage": usage,
        "usage_estimated": usage_estimated,
    }, ttft


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--spec", required=True, help="path to task_spec.json")
    ap.add_argument("--max-turns", type=int, default=6)
    ap.add_argument("--temperature", type=float, default=0)
    ap.add_argument("--timeout", type=float, default=120)
    ap.add_argument("--max-tokens", type=int, default=4096,
                     help="per-turn completion cap sent as the request's max_tokens "
                          "(default 4096, matching the bench profile's own cap in "
                          "~/.hermes/profiles/bench/config.yaml) — was hardcoded to 1024 "
                          "until adversarial review finding M1, which silently truncated "
                          "longer reasoning-mode responses before a real answer")
    ap.add_argument("--api-key-env", default=None,
                     help="name of an env var holding a Bearer token for hosted "
                          "APIs (e.g. OPENROUTER_API_KEY) — the value is read from "
                          "this process's own environment, never passed as a CLI arg")
    args = ap.parse_args()

    api_key = os.environ.get(args.api_key_env) if args.api_key_env else None
    if args.api_key_env and not api_key:
        sys.exit(f"--api-key-env {args.api_key_env} was given but that env var is unset")

    spec = json.loads(open(args.spec).read())
    tools = spec.get("tools") or None
    mock_responses = spec.get("mock_tool_responses", {})
    force_errors = set(spec.get("force_tool_error", []))

    messages = []
    if spec.get("system_prompt"):
        messages.append({"role": "system", "content": spec["system_prompt"]})
    messages.append({"role": "user", "content": spec["user_prompt"]})

    all_tool_calls = []
    tool_history = []  # [{"name":..., "args_key":..., "result_text":..., "is_failure": bool}]
    guardrail_warned = set()
    prompt_tokens = completion_tokens = 0
    start = time.time()
    error = None
    final_text = ""
    turns = 0
    ttft_seconds = None  # time-to-first-token of the FIRST API call in this run
    usage_estimated = False
    total_cost_usd = None  # only hosted/metered backends (e.g. OpenRouter)
    # report this in their usage object; stays None for local models

    try:
        for turns in range(1, args.max_turns + 1):
            resp, turn_ttft = call_backend_streaming(
                args.base_url, args.model, messages, tools, args.temperature, args.timeout,
                args.max_tokens, api_key=api_key,
            )
            if ttft_seconds is None:
                ttft_seconds = turn_ttft
            if resp.get("usage_estimated"):
                usage_estimated = True
            usage = resp.get("usage", {})
            prompt_tokens += usage.get("prompt_tokens", 0)
            completion_tokens += usage.get("completion_tokens", 0)
            if usage.get("cost") is not None:
                total_cost_usd = (total_cost_usd or 0) + usage["cost"]

            choice = resp["choices"][0]
            msg = choice["message"]
            messages.append(msg)

            tool_calls = msg.get("tool_calls") or []
            if choice.get("finish_reason") == "length":
                # A response cut off mid-generation (hit max_tokens) is NOT
                # the model's real final answer — grading it as one
                # silently penalizes exactly the models this benchmark
                # deliberately runs in high-reasoning/thinking mode
                # (adversarial review finding M1): a longer reasoning
                # trace is more likely to hit the ceiling before reaching
                # a real answer. Surface it as a run error instead of a
                # graded (near-certainly wrong) response.
                #
                # Checked BEFORE `if not tool_calls`, not just inside it
                # (3rd adversarial review, low finding): a tool call can
                # ALSO be truncated mid-arguments by hitting max_tokens —
                # the old code only ever checked this when tool_calls was
                # empty, so a cut-off tool call's mangled JSON arguments
                # (caught downstream as {"_raw": ...} on a JSONDecodeError)
                # got graded as a real, if malformed, tool call — the same
                # unfairness M1 was written to prevent, just one branch
                # over.
                error = (
                    f"response truncated (finish_reason=length) before a final "
                    f"answer — max_tokens={args.max_tokens} was likely too low for "
                    f"this turn, not a real answer to grade"
                )
                break
            if not tool_calls:
                final_text = msg.get("content") or ""
                break

            for tc in tool_calls:
                fn = tc["function"]
                try:
                    fn_args = json.loads(fn.get("arguments") or "{}")
                except json.JSONDecodeError:
                    fn_args = {"_raw": fn.get("arguments")}
                all_tool_calls.append({"name": fn["name"], "arguments": fn_args})

                is_failure = True
                if fn["name"] in force_errors:
                    # Wording deliberately realistic — must not reveal this is a
                    # scripted/mock harness (a model that spots "simulated" or
                    # "benchmark" in a tool result reasonably starts discounting
                    # ALL tool output as fake, including genuinely good results
                    # later in the same run — confirmed live 2026-08-20).
                    result_text = json.dumps({"error": f"{fn['name']}: request failed (connection reset)"})
                elif fn["name"] in mock_responses:
                    result_text = mock_responses[fn["name"]]
                    is_failure = False
                else:
                    # Same realism requirement — a tool the task didn't script a
                    # response for should look like an ordinary failure, not a
                    # giveaway that the harness is scripted.
                    result_text = json.dumps({"error": f"{fn['name']}: service temporarily unavailable"})

                args_key = json.dumps(fn_args, sort_keys=True)
                warning = guardrail_warning(tool_history, fn["name"], args_key, guardrail_warned)
                tool_history.append(
                    {"name": fn["name"], "args_key": args_key, "result_text": result_text, "is_failure": is_failure}
                )
                if warning:
                    result_text = result_text + "\n\n" + warning

                messages.append(
                    {
                        "role": "tool",
                        # `tc.get("id", fn["name"])` (3rd adversarial
                        # review, low finding): tool_calls_acc's streaming
                        # accumulation always sets the "id" KEY, even when
                        # no chunk ever carried a real id (it defaults to
                        # None at index-creation time and is only
                        # overwritten if a later delta has a truthy one) —
                        # so the key was never actually MISSING, just None,
                        # and dict.get's default only fires on a missing
                        # key, not a None value. `or` falls back correctly
                        # on both.
                        "tool_call_id": tc.get("id") or fn["name"],
                        "content": result_text,
                    }
                )
        else:
            error = f"exceeded max_turns ({args.max_turns}) without a final non-tool-call response"
    except urllib.error.URLError as e:
        error = f"request failed: {e}"
    except (KeyError, IndexError, json.JSONDecodeError) as e:
        error = f"unexpected response shape: {e}"
    except (TimeoutError, http.client.HTTPException, OSError) as e:
        # A read timeout (socket.timeout IS TimeoutError, but is NOT a
        # urllib.error.URLError subclass, so it fell straight through the
        # handler above uncaught) or a stream cut short mid-response
        # (http.client.IncompleteRead) used to crash this process entirely
        # — adversarial review finding M3. run_prompt_suite.py's JSON-decode
        # of empty stdout then silently produced `pass: false, run_error:
        # null`, indistinguishable from a genuine graded model failure.
        error = f"connection error mid-request: {type(e).__name__}: {e}"

    # Tool-call parsing here is regex/text-based, not schema-validated — a
    # model can emit a call to a name it was never actually offered (and a
    # misconfigured proxy/filter upstream can silently drop tools before the
    # model ever sees them). Surface that mismatch explicitly rather than
    # letting a check accidentally pass on a hallucinated tool name.
    declared_names = {t["function"]["name"] for t in (tools or [])}
    hallucinated_tool_calls = [c["name"] for c in all_tool_calls if c["name"] not in declared_names]

    wall = time.time() - start
    result = {
        "messages": messages,
        "tool_calls": all_tool_calls,
        "hallucinated_tool_calls": hallucinated_tool_calls,
        "final_text": final_text,
        "turns": turns,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": prompt_tokens + completion_tokens,
        "wall_seconds": round(wall, 3),
        "tokens_per_second": round(completion_tokens / wall, 2) if wall > 0 else None,
        "ttft_seconds": round(ttft_seconds, 3) if ttft_seconds is not None else None,
        "usage_estimated": usage_estimated,
        "total_cost_usd": total_cost_usd,
        "error": error,
    }
    print(json.dumps(result, indent=2))
    sys.exit(1 if error else 0)


if __name__ == "__main__":
    main()
