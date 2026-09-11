#!/usr/bin/env python3
"""C1 token-equality gate: VMLX_ENABLE_UNSAFE_COMPILE must not change output.

The runbook requires re-verifying this after ANY vmlx re-pin, because the flag's
documented failure mode is silent numerical corruption rather than a crash.
Long greedy generations plus a native tool call, compared token-for-token.
"""
import json, sys, urllib.request
URL="http://127.0.0.1:8024/v1/chat/completions"
MODEL="ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit"
TOOLS=json.load(open("fixtures/hermes_ops/tools.json"))
OUT=sys.argv[1]
QS=["Explain step by step how a B-tree insert works, in detail.",
    "Write a Python function that merges overlapping intervals, with comments.",
    "Describe the tradeoffs between mmap and read for large files.",
    "List the tools you have and say when each is appropriate."]
def ask(user,n,tools=None):
    b={"model":MODEL,"messages":[{"role":"user","content":user}],
       "temperature":0,"top_k":1,"max_tokens":n}
    if tools: b["tools"]=tools
    req=urllib.request.Request(URL,data=json.dumps(b).encode(),
        headers={"Content-Type":"application/json"})
    with urllib.request.urlopen(req,timeout=1800) as r: p=json.load(r)
    m=p["choices"][0]["message"]
    return {"text":m.get("content") or "",
            "tool_calls":[(c["function"]["name"],c["function"]["arguments"]) for c in (m.get("tool_calls") or [])],
            "completion_tokens":p["usage"]["completion_tokens"]}
res={f"q{i}":ask(q,700) for i,q in enumerate(QS)}
res["tool"]=ask("Add 17 and 25 using a tool.",200,TOOLS)
for k,v in res.items():
    print(f"  {k}: {v['completion_tokens']} tok {[t[0] for t in v['tool_calls']]}")
json.dump(res, open(OUT,"w"), indent=2)
