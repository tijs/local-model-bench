#!/usr/bin/env python3
"""Score an anchor-fidelity gate run. Call this only after the gate's DONE
sentinel: scoring a glob mid-run silently reads a partial artifact set and
reports the smaller denominator as though it were the result.

usage: score_anchor_fidelity.py <artifact-dir> <prefix> [n]
"""
import json
import sys

art, prefix = sys.argv[1], sys.argv[2]
n = int(sys.argv[3]) if len(sys.argv) > 3 else 5

admissible = identical = 0
for i in range(n):
    cold = json.load(open(f"{art}/{prefix}-{i}-cold.json"))
    restored = json.load(open(f"{art}/{prefix}-{i}-restored.json"))
    # A leg only compares if it really was cold vs really restored over the
    # same prompt; otherwise it is not evidence either way.
    ok = (cold["cached_tokens"] == 0
          and restored["cached_tokens"] > 0
          and cold["prompt_tokens"] == restored["prompt_tokens"])
    same = (cold["text"] == restored["text"]
            and cold["tool_calls"] == restored["tool_calls"])
    admissible += ok
    identical += ok and same
    print(f"  p{i}: admissible={ok} identical={same}")

print(f"  fidelity: admissible {admissible}/{n}, identical {identical}/{admissible}")
sys.exit(0 if admissible == n and identical == admissible else 1)
