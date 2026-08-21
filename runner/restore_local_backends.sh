#!/usr/bin/env bash
# Restores both local backends that unload_all.sh stops, after a benchmark
# session is done. Run this when you're finished testing, not automatically —
# cocore's model reload takes real RAM+time, and you don't want it fighting
# a benchmark run for the same resources.
set -uo pipefail

echo "--- Restoring cocore (LFM2.5-2.6B, resumes cocore.dev network serving) ---"
cocore agent models set "LiquidAI/LFM2.5-2.6B-MLX-bf16" 2>&1 | grep -v "pinned process signing identity" || true
sleep 2
# The models-set bounce fully unloads the LaunchAgent rather than reloading
# it cleanly (observed live 2026-08-19) — re-bootstrap explicitly.
launchctl bootstrap "gui/$(id -u)" ~/Library/LaunchAgents/dev.cocore.provider.plist 2>&1 || true
sleep 2

echo "--- Restoring hermes's mara-mlx LaunchAgent (fitness profile's local fallback) ---"
# gui/$(id -u), not a hardcoded gui/501 — same fix as unload_all.sh (3rd
# adversarial review, low finding).
launchctl bootstrap "gui/$(id -u)" ~/Library/LaunchAgents/ai.hermes.mara-mlx.plist 2>&1 || true

sleep 3
echo "--- Verifying ---"
cocore agent active 2>&1 | tail -1
ps aux | grep -E "vllm_mlx.server|cocore_inference_server" | grep -v grep || echo "  (no model processes running — something didn't restart, check manually)"
