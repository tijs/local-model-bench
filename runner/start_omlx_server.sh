#!/usr/bin/env bash
# Start an isolated, foreground oMLX server for local-model-bench.
#
# This deliberately never uses ~/.omlx, the CoCore Python environment, or
# benchmark ports owned by existing backends. The model root must already hold
# a subdirectory named exactly --served-model-id; download/staging is separate
# so a typo cannot silently fetch or serve a different artifact.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUNTIME_BIN_DEFAULT="$HOME/.local/share/local-model-bench/omlx-venv/bin/omlx"
BASE_DEFAULT="$REPO/runner/.omlx-runtime"

usage() {
  cat <<'EOF'
Usage: start_omlx_server.sh --model-dir ROOT --served-model-id ID --port PORT \
  --context-cap TOKENS --cache-mode cold|hot|ssd [options]

Options:
  --runtime-bin PATH         Isolated oMLX executable (default: ~/.local/share/local-model-bench/omlx-venv/bin/omlx)
  --base-path PATH           Isolated oMLX state root (default: runner/.omlx-runtime)
  --cache-dir PATH           Isolated paged SSD cache root (default: BASE/cache)
  --memory-guard TIER        safe|balanced|aggressive (default: safe)
  --hot-cache-max-size SIZE  Hot KV cache size for hot/ssd modes (default: 4GB)
  --ssd-cache-max-size SIZE  SSD KV cache size for ssd mode (default: 20GB)
  --log-path PATH            oMLX log directory (default: BASE/logs)
  --mtp-mode off|lightning   Explicit native MTP identity (default: off)
  --reasoning-effort LEVEL   Forced chat-template reasoning_effort, if supported
  --temperature FLOAT        Per-model coding default (default: 1.0)
  --top-p FLOAT              Per-model coding default (default: 0.95)
  --top-k INTEGER            Per-model coding default (default: 20)
  --min-p FLOAT              Per-model coding default (default: 0)
  --repetition-penalty FLOAT Per-model coding default (default: 1)
  --presence-penalty FLOAT   Per-model coding default (default: 0)
  --max-tokens INTEGER       Per-request generation cap (default: 32768)
  --dry-run                  Validate and print, but do not bind a port
EOF
}

MODEL_DIR=""
SERVED_MODEL_ID=""
PORT=""
CONTEXT_CAP=""
CACHE_MODE=""
RUNTIME_BIN="$RUNTIME_BIN_DEFAULT"
BASE_PATH="$BASE_DEFAULT"
CACHE_DIR=""
# Lifecycle control remains repository-local even when --base-path relocates
# oMLX settings.  The teardown wrapper must not have to reverse-parse config.
CONTROL_PATH="$BASE_DEFAULT"
MEMORY_GUARD="safe"
HOT_CACHE_MAX_SIZE="4GB"
SSD_CACHE_MAX_SIZE="20GB"
LOG_PATH=""
MTP_MODE="off"
REASONING_EFFORT=""
TEMPERATURE="1.0"
TOP_P="0.95"
TOP_K="20"
MIN_P="0"
REPETITION_PENALTY="1"
PRESENCE_PENALTY="0"
MAX_TOKENS="32768"
DRY_RUN=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --model-dir) MODEL_DIR="${2:?missing value}"; shift 2 ;;
    --served-model-id) SERVED_MODEL_ID="${2:?missing value}"; shift 2 ;;
    --port) PORT="${2:?missing value}"; shift 2 ;;
    --context-cap) CONTEXT_CAP="${2:?missing value}"; shift 2 ;;
    --cache-mode) CACHE_MODE="${2:?missing value}"; shift 2 ;;
    --runtime-bin) RUNTIME_BIN="${2:?missing value}"; shift 2 ;;
    --base-path) BASE_PATH="${2:?missing value}"; shift 2 ;;
    --cache-dir) CACHE_DIR="${2:?missing value}"; shift 2 ;;
    --memory-guard) MEMORY_GUARD="${2:?missing value}"; shift 2 ;;
    --hot-cache-max-size) HOT_CACHE_MAX_SIZE="${2:?missing value}"; shift 2 ;;
    --ssd-cache-max-size) SSD_CACHE_MAX_SIZE="${2:?missing value}"; shift 2 ;;
    --log-path) LOG_PATH="${2:?missing value}"; shift 2 ;;
    --mtp-mode) MTP_MODE="${2:?missing value}"; shift 2 ;;
    --reasoning-effort) REASONING_EFFORT="${2:?missing value}"; shift 2 ;;
    --temperature) TEMPERATURE="${2:?missing value}"; shift 2 ;;
    --top-p) TOP_P="${2:?missing value}"; shift 2 ;;
    --top-k) TOP_K="${2:?missing value}"; shift 2 ;;
    --min-p) MIN_P="${2:?missing value}"; shift 2 ;;
    --repetition-penalty) REPETITION_PENALTY="${2:?missing value}"; shift 2 ;;
    --presence-penalty) PRESENCE_PENALTY="${2:?missing value}"; shift 2 ;;
    --max-tokens) MAX_TOKENS="${2:?missing value}"; shift 2 ;;
    --dry-run) DRY_RUN=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "FATAL: unknown option: $1" >&2; usage >&2; exit 2 ;;
  esac
