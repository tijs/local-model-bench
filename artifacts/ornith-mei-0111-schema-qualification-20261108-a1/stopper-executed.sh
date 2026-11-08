#!/usr/bin/env bash
# Stop only the Mei process launched from this benchmark's isolated runtime
# base. Never touches CoCore, Mara, vllm-mlx, llama.cpp, or oMLX servers.
set -euo pipefail

RUNTIME_BASE="${MEI_RUNTIME_BASE:-$HOME/.local/share/local-model-bench/mei-runtime}"
PID_FILE="$RUNTIME_BASE/server.pid"
TIMEOUT=30

while [[ $# -gt 0 ]]; do
  case "$1" in
    --runtime-base) RUNTIME_BASE="${2:?missing value}"; shift 2 ;;
    --timeout) TIMEOUT="${2:?missing value}"; shift 2 ;;
    -h|--help) echo "Usage: stop_mei_server.sh [--runtime-base PATH] [--timeout SECONDS]"; exit 0 ;;
    *) echo "FATAL: unknown option: $1" >&2; exit 2 ;;
  esac
done

PID_FILE="$RUNTIME_BASE/server.pid"
[[ -f "$PID_FILE" ]] || { echo "No isolated Mei pid file at $PID_FILE"; exit 0; }
PID="$(tr -d '[:space:]' < "$PID_FILE")"
[[ "$PID" =~ ^[0-9]+$ ]] || { echo "FATAL: invalid isolated Mei pid file: $PID_FILE" >&2; exit 1; }

if ! kill -0 "$PID" 2>/dev/null; then
  rm -f "$PID_FILE"
  echo "Isolated Mei PID $PID is already stopped."
  exit 0
fi
COMMAND="$(ps -p "$PID" -o command= 2>/dev/null || true)"
if [[ "$COMMAND" != *"mei"* ]]; then
  echo "FATAL: pid $PID from $PID_FILE is not a Mei process; refusing to kill it" >&2
  exit 1
fi

kill -TERM "$PID"
for _ in $(seq 1 "$TIMEOUT"); do
  if ! kill -0 "$PID" 2>/dev/null; then
    rm -f "$PID_FILE"
    echo "Stopped isolated Mei PID $PID."
    exit 0
  fi
  if [[ "$(ps -o stat= -p "$PID" 2>/dev/null)" == Z* ]]; then
    rm -f "$PID_FILE"
    echo "Stopped isolated Mei PID $PID (awaiting parent reap)."
    exit 0
  fi
  sleep 1
done
kill -KILL "$PID" 2>/dev/null || true
rm -f "$PID_FILE"
echo "Force-stopped isolated Mei PID $PID after ${TIMEOUT}s."
