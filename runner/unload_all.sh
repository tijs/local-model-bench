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
set -uo pipefail

echo "--- Stopping cocore (also takes this machine offline on cocore.dev for the duration) ---"
cocore agent models set "" 2>&1 | grep -v "pinned process signing identity" || true
sleep 3

echo "--- Stopping hermes's independent mara-mlx LaunchAgent (fitness profile's local fallback) ---"
launchctl bootout gui/501/ai.hermes.mara-mlx 2>/dev/null || true
sleep 1

echo "--- Cleaning up any orphaned processes (cocore's own bounce leaves one) ---"
# Matches every server invocation style seen this session: the old
# `python -m vllm_mlx.server` module form AND the newer `vllm-mlx serve`
# CLI entry point (added with the 0.4.1 upgrade, 2026-08-20) — a plain
# pkill -f "vllm_mlx.server" misses the latter, which bit this session
# twice (a stale process kept answering on a port a new one couldn't
# bind, silently serving the WRONG model to a request that looked fine).
for _ in 1 2 3; do
  pids=$(pgrep -f "vllm_mlx.server|vllm-mlx serve|vllm-mlx|cocore_inference_server.py" || true)
  [ -z "$pids" ] && break
  echo "$pids" | xargs kill -9 2>/dev/null || true
  sleep 2
done

pkill -9 -f "llama-server" 2>/dev/null || true
pkill -9 -f "bench_local_proxy.py" 2>/dev/null || true

sleep 1
echo "--- Remaining candidate-backend processes (should be empty) ---"
ps aux | grep -iE "cocore_inference_server|vllm_mlx.server|vllm-mlx|llama-server|bench_local_proxy" | grep -v grep || echo "  (none)"
