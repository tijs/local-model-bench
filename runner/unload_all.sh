#!/usr/bin/env bash
# Stop known candidate listeners on configured benchmark ports only.
# No application runtime, profile, LaunchAgent, or CoCore lifecycle is managed.
# The retired lifecycle source is preserved under runner/legacy/.
set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Ports this benchmark actually uses: every raw_port/proxy_port declared
# in configs/*/*.yaml, plus the well-known defaults, deduplicated. Parsed
# with grep rather than a YAML library so this script stays dependency-free
# and usable when the uv environment isn't available.
bench_ports() {
  {
    grep -rhoE '^[[:space:]]*(raw_port|proxy_port):[[:space:]]*[0-9]+' \
      "$REPO_ROOT"/configs/*/*.yaml 2>/dev/null | grep -oE '[0-9]+'
    printf '8012\n8015\n8020\n'   # vllm-mlx / bench proxy / isolated oMLX
  } | sort -un
}

# Commands we are willing to kill when found bound to one of those ports.
BACKEND_CMD_PATTERN='vllm_mlx\.server|vllm-mlx|llama-server|bench_local_proxy\.py|omlx'

stop_port() {
  local port="$1" pid cmd
  for pid in $(lsof -nP -iTCP:"$port" -sTCP:LISTEN -t 2>/dev/null | sort -un); do
    cmd="$(ps -o command= -p "$pid" 2>/dev/null)"
    [ -z "$cmd" ] && continue
    if ! printf '%s' "$cmd" | grep -qE "$BACKEND_CMD_PATTERN"; then
      echo "  port $port: pid $pid is not a known benchmark backend, leaving it alone:"
      echo "    $cmd"
      continue
    fi
    echo "  port $port: stopping pid $pid ($(printf '%.90s' "$cmd"))"
    kill -TERM "$pid" 2>/dev/null || true
    for _ in 1 2 3 4 5 6 7 8 9 10; do
      kill -0 "$pid" 2>/dev/null || break
      sleep 1
    done
    kill -0 "$pid" 2>/dev/null && kill -9 "$pid" 2>/dev/null || true
  done
}

if [ "${1:-}" = "--list-ports" ]; then
  # Inspection hook: prints the ports this script would act on, and
  # changes nothing.
  bench_ports
  exit 0
fi

# Lets runner/tests/test_unload_all_sh.py `source` this file to exercise
# bench_ports/stop_port directly without running any of the teardown
# below. `return` when sourced, `exit` when somehow run directly.
if [ "${BENCH_UNLOAD_DEFINE_ONLY:-0}" = "1" ]; then
  return 0 2>/dev/null || exit 0
fi

echo "--- Freeing this benchmark's configured ports ---"
# The problem the old code solved (and must keep solving): a stale process
# keeps answering on a port a new one cannot bind, silently serving the
# WRONG model to a request that looks fine — hit twice on 2026-08-20. The
# port-derived approach addresses that directly and by construction, since
# "still bound to the port" IS the failure condition, and it covers every
# invocation style (`python -m vllm_mlx.server`, `vllm-mlx serve`, a uv
# wrapper, ...) without needing to enumerate them.
for port in $(bench_ports); do
  stop_port "$port"
done

if [ "${BENCH_UNLOAD_FORCE:-0}" = "1" ]; then
  # Opt-in escape hatch: a stale engine holding GPU memory without
  # listening on any port. Scoped to this user's own processes; still
  # capable of hitting an unrelated checkout's server, which is exactly
  # why it is no longer the default.
  echo "--- BENCH_UNLOAD_FORCE=1: broad pattern sweep (may hit unrelated processes) ---"
  for _ in 1 2 3; do
    pids=$(pgrep -U "$(id -u)" -f "vllm_mlx.server|vllm-mlx serve|vllm-mlx|llama-server|bench_local_proxy.py" || true)
    [ -z "$pids" ] && break
    echo "$pids" | xargs kill -9 2>/dev/null || true
    sleep 2
  done
fi

sleep 1
echo "--- Remaining candidate-backend processes (should be empty) ---"
ps aux | grep -iE "vllm_mlx.server|vllm-mlx|llama-server|bench_local_proxy" | grep -v grep || echo "  (none)"
