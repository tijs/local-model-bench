#!/usr/bin/env bash
# Restores the Hermes local fallback that unload_all.sh stops, after a
# benchmark session is done: the ai.hermes.mara-mlx LaunchAgent (the
# fitness profile's local-model fallback). MANUAL, user-invoked only —
# no benchmark run invokes this script automatically.
#
# CoCore remains INTENTIONALLY OFF: this script does NOT start or mutate
# CoCore, does not invoke `cocore`, and does not bootstrap its LaunchAgent.
# Bringing CoCore back is an explicit manual user decision outside this
# benchmark, never an automatic step. (Pre-2026-09-14 versions reloaded
# LFM2.5-2.6B and re-bootstrapped the cocore agent; that contract is
# retired — see AGENTS.md and the git history.)
set -uo pipefail

echo "--- Restoring hermes's mara-mlx LaunchAgent (fitness profile's local fallback) ---"
# gui/$(id -u), not a hardcoded gui/501 — same fix as unload_all.sh (3rd
# adversarial review, low finding).
launchctl bootstrap "gui/$(id -u)" ~/Library/LaunchAgents/ai.hermes.mara-mlx.plist 2>&1 || true

sleep 3
echo "--- Verifying ---"
if launchctl print "gui/$(id -u)/ai.hermes.mara-mlx" >/dev/null 2>&1; then
  echo "  ai.hermes.mara-mlx is loaded."
else
  echo "  ai.hermes.mara-mlx is NOT loaded — check the plist / launchd manually."
fi
echo "  CoCore remains intentionally off (not started, not restored)."
ps aux | grep -E "vllm_mlx.server|llama-server" | grep -v grep || echo "  (no benchmark model processes running)"