done

for field in MODEL_DIR SERVED_MODEL_ID PORT CONTEXT_CAP CACHE_MODE; do
  if [[ -z "${!field}" ]]; then
    echo "FATAL: a required launch argument is missing ($field)" >&2
    usage >&2
    exit 2
  fi
done
case "$CACHE_MODE" in cold|hot|ssd) ;; *) echo "FATAL: cache mode must be cold, hot, or ssd" >&2; exit 2 ;; esac
case "$MTP_MODE" in off|lightning) ;; *) echo "FATAL: mtp mode must be off or lightning" >&2; exit 2 ;; esac
case "$MEMORY_GUARD" in safe|balanced|aggressive) ;; *) echo "FATAL: invalid memory guard: $MEMORY_GUARD" >&2; exit 2 ;; esac
[[ "$PORT" =~ ^[0-9]+$ ]] || { echo "FATAL: port must be numeric" >&2; exit 2; }
[[ "$CONTEXT_CAP" =~ ^[0-9]+$ ]] || { echo "FATAL: context cap must be numeric" >&2; exit 2; }
[[ "$MAX_TOKENS" =~ ^[0-9]+$ ]] || { echo "FATAL: max tokens must be numeric" >&2; exit 2; }

MODEL_DIR="$(cd "$MODEL_DIR" && pwd)"
BASE_PATH="$(mkdir -p "$BASE_PATH" && cd "$BASE_PATH" && pwd)"
CONTROL_PATH="$(mkdir -p "$CONTROL_PATH" && cd "$CONTROL_PATH" && pwd)"
LOG_PATH="${LOG_PATH:-$BASE_PATH/logs}"
MODEL_PATH="$MODEL_DIR/$SERVED_MODEL_ID"

[[ -d "$MODEL_PATH" ]] || { echo "FATAL: model directory missing: $MODEL_PATH" >&2; exit 1; }
[[ -f "$MODEL_PATH/config.json" ]] || { echo "FATAL: missing config.json: $MODEL_PATH/config.json" >&2; exit 1; }
[[ -x "$RUNTIME_BIN" ]] || { echo "FATAL: isolated oMLX executable not found: $RUNTIME_BIN" >&2; exit 1; }

if (( ! DRY_RUN )) && /usr/sbin/lsof -nP -iTCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1; then
  echo "FATAL: port $PORT is already listening; refuse to attach to a stale process" >&2
  /usr/sbin/lsof -nP -iTCP:"$PORT" -sTCP:LISTEN >&2 || true
  exit 1
fi

mkdir -p "$LOG_PATH"
if [[ -z "$CACHE_DIR" ]]; then
  CACHE_DIR="$BASE_PATH/cache/$SERVED_MODEL_ID"
