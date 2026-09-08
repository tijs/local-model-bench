#!/usr/bin/env bash
# Start an isolated Mei server for local-model-bench.
#
# Conventions: dedicated port (8024),
# dedicated logs/runtime base, pid file at BASE/server.pid, refuses to
# start when the port is already listening, and never touches the ports or
# processes of other engines. Builds the pinned Swift package on demand.
set -euo pipefail

MEI_REPO_DEFAULT="${MEI_REPO:-$HOME/projects/mei}"
RUNTIME_BASE_DEFAULT="$HOME/.local/share/local-model-bench/mei-runtime"
# Pinned-scratch default: resolves vmlx-swift from the remote fork at the
# exact Package.swift revision (91fed8be), NOT from any local clone — a
# scratch dir built once against a local-path Package.swift leaks that
# identity into every later build and dirties ~/projects/mei/Package.resolved.
BUILD_DIR_DEFAULT="$HOME/.local/share/local-model-bench/mei-build-pinned-91fed8be"

usage() {
  cat <<'EOF'
Usage: start_mei_server.sh --model-dir ROOT --served-model-id ID --port PORT \
  --context-cap TOKENS [options]

Options:
  --prefill-step-size N     Chunked prefill window (default: 512)
  --max-tokens N            Server-side generation cap (default: 32768)
  --temperature F --top-p F --top-k N --min-p F
  --emit-reasoning BOOL     Expose reasoning_content (default: true)
  --enable-thinking BOOL    Force template enable_thinking (default: none ->
                            not passed; nil = template default, which for the
                            staged Laguna-XS-2.1 chat_template.jinja is FALSE)
  --cache-reuse BOOL        In-process KV/prefix reuse (default: true)
  --kv-bits N               KV quantization bits (default: none)
  --kv-cache-dir DIR        On-disk KV cache dir for the prefix coordinator
                            (default: none -> in-memory paged tier only; the
                            qwen3_5_moe/Ornith hybrid requires this tier for
                            cross-turn reuse — cached_tokens stays 0 without it)
  --optimization-profile PROFILE  Mei optimization profile: auto|generic|ornith
                            (default: none -> not passed; Mei auto picks it.
                            generic is the Nemotron gate operating point)
  --memory-limit-bytes N    Explicit MLX allocator limit in bytes
                            (default: none -> not passed; Mei uses its own
                            default, ~1.5x the Metal recommended working set)
  --cache-limit-bytes N     MLX buffer-pool cache limit in bytes
                            (default: none -> not passed; Mei default 0 = use
                            the default limit)
  --compiled-decode BOOL    Graph-traced compiled decode (default: none -> not
                            passed; Mei default false)
  --mei-repo PATH           Mei checkout (default: ~/projects/mei)
  --runtime-base PATH       Mei runtime root (default: ~/.local/share/local-model-bench/mei-runtime)
  --build-dir PATH          SwiftPM scratch/build dir (default: .../mei-build-pinned-91fed8be)
  --dry-run                 Validate and print, but do not launch
EOF
}

MODEL_DIR=""
SERVED_MODEL_ID=""
PORT=""
CONTEXT_CAP=""
PREFILL_STEP_SIZE="512"
MAX_TOKENS="32768"
TEMPERATURE="0.6"
TOP_P="0.95"
TOP_K="20"
MIN_P=""
EMIT_REASONING="true"
ENABLE_THINKING=""
CACHE_REUSE="true"
KV_BITS=""
KV_CACHE_DIR=""
OPTIMIZATION_PROFILE=""
MEMORY_LIMIT_BYTES=""
CACHE_LIMIT_BYTES=""
COMPILED_DECODE=""
MEI_REPO="$MEI_REPO_DEFAULT"
RUNTIME_BASE="$RUNTIME_BASE_DEFAULT"
BUILD_DIR="$BUILD_DIR_DEFAULT"
DRY_RUN=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --model-dir) MODEL_DIR="${2:?missing value}"; shift 2 ;;
    --served-model-id) SERVED_MODEL_ID="${2:?missing value}"; shift 2 ;;
    --port) PORT="${2:?missing value}"; shift 2 ;;
    --context-cap) CONTEXT_CAP="${2:?missing value}"; shift 2 ;;
    --prefill-step-size) PREFILL_STEP_SIZE="${2:?missing value}"; shift 2 ;;
    --max-tokens) MAX_TOKENS="${2:?missing value}"; shift 2 ;;
    --temperature) TEMPERATURE="${2:?missing value}"; shift 2 ;;
    --top-p) TOP_P="${2:?missing value}"; shift 2 ;;
    --top-k) TOP_K="${2:?missing value}"; shift 2 ;;
    --min-p) MIN_P="${2:?missing value}"; shift 2 ;;
    --emit-reasoning) EMIT_REASONING="${2:?missing value}"; shift 2 ;;
    --enable-thinking) ENABLE_THINKING="${2:?missing value}"; shift 2 ;;
    --cache-reuse) CACHE_REUSE="${2:?missing value}"; shift 2 ;;
    --kv-bits) KV_BITS="${2:?missing value}"; shift 2 ;;
    --kv-cache-dir) KV_CACHE_DIR="${2:?missing value}"; shift 2 ;;
    --optimization-profile) OPTIMIZATION_PROFILE="${2:?missing value}"; shift 2 ;;
    --memory-limit-bytes) MEMORY_LIMIT_BYTES="${2:?missing value}"; shift 2 ;;
    --cache-limit-bytes) CACHE_LIMIT_BYTES="${2:?missing value}"; shift 2 ;;
    --compiled-decode) COMPILED_DECODE="${2:?missing value}"; shift 2 ;;
    --mei-repo) MEI_REPO="${2:?missing value}"; shift 2 ;;
    --runtime-base) RUNTIME_BASE="${2:?missing value}"; shift 2 ;;
    --build-dir) BUILD_DIR="${2:?missing value}"; shift 2 ;;
    --dry-run) DRY_RUN=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "FATAL: unknown option: $1" >&2; usage >&2; exit 2 ;;
  esac
