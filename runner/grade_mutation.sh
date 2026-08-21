#!/usr/bin/env bash
# Grades a test-writing task by mutation kill rate: the agent's own test file
# must (1) pass against the real, correct implementation, and (2) fail
# against every mutant (a pre-written, deliberately-bugged swap of the
# implementation file). This is the standard rigorous way to score
# "write tests for X" tasks — an empty or trivial test file passes (1) but
# kills zero mutants, so it can't get a free pass.
#
# Usage:
#   grade_mutation.sh <run-dir> <source-file-rel-to-run-dir> \
#       <baseline-test-command> <cwd-rel-to-run-dir> <mutant-file-1> [<mutant-file-2> ...]
#
# <cwd-rel-to-run-dir> is where <baseline-test-command> is actually run from
# (e.g. "rust" for a Cargo project living under run-dir/rust/) — added
# 2026-08-21 after finding this script always ran the test command from
# run-dir itself, which only ever "worked" by never being exercised: no
# test-writing task had ever run against a live model before this, so a
# fixture whose Cargo.toml/deno.json/package.json lives in a subdirectory of
# run-dir (every fixture in this repo) would fail with "could not find
# Cargo.toml" before ever reaching a real pass/fail on the agent's tests.
#
# Exit code 0 = task passed (baseline command succeeded AND every mutant was
# killed). Exit code 1 = failed. Prints a one-line summary either way.
set -uo pipefail

run_dir="$1"; shift
source_file="$1"; shift
test_command="$1"; shift
test_cwd="$1"; shift
mutants=("$@")

if [ ${#mutants[@]} -eq 0 ]; then
  echo "grade_mutation: no mutant files given" >&2
  exit 2
fi

full_source="$run_dir/$source_file"
if [ ! -f "$full_source" ]; then
  echo "grade_mutation: source file not found: $full_source" >&2
  exit 2
fi
full_test_cwd="$run_dir/$test_cwd"
if [ ! -d "$full_test_cwd" ]; then
  echo "grade_mutation: test cwd not found: $full_test_cwd" >&2
  exit 2
fi

backup=$(mktemp)
# Per-process-unique log paths (adversarial review finding L-4) — the
# previous fixed /tmp/grade_mutation_{baseline,mutant}.log names would
# collide if two grading runs ever overlapped (e.g. --trials running
# concurrently, or two configs' mutation tasks racing).
baseline_log=$(mktemp)
mutant_log=$(mktemp)
cleanup() { cp "$backup" "$full_source"; rm -f "$backup" "$baseline_log" "$mutant_log"; }
trap cleanup EXIT

echo "== baseline (correct implementation) =="
if ! (cd "$full_test_cwd" && eval "$test_command") > "$baseline_log" 2>&1; then
  echo "FAIL: agent's tests do not pass against the correct implementation"
  tail -20 "$baseline_log"
  exit 1
fi
echo "  passed"

killed=0
survived=0
suspect_mutants=()
for mutant in "${mutants[@]}"; do
  cp "$mutant" "$full_source"
  echo "== mutant: $(basename "$mutant") =="
  if (cd "$full_test_cwd" && eval "$test_command") > "$mutant_log" 2>&1; then
    echo "  SURVIVED (agent's tests did not catch this bug)"
    survived=$((survived + 1))
  else
    # A nonzero exit here SHOULD mean "the agent's tests ran and caught a
    # real behavioral difference" — but it's the same signal a mutant that
    # doesn't even COMPILE would produce, which isn't the agent's tests
    # catching anything (adversarial review finding M5). Heuristic check,
    # not a hard gate (a genuine assertion failure can legitimately print
    # something that looks like these patterns too): flag it loudly if the
    # log shows compiler-error markers with no sign the test runner itself
    # ever started, rather than silently trusting every nonzero exit.
    if grep -qE 'error\[E[0-9]+\]|error TS[0-9]+|SyntaxError' "$mutant_log" \
       && ! grep -qE 'test result:|Test Files|running [0-9]+ test' "$mutant_log"; then
      echo "  killed — ⚠ WARNING: log looks like a COMPILE failure, not a test"
      echo "    catching the bug — this mutant may be invalid rather than genuinely"
      echo "    killed by the agent's tests. Check $mutant_log."
      suspect_mutants+=("$(basename "$mutant")")
    else
      echo "  killed"
    fi
    killed=$((killed + 1))
  fi
  cp "$backup" "$full_source"
done

echo "== result: $killed/${#mutants[@]} mutants killed =="
# Compile-failure warnings restated here, at the very end (adversarial
# review finding L-3) — the per-mutant warning above can end up far
# earlier in the output than the caller's final truncation window (this
# script's own caller slices to the last 2000 chars, and THAT gets sliced
# again to the last 500 for the log row) — with enough mutants or verbose
# test output, an early mutant's warning could be pushed out entirely
# before ever reaching the log. A short summary at the very end survives
# any reasonable truncation, since truncation always keeps the tail.
if [ ${#suspect_mutants[@]} -gt 0 ]; then
  echo "⚠ COMPILE-FAILURE SUSPECTED (not necessarily a genuine test-catch) for: ${suspect_mutants[*]}"
fi
if [ "$survived" -eq 0 ]; then
  echo "PASS"
  exit 0
else
  echo "FAIL: $survived mutant(s) survived"
  exit 1
fi
