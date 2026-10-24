#!/usr/bin/env bash
# Compatibility preflight for the isolated "bench" Hermes profile.
# run_fixture_suite.py starts a new `hermes chat` (no resume/continue) and
# exports telemetry by that run's session ID. Deleting stored sessions is
# not needed for isolation. Preserve all persisted profile state, including
# memories, operational logs, and scheduled jobs; never create missing dirs.
set -euo pipefail

PROFILE_DIR="${HOME:?HOME must be set}/.hermes/profiles/bench"

# Refuse links before following any profile-path component or sessions target,
# including dangling links. This helper must not operate on another profile.
for path in "$HOME" "$HOME/.hermes" "$HOME/.hermes/profiles" "$PROFILE_DIR" "$PROFILE_DIR/sessions"; do
  if [ -L "$path" ]; then
    echo "Refusing symlinked bench profile path: $path" >&2
    exit 1
  fi
done

if [ ! -d "$PROFILE_DIR" ]; then
  echo "bench profile not found at $PROFILE_DIR" >&2
  exit 1
fi

if [ -e "$PROFILE_DIR/sessions" ] && [ ! -d "$PROFILE_DIR/sessions" ]; then
  echo "bench sessions path is not a directory: $PROFILE_DIR/sessions" >&2
  exit 1
fi

echo "Bench profile checked; sessions, memories, logs, and cron preserved."
