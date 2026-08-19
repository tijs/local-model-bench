#!/usr/bin/env python3
"""
Grades a run_prompt.py result JSON against a check spec. Strips <think>...
</think> reasoning blocks before matching text — many local models (LFM
included) emit an inline reasoning trace before the real answer; grading on
the raw string would unfairly fail a model for reasoning at all, so we only
score the actual answer content, same as a real harness would present it to
a user.

Usage:
  grade_prompt.py --result run_result.json --check check_spec.json

check_spec.json, one of:
  {"type": "regex", "pattern": "^42$"}
  {"type": "contains", "text": "42"}
  {"type": "tool_call_then_response",
   "expected_tool": "add_numbers",
   "expected_args": {"a": 15, "b": 27},   // order-agnostic on values
   "response_contains": "42"}

Prints "PASS" or "FAIL: <reason>" and exits 0/1 accordingly.
"""
import argparse
import json
import re
import sys

THINK_BLOCK = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)


def strip_reasoning(text):
    return THINK_BLOCK.sub("", text or "").strip()


def grade(result, check):
    if result.get("error"):
        return False, f"run errored: {result['error']}"
    if result.get("hallucinated_tool_calls"):
        return False, f"model called tool(s) never declared in this task's manifest: {result['hallucinated_tool_calls']} — check the proxy isn't filtering tools, or the model is confabulating"

    kind = check["type"]

    if kind == "regex":
        text = strip_reasoning(result.get("final_text", ""))
        if re.search(check["pattern"], text):
            return True, ""
        return False, f"final_text {text!r} did not match pattern {check['pattern']!r}"

    if kind == "contains":
        text = strip_reasoning(result.get("final_text", ""))
        if check["text"] in text:
            return True, ""
        return False, f"final_text {text!r} did not contain {check['text']!r}"

    if kind == "contains_any":
        text = strip_reasoning(result.get("final_text", "")).lower()
        if any(phrase.lower() in text for phrase in check["phrases"]):
            return True, ""
        return False, f"final_text {text!r} did not contain any of {check['phrases']}"

    if kind == "chained_tool_calls":
        calls = result.get("tool_calls", [])
        names_in_order = [c["name"] for c in calls]
        expected = check["expected_sequence"]
        # each expected name must appear, in order (not necessarily contiguous)
        cursor = 0
        for name in expected:
            found = False
            while cursor < len(names_in_order):
                if names_in_order[cursor] == name:
                    found = True
                    cursor += 1
                    break
                cursor += 1
            if not found:
                return False, f"expected sequence {expected} not found in actual calls {names_in_order}"

        if "write_file_arg_contains" in check:
            needle = check["write_file_arg_contains"]
            matches = [
                c for c in calls
                if c["name"] == "write_file"
                and any(needle in str(v) for v in c["arguments"].values())
            ]
            if not matches:
                return False, f"no write_file call had an argument containing {needle!r} (calls: {[c['arguments'] for c in calls if c['name']=='write_file']})"

        return True, ""

    if kind == "tool_call_then_response":
        calls = [c for c in result.get("tool_calls", []) if c["name"] == check["expected_tool"]]
        if not calls:
            return False, f"tool '{check['expected_tool']}' was never called (called: {[c['name'] for c in result.get('tool_calls', [])]})"

        expected_args = check.get("expected_args")
        if not expected_args:
            # no specific arguments required — any call to the right tool counts
            matched = calls[0]
        else:
            expected_values = sorted(map(str, expected_args.values()))
            matched = None
            for c in calls:
                actual_values = sorted(map(str, c["arguments"].values()))
                if actual_values == expected_values:
                    matched = c
                    break
            if matched is None:
                return False, f"'{check['expected_tool']}' was called but never with argument values {expected_values} (saw: {[c['arguments'] for c in calls]})"

        if "response_contains" in check:
            text = strip_reasoning(result.get("final_text", ""))
            if check["response_contains"] not in text:
                return False, f"tool was called correctly but final response {text!r} did not contain {check['response_contains']!r}"

        return True, ""

    raise ValueError(f"unknown check type: {kind}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--result", required=True)
    ap.add_argument("--check", required=True)
    args = ap.parse_args()

    result = json.loads(open(args.result).read())
    check = json.loads(open(args.check).read())

    ok, reason = grade(result, check)
    if ok:
        print("PASS")
        sys.exit(0)
    else:
        print(f"FAIL: {reason}")
        sys.exit(1)


if __name__ == "__main__":
    main()
