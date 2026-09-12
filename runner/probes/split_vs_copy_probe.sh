#!/bin/bash
# base    : anchors off                       -> reference (known: 15 tokens)
# anchors : anchors on, snapshot stored       -> known defect (27 tokens)
# nostore : anchors on, split+eval, NO store  -> which half causes it?
SP="$1"; B=/Users/tijs/projects/mei-align/.build/release
KV=/Users/tijs/.local/share/local-model-bench/mei-runtime/kv-nostore
cd /Users/tijs/projects/local-model-bench
stop(){ local w; pkill -f "release/me[i] --model-dir" 2>/dev/null
  for w in $(seq 1 30); do lsof -ti:8024 >/dev/null 2>&1 || break; /bin/sleep 1; done; }
leg(){ local label="$1" anchors="$2" nostore="$3" w extra=()
  stop; rm -rf "$KV"; mkdir -p "$KV"
  [ "$anchors" = "on" ] && extra=(--ssm-anchor-boundaries 2)
  env VMLX_ENABLE_UNSAFE_COMPILE=1 VMLX_FUSED_GATE_UP_CACHE_LIMIT_BYTES=0 \
      VMLX_NO_SNAPSHOT_STORE="$nostore" VMLX_CACHE_FETCH_TRACE=1 \
    nohup "$B/mei" \
      --model-dir /Users/tijs/.local/share/local-model-bench/mei-models/Ornith-1.5-35B-A3B-MLX-4bit-aligned \
      --served-model-id ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit --port 8024 \
      --context-cap 65536 --prefill-step-size 1024 --max-tokens 8192 \
      --kv-cache-dir "$KV" --cache-reuse true "${extra[@]}" \
      > "$SP/ns-$label.log" 2>&1 &
  for w in $(seq 1 180); do grep -q "mei: listening" "$SP/ns-$label.log" 2>/dev/null && break; /bin/sleep 5; done
  grep -q "mei: listening" "$SP/ns-$label.log" || { echo "  SERVER FAIL $label"; return 1; }
  uv run --locked python "$SP/small_one.py" "$label" "$SP/ns-$label.json"
  echo "    store-boundary lines: $(grep -c 'store-boundary' "$SP/ns-$label.log")  no-store fired: $(grep -c 'no-store' "$SP/ns-$label.log")"
  stop; }
leg base    off 0
leg anchors on  0
leg nostore on  1
rm -rf "$KV"
uv run --locked python - "$SP" <<'PY'
import json,sys,os
SP=sys.argv[1]
g=lambda n: json.load(open(f"{SP}/ns-{n}.json")) if os.path.exists(f"{SP}/ns-{n}.json") else None
b,a,n=g('base'),g('anchors'),g('nostore')
if not (b and a and n): print("  MISSING legs"); raise SystemExit
same=lambda x,y: x['content']==y['content'] and x['completion_tokens']==y['completion_tokens']
print(f"  base    ctok {b['completion_tokens']}")
print(f"  anchors ctok {a['completion_tokens']}  -> {'same as base' if same(b,a) else 'DIFFERS from base'}")
print(f"  nostore ctok {n['completion_tokens']}  -> base:{'same' if same(b,n) else 'differs'}  anchors:{'same' if same(a,n) else 'differs'}")
print()
if same(b,a):
    print("  => INADMISSIBLE: anchors did not reproduce the defect; nostore proves nothing.")
elif same(a,n):
    print("  => SPLIT+EVAL is the cause. Storing the snapshot is irrelevant —")
    print("     discarding it changes nothing. The defect is resumption.")
elif same(b,n):
    print("  => THE SNAPSHOT COPY is the cause. The same split with no store")
    print("     reproduces the unsplit answer exactly.")
else:
    print("  => NEITHER alone: three distinct outputs, so split and store both contribute.")
PY
echo "NOSTORE PROBE DONE"