done

for field in MODEL_DIR SERVED_MODEL_ID PORT CONTEXT_CAP; do
  if [[ -z "${!field}" ]]; then
    echo "FATAL: a required launch argument is missing ($field)" >&2
    usage >&2
    exit 2
  fi
done
[[ "$PORT" =~ ^[0-9]+$ ]] || { echo "FATAL: port must be numeric" >&2; exit 2; }
[[ "$CONTEXT_CAP" =~ ^[0-9]+$ ]] || { echo "FATAL: context cap must be numeric" >&2; exit 2; }

[[ -d "$MEI_REPO" ]] || { echo "FATAL: Mei checkout missing: $MEI_REPO" >&2; exit 1; }
[[ -f "$MEI_REPO/Package.swift" ]] || { echo "FATAL: $MEI_REPO is not a Swift package" >&2; exit 1; }
[[ -d "$MODEL_DIR" ]] || { echo "FATAL: model directory missing: $MODEL_DIR" >&2; exit 1; }
[[ -f "$MODEL_DIR/config.json" ]] || { echo "FATAL: missing config.json: $MODEL_DIR/config.json" >&2; exit 1; }

if (( ! DRY_RUN )) && /usr/sbin/lsof -nP -iTCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1; then
  echo "FATAL: port $PORT is already listening; refuse to attach to a stale process" >&2
  /usr/sbin/lsof -nP -iTCP:"$PORT" -sTCP:LISTEN >&2 || true
  exit 1
fi

BIN="$BUILD_DIR/release/mei"

# Build the argument vector BEFORE building, so --dry-run can print the exact
# launch line (with every gate control) without compiling the Swift package or
# starting a server. Only explicitly-provided values are forwarded — no default
# overrides a current config's behavior.
ARGS=(--model-dir "$MODEL_DIR" --served-model-id "$SERVED_MODEL_ID"
  --host 127.0.0.1 --port "$PORT"
  --context-cap "$CONTEXT_CAP" --max-tokens "$MAX_TOKENS"
  --prefill-step-size "$PREFILL_STEP_SIZE"
  --temperature "$TEMPERATURE" --top-p "$TOP_P" --top-k "$TOP_K"
  --emit-reasoning "$EMIT_REASONING" --cache-reuse "$CACHE_REUSE")
[[ -n "$MIN_P" ]] && ARGS+=(--min-p "$MIN_P")
[[ -n "$ENABLE_THINKING" ]] && ARGS+=(--enable-thinking "$ENABLE_THINKING")
[[ -n "$KV_BITS" ]] && ARGS+=(--kv-bits "$KV_BITS")
[[ -n "$KV_CACHE_DIR" ]] && ARGS+=(--kv-cache-dir "$KV_CACHE_DIR")
[[ -n "$OPTIMIZATION_PROFILE" ]] && ARGS+=(--optimization-profile "$OPTIMIZATION_PROFILE")
[[ -n "$MEMORY_LIMIT_BYTES" ]] && ARGS+=(--memory-limit-bytes "$MEMORY_LIMIT_BYTES")
[[ -n "$CACHE_LIMIT_BYTES" ]] && ARGS+=(--cache-limit-bytes "$CACHE_LIMIT_BYTES")
[[ -n "$COMPILED_DECODE" ]] && ARGS+=(--compiled-decode "$COMPILED_DECODE")

printf 'mei isolated launch: '
printf '%q ' "$BIN" "${ARGS[@]}"
printf '\n'
if (( DRY_RUN )); then
  exit 0
fi

mkdir -p "$RUNTIME_BASE" "$RUNTIME_BASE/logs" "$BUILD_DIR"
LOG_DIR="$RUNTIME_BASE/logs"
PID_FILE="$RUNTIME_BASE/server.pid"

echo "mei: building (release, scratch: $BUILD_DIR) ..."
"${MEI_SWIFT:-swift}" build -c release --scratch-path "$BUILD_DIR" --package-path "$MEI_REPO" \
  > "$LOG_DIR/build.log" 2>&1 || {
  echo "FATAL: swift build failed — see $LOG_DIR/build.log" >&2
  exit 1
}
[[ -x "$BIN" ]] || { echo "FATAL: built binary missing at $BIN" >&2; exit 1; }
bash "$MEI_REPO/scripts/prepare_metallib.sh" "$BUILD_DIR/release" || { echo "FATAL: missing Metal kernel library" >&2; exit 1; }

"$BIN" "${ARGS[@]}" >> "$LOG_DIR/server.log" 2>&1 &
SERVER_PID=$!
printf '%s\n' "$SERVER_PID" > "$PID_FILE"
trap 'rm -f "$PID_FILE"' EXIT INT TERM
wait "$SERVER_PID"
