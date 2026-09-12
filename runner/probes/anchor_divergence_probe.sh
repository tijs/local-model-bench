#!/bin/bash
# Where does enabling anchors first change greedy output, and does
# VMLX_GDN_STRICT=1 undo it?
#
# Hypothesis (from vmlx GatedDelta.swift's own comment): anchors split the
# prefill at boundary positions to capture snapshots, and the fast gated-delta
# kernel accumulates recurrent state in float32 registers across a whole
# invocation, materialising it only at the end. A split therefore round-trips
# the state through memory at a boundary a single call never has -> different
# numerics -> different greedy output, with NO restore involved. The strict
# kernel rounds state every step, so segmentation should stop mattering.
SP="$1"; B=/Users/tijs/.local/share/local-model-bench/mei-build-seed
KV=/Users/tijs/.local/share/local-model-bench/mei-runtime/kv-divergence
PROBES="$(cd "$(dirname "$0")" && pwd)"
cd /Users/tijs/projects/local-model-bench
echo "PROBE build=$B"; "$B/release/mei" --version
stop(){ local w; pkill -f "release/me[i] --model-dir" 2>/dev/null
  for w in $(seq 1 30); do lsof -ti:8024 >/dev/null 2>&1 || break; /bin/sleep 1; done; }
# start <on|off> <leg> <strict 0|1>
start(){ local anchors="$1" leg="$2" strict="$3" w extra=()
  stop; rm -rf "$KV"; mkdir -p "$KV"
  [ "$anchors" = "on" ] && extra=(--ssm-anchor-boundaries 2)
  env VMLX_ENABLE_UNSAFE_COMPILE=1 VMLX_FUSED_GATE_UP_CACHE_LIMIT_BYTES=0 \
      VMLX_GDN_STRICT="$strict" \
    nohup "$B/release/mei" \
      --model-dir /Users/tijs/.local/share/local-model-bench/mei-models/Ornith-1.5-35B-A3B-MLX-4bit-aligned \
      --served-model-id ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit --port 8024 \
      --context-cap 65536 --prefill-step-size 1024 --max-tokens 8192 \
      --kv-cache-dir "$KV" --cache-reuse true "${extra[@]}" \
      > "$SP/div-$leg.log" 2>&1 &
  for w in $(seq 1 180); do grep -q "mei: listening" "$SP/div-$leg.log" 2>/dev/null && return 0; /bin/sleep 5; done
  return 1; }
seed(){ uv run --locked python - <<'PY'
import json, urllib.request
SYS=open("fixtures/hermes_ops/system_prompt.txt").read()
TOOLS=json.load(open("fixtures/hermes_ops/tools.json"))
b=json.dumps({"model":"ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit",
  "messages":[{"role":"system","content":SYS},
              {"role":"user","content":"State your role in one short line."}],
  "tools":TOOLS,"temperature":0,"top_k":1,"max_tokens":40}).encode()
r=urllib.request.Request("http://127.0.0.1:8024/v1/chat/completions",data=b,
  headers={"Content-Type":"application/json"})
with urllib.request.urlopen(r,timeout=1800) as f: json.load(f)
print("  (anchor seeded)")
PY
}
#          leg           anchors strict  seed-anchor
run_leg(){ local leg="$1" anchors="$2" strict="$3"
  echo "--- leg $leg (anchors=$anchors strict=$strict) ---"
  start "$anchors" "$leg" "$strict" || { echo "SERVER FAIL $leg"; exit 1; }
  # Seed EVERY leg, not just the anchors ones. Seeding only the anchors legs
  # made them differ from the cold legs in two ways — the flag, and having seen
  # a prior 20k conversation — so nothing downstream isolated the flag. With
  # anchors off the seed simply stores no anchor.
  seed
  uv run --locked python "$PROBES/anchor_minimal_reproducer.py" "$leg" "$SP/small2-$leg.json"
  uv run --locked python "$PROBES/anchor_agentic_replay.py" "$leg" "$SP/div2-$leg.json"; }
run_leg anchorsA      on  0
run_leg anchorsB      on  0
run_leg noanchors     off 0
run_leg anchorsStrict on  1
run_leg noanchorsStrict off 1
stop; rm -rf "$KV"
uv run --locked python "$PROBES/anchor_compare.py" "$SP" 2
echo "DIVERGENCE PROBE DONE"