fi
CACHE_DIR="$(mkdir -p "$CACHE_DIR" && cd "$CACHE_DIR" && pwd)"
# Keep context/sampling policy in the isolated base path. oMLX reads this
# before model load; CLI flags below make the server/port/cache choice explicit.
"$RUNTIME_BIN" --version >/dev/null
RUNTIME_PY="$(dirname "$RUNTIME_BIN")/python"
"$RUNTIME_PY" - "$BASE_PATH/settings.json" "$BASE_PATH/model_settings.json" "$SERVED_MODEL_ID" "$CONTEXT_CAP" "$LOG_PATH" "$MTP_MODE" "$REASONING_EFFORT" "$TEMPERATURE" "$TOP_P" "$TOP_K" "$MIN_P" "$REPETITION_PENALTY" "$PRESENCE_PENALTY" "$MAX_TOKENS" "$CACHE_MODE" "$CACHE_DIR" "$HOT_CACHE_MAX_SIZE" "$SSD_CACHE_MAX_SIZE" <<'PY'
import json, sys
from pathlib import Path
settings_path = Path(sys.argv[1])
model_settings_path = Path(sys.argv[2])
(model_id, context, log_dir, mtp_mode, reasoning_effort, temperature, top_p,
 top_k, min_p, repetition_penalty, presence_penalty, max_tokens, cache_mode,
 cache_dir, hot_cache_max_size, ssd_cache_max_size) = sys.argv[3:]
context = int(context)
max_tokens = int(max_tokens)
settings_path.write_text(json.dumps({
    "version": "1.0",
    "sampling": {"max_context_window": context, "max_context_window_policy": context,
                 "max_tokens": max_tokens, "temperature": float(temperature), "top_p": float(top_p),
                 "top_k": int(top_k), "repetition_penalty": float(repetition_penalty)},
    "cache": {
        "enabled": cache_mode != "cold",
        "hot_cache_only": cache_mode == "hot",
        "ssd_cache_dir": cache_dir,
        "ssd_cache_max_size": ssd_cache_max_size,
        "hot_cache_max_size": hot_cache_max_size if cache_mode != "cold" else "0",
    },
    "logging": {"log_dir": log_dir},
}, indent=2) + "\n")
model = {
    "max_context_window": context, "max_tokens": max_tokens,
    "temperature": float(temperature), "top_p": float(top_p), "top_k": int(top_k),
    "min_p": float(min_p), "repetition_penalty": float(repetition_penalty),
    "presence_penalty": float(presence_penalty), "force_sampling": True,
    "mtp_enabled": mtp_mode == "lightning",
}
if reasoning_effort:
    model["chat_template_kwargs"] = {"reasoning_effort": reasoning_effort}
    model["forced_ct_kwargs"] = ["reasoning_effort"]
model_settings_path.write_text(json.dumps({"version": 1, "models": {model_id: model}}, indent=2) + "\n")
PY

CMD=("$RUNTIME_BIN" serve --base-path "$BASE_PATH" --model-dir "$MODEL_DIR" --no-hf-cache --host 127.0.0.1 --port "$PORT" --log-level info --memory-guard "$MEMORY_GUARD" --max-concurrent-requests 1)
case "$CACHE_MODE" in
  cold) CMD+=(--no-cache) ;;
  hot) CMD+=(--paged-ssd-cache-dir "$CACHE_DIR" --paged-ssd-cache-max-size 1MB --hot-cache-max-size "$HOT_CACHE_MAX_SIZE") ;;
  ssd) CMD+=(--paged-ssd-cache-dir "$CACHE_DIR" --paged-ssd-cache-max-size "$SSD_CACHE_MAX_SIZE" --hot-cache-max-size "$HOT_CACHE_MAX_SIZE") ;;
esac

printf 'oMLX isolated launch (cache=%s, served_model_id=%s): ' "$CACHE_MODE" "$SERVED_MODEL_ID"
printf '%q ' "${CMD[@]}"
printf '\n'
if (( DRY_RUN )); then
  exit 0
fi

printf '%s\n' "$$" > "$CONTROL_PATH/server.pid"
trap 'rm -f "$CONTROL_PATH/server.pid"' EXIT INT TERM
exec "${CMD[@]}"
