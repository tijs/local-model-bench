#!/usr/bin/env bash
# Resets the isolated "bench" hermes profile's session/memory state.
# Run this before starting a new candidate model's test batch, so nothing
# from a previous model's sessions can leak in. memory_enabled/
# user_profile_enabled are already off in the profile's config.yaml, but
# past session transcripts still accumulate on disk — clear those too for a
# true fresh start (and to avoid growing disk usage over many benchmark
# runs).
set -euo pipefail

PROFILE_DIR="$HOME/.hermes/profiles/bench"

if [ ! -d "$PROFILE_DIR" ]; then
  echo "bench profile not found at $PROFILE_DIR" >&2
  exit 1
fi

echo "Clearing bench profile session/memory state..."
rm -rf "$PROFILE_DIR/sessions" "$PROFILE_DIR/memories" "$PROFILE_DIR/logs" "$PROFILE_DIR/cron"
mkdir -p "$PROFILE_DIR/sessions" "$PROFILE_DIR/memories" "$PROFILE_DIR/logs"

echo "Done. bench profile is fresh."
