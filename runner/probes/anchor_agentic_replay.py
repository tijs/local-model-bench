#!/usr/bin/env python3
"""Where does the anchor-restored path first diverge from a cold one?

The anchors arm reproducibly fails hermes_ops-multi-step-chain while the
no-anchors arm reproducibly passes it, generating 1353 tokens instead of 4505
and never calling search_files/read_file/patch. This replays that exact
conversation turn by turn, with the task's own mocked tool responses, so both
legs see IDENTICAL input at every turn. Greedy (temperature 0, top_k 1): with an
exact cache, identical input must give identical output, so ANY difference is
numerical divergence in the restored cache.

usage: anchor_divergence.py <leg-label> <out.json>
"""
import json
import sys
import urllib.request

URL = "http://127.0.0.1:8024/v1/chat/completions"
MODEL = "ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit"
SYS = open("fixtures/hermes_ops/system_prompt.txt").read()
TOOLS = json.load(open("fixtures/hermes_ops/tools.json"))
USER = ("There's a bug in the discount calculator — find it, fix it, and "
        "verify your fix passes the existing tests.")

# Verbatim from tasks/hermes_ops.yaml, so the replay matches what the suite does.
MOCKS = {
    "search_files": '{"matches": ["src/pricing/discount.ts:8:export function calculateDiscount(price, percent) {", "src/pricing/discount.ts:9:  return price - percent;", "tests/discount.test.ts:3:expect(calculateDiscount(100, 20)).toBe(80);"]}',
    "read_file": '{"content": "1|export function calculateDiscount(price, percent) {\\n2|  return price - percent;\\n3|}\\n"}',
    "patch": '{"success": true, "diff": "-  return price - percent;\\n+  return price * (1 - percent / 100);"}',
    "terminal": '{"output": "PASS 1 test", "exit_code": 0, "error": null}',
}
DEFAULT_MOCK = '{"output": "ok", "exit_code": 0, "error": null}'

LEG, OUT = sys.argv[1], sys.argv[2]


def ask(messages):
    body = json.dumps({
        "model": MODEL, "messages": messages, "tools": TOOLS,
        "temperature": 0, "top_k": 1, "max_tokens": 1200,
    }).encode()
    req = urllib.request.Request(URL, data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=1800) as r:
        p = json.load(r)
    m = p["choices"][0]["message"]
    u = p["usage"]
    return m, {
        "content": m.get("content") or "",
        "tool_calls": [(c["function"]["name"], c["function"]["arguments"])
                       for c in (m.get("tool_calls") or [])],
        "completion_tokens": u["completion_tokens"],
        "prompt_tokens": u["prompt_tokens"],
        "cached_tokens": u.get("prompt_tokens_details", {}).get("cached_tokens", 0),
    }


messages = [{"role": "system", "content": SYS}, {"role": "user", "content": USER}]
turns = []
for turn in range(1, 11):
    raw, rec = ask(messages)
    rec["turn"] = turn
    turns.append(rec)
    names = [n for n, _ in rec["tool_calls"]]
    print(f"  [{LEG}] turn {turn}: {rec['completion_tokens']:5d} tok  "
          f"cached {rec['cached_tokens']:6d}  tools {names}")
    if not raw.get("tool_calls"):
        break
    # Replay the assistant turn verbatim, then answer each call with the mock.
    messages.append({k: v for k, v in raw.items()
                     if k in ("role", "content", "tool_calls")})
    for c in raw["tool_calls"]:
        messages.append({
            "role": "tool", "tool_call_id": c["id"],
            "content": MOCKS.get(c["function"]["name"], DEFAULT_MOCK),
        })

json.dump({"leg": LEG, "turns": turns}, open(OUT, "w"), indent=2)
