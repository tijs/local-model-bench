#!/bin/bash
set -euo pipefail
prep=$1
core=$2
queued=$3
wait_for_exit() {
  local pid=$1 marker=$2 current
  while true; do
    current=$(ps -p "$pid" -o lstart=,command= || true)
    test -n "$current" || break
    test "$current" = "$marker" || { echo "PID identity changed: $pid"; return 1; }
    sleep 10
  done
}
wait_for_exit 45274 "$4"
wait_for_exit 46941 "$5"
test -s "$prep/comparison.json"
test "$(sysctl -n kern.memorystatus_vm_pressure_level)" = 1
if lsof -nP -iTCP:8017 -iTCP:8024 -sTCP:LISTEN; then
  echo 'Benchmark port still occupied'
  exit 1
fi
test "$(git -C "$core" rev-parse HEAD)" = b06cc4dc5af50e281b1b6309b2f7b79719fa9427
test -z "$(git -C "$core" status --porcelain)"
shasum -a 256 "$queued/screen.cpp" "$core/mlx/config.cpp" > "$queued/inputs.sha256"
xcrun clang++ -std=c++20 -O3 -DNDEBUG -DMLX_STATIC -I "$core" \
  "$queued/screen.cpp" "$core/mlx/config.cpp" -o "$queued/config_lookup_screen" \
  > "$queued/build.log" 2>&1
"$queued/config_lookup_screen" > "$queued/lookup.jsonl"
printf 'Completed isolated config lookup screen\n'
