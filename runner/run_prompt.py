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
import json
import sys
import time
import urllib.request
import urllib.error


def call_backend(base_url, model, messages, tools, temperature, timeout):
    body = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": 1024,
    }
    if tools:
        body["tools"] = tools
    req = urllib.request.Request(
        f"{base_url.rstrip('/')}/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--spec", required=True, help="path to task_spec.json")
    ap.add_argument("--max-turns", type=int, default=6)
    ap.add_argument("--temperature", type=float, default=0)
    ap.add_argument("--timeout", type=float, default=120)
    args = ap.parse_args()

    spec = json.loads(open(args.spec).read())
    tools = spec.get("tools") or None
    mock_responses = spec.get("mock_tool_responses", {})
    force_errors = set(spec.get("force_tool_error", []))

    messages = []
    if spec.get("system_prompt"):
        messages.append({"role": "system", "content": spec["system_prompt"]})
    messages.append({"role": "user", "content": spec["user_prompt"]})

    all_tool_calls = []
    prompt_tokens = completion_tokens = 0
    start = time.time()
    error = None
    final_text = ""
    turns = 0

    try:
        for turns in range(1, args.max_turns + 1):
            resp = call_backend(
                args.base_url, args.model, messages, tools, args.temperature, args.timeout
            )
            usage = resp.get("usage", {})
            prompt_tokens += usage.get("prompt_tokens", 0)
            completion_tokens += usage.get("completion_tokens", 0)

            choice = resp["choices"][0]
            msg = choice["message"]
            messages.append(msg)

            tool_calls = msg.get("tool_calls") or []
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

                if fn["name"] in force_errors:
                    result_text = json.dumps({"error": f"{fn['name']} failed: simulated error for benchmark"})
                elif fn["name"] in mock_responses:
                    result_text = mock_responses[fn["name"]]
                else:
                    result_text = json.dumps({"error": f"no mock response defined for tool '{fn['name']}'"})

                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.get("id", fn["name"]),
                        "content": result_text,
                    }
                )
        else:
            error = f"exceeded max_turns ({args.max_turns}) without a final non-tool-call response"
    except urllib.error.URLError as e:
        error = f"request failed: {e}"
    except (KeyError, IndexError, json.JSONDecodeError) as e:
        error = f"unexpected response shape: {e}"

    wall = time.time() - start
    result = {
        "messages": messages,
        "tool_calls": all_tool_calls,
        "final_text": final_text,
        "turns": turns,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": prompt_tokens + completion_tokens,
        "wall_seconds": round(wall, 3),
        "tokens_per_second": round(completion_tokens / wall, 2) if wall > 0 else None,
        "error": error,
    }
    print(json.dumps(result, indent=2))
    sys.exit(1 if error else 0)


if __name__ == "__main__":
    main()
