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
REPO="${1:?usage: unit_tests_gate.sh <mei-repo>}"
cd "$REPO" || exit 1
echo "UNIT TEST GATE repo=$REPO branch=$(git branch --show-current) head=$(git rev-parse --short HEAD)"
swift test 2>&1 | tail -40
# `swift test | tail` would otherwise report tail's status, not the tests'.
status=${PIPESTATUS[0]}
echo "UNIT TEST GATE $([ "$status" -eq 0 ] && echo PASS || echo FAIL) (exit $status)"
exit "$status"
