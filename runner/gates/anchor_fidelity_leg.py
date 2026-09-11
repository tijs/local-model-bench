#!/usr/bin/env python3
"""One prompt, one fresh server, on the SHIPPED anchor path.

The release candidate has no adaptive boundary, so cross-conversation reuse
comes from the structural anchor — which requires an IDENTICAL system prompt.
That is the path prefix reuse ships with, and the one this gate must cover.
"""
import json, sys, urllib.request
URL="http://127.0.0.1:8024/v1/chat/completions"
MODEL="ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit"
SYS=open("fixtures/hermes_ops/system_prompt.txt").read()      # identical for all
TOOLS=json.load(open("fixtures/hermes_ops/tools.json"))
LEG, IDX, PJ, OUT = sys.argv[1], int(sys.argv[2]), sys.argv[3], sys.argv[4]
PROMPTS=json.load(open(PJ))
def ask(user,n):
    body=json.dumps({"model":MODEL,"messages":[{"role":"system","content":SYS},
        {"role":"user","content":user}],"tools":TOOLS,"temperature":0,"top_k":1,
        "max_tokens":n}).encode()
    req=urllib.request.Request(URL,data=body,headers={"Content-Type":"application/json"})
    with urllib.request.urlopen(req,timeout=1800) as r: p=json.load(r)
    u,m=p["usage"],p["choices"][0]["message"]
    return {"text":m.get("content") or "",
            "tool_calls":[(c["function"]["name"],c["function"]["arguments"]) for c in (m.get("tool_calls") or [])],
            "completion_tokens":u["completion_tokens"],"prompt_tokens":u["prompt_tokens"],
            "cached_tokens":u.get("prompt_tokens_details",{}).get("cached_tokens",0)}
if LEG=="restored":
    ask("An unrelated earlier conversation: state your role in one line.", 40)
r=ask(PROMPTS[IDX], 300)
print(f"  {LEG:8s} p{IDX}: prompt {r['prompt_tokens']:,} cached {r['cached_tokens']:,} "
      f"ctok {r['completion_tokens']} tools {[t[0] for t in r['tool_calls']]}")
json.dump(r, open(OUT,"w"), indent=2)
