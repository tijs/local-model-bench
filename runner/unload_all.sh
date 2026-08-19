#!/usr/bin/env bash
# Kill locally-running model backends before loading a benchmark candidate.
# Deliberately does NOT touch the hermes gateway itself (hermes_cli.main
# gateway run) — that's the orchestration layer we still need running.
#
# NOT YET VALIDATED LIVE. Run this supervised the first time and confirm:
#   - cocore's engine actually dies cleanly (check for orphaned parent proc)
#   - nothing auto-respawns it
# before trusting it in an unattended run.
set -euo pipefail

echo "Killing cocore inference engine..."
pkill -f "cocore_inference_server.py" || true
pkill -f "vllm_mlx.server" || true

echo "Killing llama.cpp server (if running)..."
pkill -f "llama-server" || true

sleep 1
echo "Remaining candidate-backend processes (should be empty):"
ps aux | grep -iE "cocore_inference_server|vllm_mlx.server|llama-server" | grep -v grep || echo "  (none)"
