#!/bin/bash
# Unit-test gate: `swift test` on the Mei checkout that will be served.
# usage: unit_tests_gate.sh <mei-repo>
#
# Why this exists. On 2026-09-11 the 0.4.2 branch was RED:
# testOrnithMoeModelKeepsKVCacheDirEmptyDefault asserted kvCacheDir == "" with
# the comment "Ornith behavior preserved: no implicit disk-KV default", which
# is the exact contract f1ba4af deliberately reversed when qwen3_5_moe joined
# diskKVRequiredModelTypes. The test was never updated. None of the other gates
# runs unit tests, and the release runbook did not either, so it would have
# shipped. It was caught only incidentally, by an unrelated build.
#
# Scope: the NON-METAL unit suites only. MeiAcceptanceTests is excluded on
# purpose — it drives a live server at MEI_ACCEPTANCE_BASE_URL and needs a
# provisioned mlx.metallib, so a bare `swift test` fails with connection-refused
# and "Failed to load the default metallib" even when the code is perfectly
# fine. Those behaviours are already covered against a real server by
# runner/probe_mei.py and the fidelity/C1 gates; duplicating them here would
# only produce a gate that is red for environmental reasons and therefore
# ignored.
REPO="${1:?usage: unit_tests_gate.sh <mei-repo>}"
cd "$REPO" || exit 1
echo "UNIT TEST GATE repo=$REPO branch=$(git branch --show-current) head=$(git rev-parse --short HEAD)"
# QuantizedRotatingKVCacheTests is excluded for the same reason as the
# acceptance tests: it allocates real MLX arrays and dies with "Failed to load
# the default metallib" unless scripts/prepare_metallib.sh has provisioned one
# next to the test binary. It is a genuine test, just not a non-Metal one.
SUITES=(ServerConfigParsingTests OpenAITypesTests ToolArgumentNormalizerTests
        SSMAnchorBoundariesTests CacheRestoreTrackerTests
        RouterSSEToolCallIndexingTests)
status=0
for suite in "${SUITES[@]}"; do
  out=$(swift test --filter "$suite" 2>&1)
  line=$(echo "$out" | grep -E "Executed [0-9]+ tests" | tail -1)
  if echo "$out" | grep -q "with 0 failures"; then
    echo "  PASS $suite — ${line:-no tests matched}"
  else
    echo "  FAIL $suite"
    echo "$out" | grep -E "error:" | head -3
    status=1
  fi
done
echo "UNIT TEST GATE $([ "$status" -eq 0 ] && echo PASS || echo FAIL) (exit $status)"
exit "$status"
