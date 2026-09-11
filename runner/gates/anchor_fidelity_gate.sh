#!/bin/bash
# Captured-anchor fidelity, 5 prompts, fresh server + KV per leg.
# usage: anchor_fidelity_gate.sh <artifact-dir> <build-dir> <artifact-prefix>
SP="$1"; B="$2"; PFX="$3"
KV=/Users/tijs/.local/share/local-model-bench/mei-runtime/kv-$PFX
GATES="$(cd "$(dirname "$0")" && pwd)"
cd "$GATES/../.."
echo "GATE build=$B prefix=$PFX"
"$B/release/mei" --version 2>/dev/null | head -1
stop(){ local w; pkill -f "release/me[i] --model-dir" 2>/dev/null
  for w in $(seq 1 30); do lsof -ti:8024 >/dev/null 2>&1 || break; /bin/sleep 1; done; }
start(){ local w; rm -rf "$KV"; mkdir -p "$KV"
  env VMLX_ENABLE_UNSAFE_COMPILE=1 VMLX_FUSED_GATE_UP_CACHE_LIMIT_BYTES=0 \
    nohup "$B/release/mei" \
      --model-dir /Users/tijs/.local/share/local-model-bench/mei-models/Ornith-1.5-35B-A3B-MLX-4bit-aligned \
      --served-model-id ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit --port 8024 --context-cap 65536 \
      --prefill-step-size 1024 --max-tokens 8192 --ssm-anchor-boundaries 2 \
      --kv-cache-dir "$KV" --temperature 0.6 --top-p 0.95 --top-k 20 \
      --emit-reasoning true --cache-reuse true > "$SP/$PFX-srv.log" 2>&1 &
  for w in $(seq 1 120); do grep -q "mei: listening" "$SP/$PFX-srv.log" 2>/dev/null && return 0; /bin/sleep 5; done
  return 1; }
for idx in 0 1 2 3 4; do
  for leg in cold restored; do
    stop; start || { echo "SERVER FAIL"; exit 1; }
    uv run --locked python "$GATES/anchor_fidelity_leg.py" "$leg" "$idx" "$SP/prompts.json" "$SP/$PFX-$idx-$leg.json"
  done
done
stop; rm -rf "$KV"
uv run --locked python "$GATES/score_anchor_fidelity.py" "$SP" "$PFX"
echo "  restore-invariant warnings: $(grep -c 'cache/restore] WARNING' "$SP/$PFX-srv.log" 2>/dev/null || echo 0)"
echo "FIDELITY GATE DONE prefix=$PFX"
