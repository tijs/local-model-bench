#!/bin/bash
# C1 token-equality: VMLX_ENABLE_UNSAFE_COMPILE=0 vs =1 must match token-for-token.
# usage: c1_gate.sh <scratchpad> <build-dir> <prefix>
SP="$1"; B="$2"; PFX="$3"
GATES="$(cd "$(dirname "$0")" && pwd)"
cd "$GATES/../.."
stop(){ local w; pkill -f "release/me[i] --model-dir" 2>/dev/null
  for w in $(seq 1 30); do lsof -ti:8024 >/dev/null 2>&1 || break; /bin/sleep 1; done; }
run_leg(){ local c1="$1" log="$SP/$PFX-c1$c1.log" w
  stop
  env VMLX_ENABLE_UNSAFE_COMPILE="$c1" VMLX_FUSED_GATE_UP_CACHE_LIMIT_BYTES=0 \
    nohup "$B/release/mei" \
      --model-dir /Users/tijs/.local/share/local-model-bench/mei-models/Ornith-1.5-35B-A3B-MLX-4bit-aligned \
      --served-model-id ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit --port 8024 \
      --context-cap 65536 --prefill-step-size 1024 --max-tokens 8192 \
      --temperature 0.6 --top-p 0.95 --top-k 20 --cache-reuse false > "$log" 2>&1 &
  for w in $(seq 1 120); do grep -q "mei: listening" "$log" 2>/dev/null && break; /bin/sleep 5; done
  grep -q "mei: listening" "$log" || { echo "SERVER FAIL c1=$c1"; return 1; }
  # prove the leg really ran with the intended flag
  echo "  banner: $(grep -o 'unsafe-compile [01]' "$log" | head -1)  (requested $c1)"
  grep -q "unsafe-compile $c1" "$log" || { echo "FLAG NOT APPLIED c1=$c1"; return 1; }
  uv run --locked python "$GATES/c1_equality.py" "$SP/$PFX-c1$c1.json"; }
echo "C1 GATE build=$B"
echo "-- leg C1=0"; run_leg 0 || exit 1
echo "-- leg C1=1"; run_leg 1 || exit 1
stop
uv run --locked python - "$SP/$PFX-c10.json" "$SP/$PFX-c11.json" <<'PY'
import json,sys
a=json.load(open(sys.argv[1])); b=json.load(open(sys.argv[2]))
bad=[k for k in a if a[k]!=b[k]]
for k in a:
    print(f"  {k}: {'SAME' if a[k]==b[k] else 'DIFFER'} ({a[k]['completion_tokens']} vs {b[k]['completion_tokens']} tok)")
print("C1 TOKEN EQUALITY:", "PASS" if not bad else f"FAIL {bad}")
PY
echo "C1 GATE DONE"
