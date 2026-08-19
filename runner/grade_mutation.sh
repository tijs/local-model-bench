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
#       <baseline-test-command> <mutant-file-1> [<mutant-file-2> ...]
#
# Exit code 0 = task passed (baseline command succeeded AND every mutant was
# killed). Exit code 1 = failed. Prints a one-line summary either way.
set -uo pipefail

run_dir="$1"; shift
source_file="$1"; shift
test_command="$1"; shift
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

backup=$(mktemp)
cp "$full_source" "$backup"
cleanup() { cp "$backup" "$full_source"; rm -f "$backup"; }
trap cleanup EXIT

echo "== baseline (correct implementation) =="
if ! (cd "$run_dir" && eval "$test_command") > /tmp/grade_mutation_baseline.log 2>&1; then
  echo "FAIL: agent's tests do not pass against the correct implementation"
  tail -20 /tmp/grade_mutation_baseline.log
  exit 1
fi
echo "  passed"

killed=0
survived=0
for mutant in "${mutants[@]}"; do
  cp "$mutant" "$full_source"
  echo "== mutant: $(basename "$mutant") =="
  if (cd "$run_dir" && eval "$test_command") > /tmp/grade_mutation_mutant.log 2>&1; then
    echo "  SURVIVED (agent's tests did not catch this bug)"
    survived=$((survived + 1))
  else
    echo "  killed"
    killed=$((killed + 1))
  fi
  cp "$backup" "$full_source"
done

echo "== result: $killed/${#mutants[@]} mutants killed =="
if [ "$survived" -eq 0 ]; then
  echo "PASS"
  exit 0
else
  echo "FAIL: $survived mutant(s) survived"
  exit 1
fi
