#!/usr/bin/env python3
"""Minimal reproducer: does merely ENABLING anchors change a small cold request?

In the suite, anchors-vs-noanchors first diverges at request 3 — a 299-token
prompt with cached_tokens=0 in BOTH arms — while two same-config runs stay
request-identical until request 54. So the divergence is not the 20k restore.
This sends a short fixed sequence, greedy, and records every reply, so the two
arms can be compared without a single large prefill.

usage: small_reproducer.py <leg-label> <out.json>
"""
import json
import sys
import urllib.request

URL = "http://127.0.0.1:8024/v1/chat/completions"
MODEL = "ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit"
LEG, OUT = sys.argv[1], sys.argv[2]

# Ordered, and order matters: the suite's divergence appears only at the third
# request, so a single one-shot prompt may not reproduce it.
PROMPTS = [
    "Reply with exactly: ready",
    "What is 17 + 25? Answer with the number only.",
    "Explain in one paragraph why binary search needs a sorted input.",
    "List three tradeoffs between mmap and read for large files.",
    "Write a Python function that merges overlapping intervals, with comments.",
]


# A system message is REQUIRED for this probe to mean anything: anchor
# boundaries sit at chat role-turn boundaries, so a bare user-only prompt may
# offer nothing to split, and the probe would report "identical" because the
# mechanism never engaged rather than because it is absent. Keep it small — the
# point is that this is nothing like the 20k preamble — but keep it present.
SYSTEM = ("You are a precise engineering assistant. Answer directly and do not "
          "pad your replies. Prefer concrete detail over generalities.")


def ask(text, n):
    body = json.dumps({
        "model": MODEL,
        "messages": [{"role": "system", "content": SYSTEM},
                     {"role": "user", "content": text}],
        "temperature": 0, "top_k": 1, "max_tokens": n,
    }).encode()
    req = urllib.request.Request(URL, data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=1800) as r:
        p = json.load(r)
    u = p["usage"]
    return {
        "content": p["choices"][0]["message"].get("content") or "",
        "completion_tokens": u["completion_tokens"],
        "prompt_tokens": u["prompt_tokens"],
        "cached_tokens": u.get("prompt_tokens_details", {}).get("cached_tokens", 0),
    }


out = []
for i, text in enumerate(PROMPTS, 1):
    r = ask(text, 400)
    r["index"] = i
    out.append(r)
    print(f"  [{LEG}] req {i}: ptok {r['prompt_tokens']:5d} cached "
          f"{r['cached_tokens']:5d} ctok {r['completion_tokens']:4d}")
json.dump({"leg": LEG, "requests": out}, open(OUT, "w"), indent=2)
