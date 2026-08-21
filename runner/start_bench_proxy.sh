#!/usr/bin/env bash
# Starts local-model-bench's own tool-call-parsing proxy (bench_local_proxy.py)
# in the background. Always use this — not the fitness profile's shared
# mara_local_proxy.py on 8013, which filters the tools array to its own
# allowlist (see bench_local_proxy.py's module docstring for why this
# matters).
#
# Usage:
#   start_bench_proxy.sh [upstream_port] [proxy_port] [tool_call_parser]
# Defaults: upstream=8012 (vllm_mlx.server), proxy=8015, parser=lfm
set -euo pipefail

UPSTREAM_PORT="${1:-8012}"
PROXY_PORT="${2:-8015}"
PARSER="${3:-lfm}"
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# Matches run_bench.py/run_fixture_suite.py's own naming (adversarial
# review finding L-4, remaining half) — this used to be
# bench_local_proxy_{port}.log, a different name than either of those two
# files use/reference, so a user following an error message from
# run_fixture_suite.py pointing at "bench_proxy_{port}.log" would find
# nothing if they'd started the proxy via this script instead.
LOG_FILE="/tmp/bench_proxy_${PROXY_PORT}.log"

EXPECTED_UPSTREAM="http://127.0.0.1:${UPSTREAM_PORT}"
# Parses /healthz's JSON and compares tool_call_parser/upstream before
# reusing it (3rd adversarial review, finding CR3-17) — this used to
# early-exit on a bare 200, the same identity gap run_bench.py's own
# assert_proxy_matches() exists to close for its own proxy-launch path.
# Confirmed live: starting a proxy for upstream=19012/parser=lfm, then
# re-invoking this script for a DIFFERENT upstream=19099/parser=hermes on
# the same port, printed "Already running and healthy" and left the
# stale lfm/19012 proxy running untouched — a leftover proxy from a
# different config would have been silently reused instead of restarted
# for the config actually being launched now.
HEALTH_JSON="$(curl -s -m 2 "http://127.0.0.1:${PROXY_PORT}/healthz" 2>/dev/null || true)"
if [ -n "${HEALTH_JSON}" ]; then
  ACTUAL_PARSER="$(echo "${HEALTH_JSON}" | jq -r '.tool_call_parser // empty' 2>/dev/null || true)"
  ACTUAL_UPSTREAM="$(echo "${HEALTH_JSON}" | jq -r '.upstream // empty' 2>/dev/null || true)"
  if [ "${ACTUAL_PARSER}" = "${PARSER}" ] && [ "${ACTUAL_UPSTREAM}" = "${EXPECTED_UPSTREAM}" ]; then
    echo "Already running and healthy on port ${PROXY_PORT} (parser=${PARSER} upstream=${EXPECTED_UPSTREAM})."
    exit 0
  fi
  echo "Proxy on port ${PROXY_PORT} is healthy but points at parser=${ACTUAL_PARSER:-?} upstream=${ACTUAL_UPSTREAM:-?}, expected parser=${PARSER} upstream=${EXPECTED_UPSTREAM} — restarting it for this config instead of reusing it."
fi

pkill -f "runner/bench_local_proxy.py" 2>/dev/null || true
sleep 1

BENCH_PROXY_UPSTREAM="http://127.0.0.1:${UPSTREAM_PORT}" \
BENCH_PROXY_PORT="${PROXY_PORT}" \
BENCH_TOOL_PARSER="${PARSER}" \
nohup "${BENCH_PYTHON:-/Users/tijs/.cocore/python/bin/python}" "${REPO_DIR}/runner/bench_local_proxy.py" \
  > "${LOG_FILE}" 2>&1 &
disown

sleep 2
if curl -s -m 5 "http://127.0.0.1:${PROXY_PORT}/healthz" > /dev/null 2>&1; then
  echo "bench_local_proxy started: upstream=127.0.0.1:${UPSTREAM_PORT} proxy=127.0.0.1:${PROXY_PORT} parser=${PARSER}"
  echo "log: ${LOG_FILE}"
else
  echo "FAILED to start — check ${LOG_FILE}" >&2
  tail -20 "${LOG_FILE}" >&2
  exit 1
fi
