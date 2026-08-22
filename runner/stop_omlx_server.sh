#!/usr/bin/env bash
# Stop only the oMLX process launched from this benchmark's isolated base path.
# Never touches CoCore, Mara, vllm-mlx, llama.cpp, or any app-managed oMLX.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BASE_PATH="$REPO/runner/.omlx-runtime"
TIMEOUT=30

while [[ $# -gt 0 ]]; do
  case "$1" in
    --base-path) BASE_PATH="${2:?missing value}"; shift 2 ;;
    --timeout) TIMEOUT="${2:?missing value}"; shift 2 ;;
    -h|--help) echo "Usage: stop_omlx_server.sh [--base-path PATH] [--timeout SECONDS]"; exit 0 ;;
    *) echo "FATAL: unknown option: $1" >&2; exit 2 ;;
  esac
done

PID_FILE="$BASE_PATH/server.pid"
[[ -f "$PID_FILE" ]] || { echo "No isolated oMLX pid file at $PID_FILE"; exit 0; }
PID="$(tr -d '[:space:]' < "$PID_FILE")"
[[ "$PID" =~ ^[0-9]+$ ]] || { echo "FATAL: invalid isolated oMLX pid file: $PID_FILE" >&2; exit 1; }
if ! kill -0 "$PID" 2>/dev/null; then
  rm -f "$PID_FILE"
  echo "Isolated oMLX PID $PID is already stopped."
  exit 0
fi
COMMAND="$(ps -p "$PID" -o command= 2>/dev/null || true)"
if [[ "$COMMAND" != *"omlx"* ]]; then
  echo "FATAL: pid $PID from $PID_FILE is not an oMLX process; refusing to kill it" >&2
  exit 1
fi
kill -TERM "$PID"
for _ in $(seq 1 "$TIMEOUT"); do
  if ! kill -0 "$PID" 2>/dev/null; then
    rm -f "$PID_FILE"
    echo "Stopped isolated oMLX PID $PID."
    exit 0
  fi
  # A child launched by the acceptance orchestrator can already be a zombie:
  # kill -0 remains true until its parent reaps it, so waiting here would
  # deadlock the parent for the entire timeout on every sequential model.
  if [[ "$(ps -o stat= -p "$PID" 2>/dev/null)" == Z* ]]; then
    rm -f "$PID_FILE"
    echo "Stopped isolated oMLX PID $PID (awaiting parent reap)."
    exit 0
  fi
  sleep 1
done
kill -KILL "$PID" 2>/dev/null || true
rm -f "$PID_FILE"
echo "Force-stopped isolated oMLX PID $PID after ${TIMEOUT}s."
