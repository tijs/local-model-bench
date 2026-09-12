#!/bin/bash
# Is chunked-prefill non-invariance general to transformers, or specific to the
# hybrid recurrent path? Same test as chunk_repeat.sh but on a DENSE model
# (qwen2, 24 attention layers, no recurrent state at all).
SP="$1"; B=/Users/tijs/.local/share/local-model-bench/mei-build-042/release
M=/Users/tijs/.local/share/local-model-bench/mei-models/Qwen2.5-0.5B-Instruct-4bit
cd /Users/tijs/projects/local-model-bench
stop(){ local w; pkill -f "release/me[i] --model-dir" 2>/dev/null
  for w in $(seq 1 30); do lsof -ti:8024 >/dev/null 2>&1 || break; /bin/sleep 1; done; }
leg(){ local label="$1" step="$2" w
  stop
  nohup "$B/mei" --model-dir "$M" --served-model-id dense/test --port 8024 \
    --context-cap 8192 --prefill-step-size "$step" --max-tokens 400 \
    --cache-reuse false > "$SP/dc-$label.log" 2>&1 &
  for w in $(seq 1 60); do grep -q "mei: listening" "$SP/dc-$label.log" 2>/dev/null && break; /bin/sleep 2; done
  grep -q "mei: listening" "$SP/dc-$label.log" || { echo "  SERVER FAIL $label"; tail -3 "$SP/dc-$label.log"; return 1; }
  for r in 1 2; do
    curl -s http://127.0.0.1:8024/v1/chat/completions -H 'Content-Type: application/json' -d '{
      "model":"dense/test",
      "messages":[{"role":"system","content":"You are a precise engineering assistant. Answer directly and do not pad your replies. Prefer concrete detail over generalities. Explain carefully and completely."},
                  {"role":"user","content":"Explain in detail why binary search requires a sorted input, and what goes wrong otherwise."}],
      "temperature":0,"top_k":1,"max_tokens":300}' \
    > "$SP/dc-$label-$r.json"
    python3 -c "
import json
d=json.load(open('$SP/dc-$label-$r.json')); u=d['usage']
c=d['choices'][0]['message'].get('content') or ''
print(f'  {\"$label\":14s} step=$step req$r  ptok {u[\"prompt_tokens\"]:4d} ctok {u[\"completion_tokens\"]:4d}  sha {__import__(\"hashlib\").sha256(c.encode()).hexdigest()[:12]}')"
  done
  stop; }
leg dense_step1024 1024
leg dense_step8       8
leg dense_step4       4
echo "DENSE CHUNK DONE"
