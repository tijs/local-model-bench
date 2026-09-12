#!/usr/bin/env python3
"""The 43-token reproducer, one request, greedy."""
import json, sys, urllib.request
LABEL, OUT = sys.argv[1], sys.argv[2]
body = json.dumps({
    "model": "ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit",
    "messages": [{"role": "system", "content": "You are a precise engineering assistant. Answer directly and do not pad your replies. Prefer concrete detail over generalities."},
                 {"role": "user", "content": "Reply with exactly: ready"}],
    "temperature": 0, "top_k": 1, "max_tokens": 400,
}).encode()
req = urllib.request.Request("http://127.0.0.1:8024/v1/chat/completions", data=body,
                             headers={"Content-Type": "application/json"})
with urllib.request.urlopen(req, timeout=600) as r:
    p = json.load(r)
u = p["usage"]
rec = {"content": p["choices"][0]["message"].get("content") or "",
       "completion_tokens": u["completion_tokens"], "prompt_tokens": u["prompt_tokens"],
       "cached_tokens": u.get("prompt_tokens_details", {}).get("cached_tokens", 0)}
print(f"  [{LABEL}] ptok {rec['prompt_tokens']} cached {rec['cached_tokens']} ctok {rec['completion_tokens']}")
json.dump(rec, open(OUT, "w"), indent=2)
