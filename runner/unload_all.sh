#!/usr/bin/env bash
# Properly stop every local model backend before loading a benchmark
# candidate — validated live 2026-08-19. Two INDEPENDENT supervisors were
# found keeping vllm_mlx.server alive on port 8012, and both must be stopped
# the right way (not pkill, which just gets fought and respawned):
#
#   1. cocore's own daemon (`cocore agent serve`, launchd job
#      dev.cocore.provider) — stop via `cocore agent models set ""`, which
#      also updates cocore's public network provider record so the advisor
#      stops routing requests here. This ALSO fully unloads the LaunchAgent
#      (more than just "bouncing" it, despite the tool's own description),
#      so a leftover orphan process needs an explicit kill after.
#   2. hermes's OWN separate LaunchAgent for the fitness profile's local
#      fallback (ai.hermes.mara-mlx) — stop via `launchctl bootout`, the
#      correct way to unload a LaunchAgent (not pkill, which just races
#      launchd's KeepAlive and loses).
#
# Deliberately does NOT touch the hermes gateway itself, or the fitness
# profile's mara_local_proxy.py (harmless when idle with no backend) — only
# the model-serving engines.
#
# IMPORTANT: cocore's serving is visible on the cocore.dev network (paired
# ATProto identity). Running this takes the machine offline as a compute
# provider there for as long as the benchmark run lasts. See restore_all.sh
# to bring everything back after.
#
# Process termination is PORT-DERIVED, not name-derived (improvement plan,
# M4). `pkill -9 -f "llama-server"` matches on a command-line substring
# across the whole machine: another checkout's llama-server, an unrelated
# vllm-mlx serving something that has nothing to do with this benchmark,
# even a shell whose argv happens to contain the string. This script's
# actual job is narrower — free the ports this benchmark's configs bind —
# so it asks the OS which PID is listening on each configured port and
# stops exactly those, with a command-line sanity check before killing.
#
# `BENCH_UNLOAD_FORCE=1` restores the old broad pattern sweep, for the
# case a stale engine is holding GPU memory without listening anywhere.
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
BACKEND_CMD_PATTERN='vllm_mlx\.server|vllm-mlx|llama-server|cocore_inference_server\.py|bench_local_proxy\.py|omlx'

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

echo "--- Stopping cocore (also takes this machine offline on cocore.dev for the duration) ---"
cocore agent models set "" 2>&1 | grep -v "pinned process signing identity" || true
sleep 3

echo "--- Stopping hermes's independent mara-mlx LaunchAgent (fitness profile's local fallback) ---"
# gui/$(id -u), not a hardcoded gui/501 (3rd adversarial review, low
# finding, same spirit as M8's fix for the hardcoded cocore python path):
# 501 happens to be this machine's uid, but nothing computed it — a
# hardcoded launchctl domain target is exactly the kind of
# machine-specific fragility M8 fixed elsewhere.
launchctl bootout "gui/$(id -u)/ai.hermes.mara-mlx" 2>/dev/null || true
sleep 1

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
    pids=$(pgrep -U "$(id -u)" -f "vllm_mlx.server|vllm-mlx serve|vllm-mlx|cocore_inference_server.py|llama-server|bench_local_proxy.py" || true)
    [ -z "$pids" ] && break
    echo "$pids" | xargs kill -9 2>/dev/null || true
    sleep 2
  done
fi

sleep 1
echo "--- Remaining candidate-backend processes (should be empty) ---"
ps aux | grep -iE "cocore_inference_server|vllm_mlx.server|vllm-mlx|llama-server|bench_local_proxy" | grep -v grep || echo "  (none)"
