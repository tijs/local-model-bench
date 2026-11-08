#!/bin/bash
set -euo pipefail
repo=$1
prep=$2
core=$3
build=$4
queued=$5
marker=$6
cd "$repo"
printf 'WAIT for full timing supervisor PID 45274\n'
while true; do
  live=$(ps -p 45274 -o lstart=,command= || true)
  test -n "$live" || break
  test "$live" = "$marker" || { echo 'Timing PID identity changed'; exit 1; }
  sleep 10
done
test -s "$prep/COMPARISON.md"
test -s "$prep/comparison.json"
test "$(sysctl -n kern.memorystatus_vm_pressure_level)" = 1
if lsof -nP -iTCP:8017 -iTCP:8024 -sTCP:LISTEN; then
  echo 'Benchmark port occupied after timing campaign'; exit 1
fi
test "$(git -C "$core" rev-parse HEAD)" = b06cc4dc5af50e281b1b6309b2f7b79719fa9427
test -z "$(git -C "$core" status --porcelain)"
shasum -a 256 -c "$queued/pins.sha256"
printf 'START Gemma window diagnostics\n'
xcrun clang++ -std=c++20 -O3 -DNDEBUG -DMLX_STATIC -I "$core" \
  "$queued/screen.cpp" "$build/jaccl/libjaccl.a" "$build/libmlx.a" \
  -framework Metal -framework Foundation -framework QuartzCore \
  -framework IOKit -framework Accelerate "$build/mlx/io/libgguflib.a" \
  -o "$queued/gemma_window_screen" > "$queued/build.log" 2>&1
diagnostic_exit=0
"$queued/gemma_window_screen" "$build/mlx/backend/metal/kernels/mlx.metallib" --diagnostics \
  > "$queued/diagnostics.jsonl" 2> "$queued/diagnostics.stderr" || diagnostic_exit=$?
native_exit=0
"$queued/gemma_window_screen" "$build/mlx/backend/metal/kernels/mlx.metallib" --native-only \
  > "$queued/native-only.jsonl" 2> "$queued/native-only.stderr" || native_exit=$?
printf '{"diagnostics_exit":%s,"native_only_exit":%s}\n' "$diagnostic_exit" "$native_exit" > "$queued/outcome.json"
if test "$native_exit" = 0; then
  uv run --locked python "$queued/summarize.py" "$queued/native-only.jsonl" --native-only \
    > "$queued/native-only-summary.json"
fi
printf 'Finished Gemma window diagnostics: diagnostic=%s native=%s\n' "$diagnostic_exit" "$native_exit"
test "$diagnostic_exit" = 0 && test "$native_exit" = 0
