#!/bin/bash
# Is the 15-vs-14 chunking difference deterministic, or MLX noise?
SP="$1"; B=/Users/tijs/.local/share/local-model-bench/mei-build-seed
cd /Users/tijs/projects/local-model-bench
stop(){ local w; pkill -f "release/me[i] --model-dir" 2>/dev/null
  for w in $(seq 1 30); do lsof -ti:8024 >/dev/null 2>&1 || break; /bin/sleep 1; done; }
leg(){ local label="$1" step="$2" w
  stop
  env VMLX_ENABLE_UNSAFE_COMPILE=1 VMLX_FUSED_GATE_UP_CACHE_LIMIT_BYTES=0 \
    nohup "$B/release/mei" \
      --model-dir /Users/tijs/.local/share/local-model-bench/mei-models/Ornith-1.5-35B-A3B-MLX-4bit-aligned \
      --served-model-id ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit --port 8024 \
      --context-cap 65536 --prefill-step-size "$step" --max-tokens 8192 \
      --cache-reuse false > "$SP/cr-$label.log" 2>&1 &
  for w in $(seq 1 180); do grep -q "mei: listening" "$SP/cr-$label.log" 2>/dev/null && break; /bin/sleep 5; done
  # three identical requests in one server, to separate within-server
  # determinism from across-server variation
  for r in 1 2 3; do
    curl -s http://127.0.0.1:8024/v1/chat/completions -H 'Content-Type: application/json' -d '{
      "model":"ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit",
      "messages":[{"role":"system","content":"You are a precise engineering assistant. Answer directly and do not pad your replies. Prefer concrete detail over generalities."},
                  {"role":"user","content":"Reply with exactly: ready"}],
      "temperature":0,"top_k":1,"max_tokens":400}' \
    | python3 -c "
import json,sys
d=json.load(sys.stdin); u=d['usage']
print(f'  {\"$label\":16s} req$r ctok {u[\"completion_tokens\"]}')"
  done
  stop; }
leg step1024_a 1024
leg step32_a     32
leg step1024_b 1024
leg step32_b     32
echo "CHUNK REPEAT DONE"
