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
# Some models/templates (observed live with Qwen3.8-27B via vllm-mlx) start
# assistant turns implicitly "inside" a thinking block — the response has a
# closing </think> but no opening <think> tag. Strip everything up to and
# including the first lone closing tag too, or reasoning leaks into graded
# output.
LONE_CLOSE_THINK = re.compile(r"^.*?</think>", re.DOTALL | re.IGNORECASE)
# An OPENED-but-never-closed think block (adversarial review finding M2) —
# distinct from the lone-close case above. run_prompt.py now refuses to
# treat a finish_reason=length response as a real answer at all (finding
# M1), which prevents the specific failure mode the review demonstrated
# (a truncated-mid-reasoning response with raw reasoning graded as the
# answer) — but a model could in principle emit this shape for some other
# reason, so strip defensively too: an unclosed <think> means everything
# from that point on is an incomplete reasoning trace, not an answer, so
# drop it rather than grade it.
UNCLOSED_OPEN_THINK = re.compile(r"<think>.*$", re.DOTALL | re.IGNORECASE)


def strip_reasoning(text):
    text = text or ""
    stripped = THINK_BLOCK.sub("", text)
    if stripped == text and "</think>" in text and "<think>" not in text:
        stripped = LONE_CLOSE_THINK.sub("", text)
    elif "<think>" in stripped and "</think>" not in stripped:
        stripped = UNCLOSED_OPEN_THINK.sub("", stripped)
    return stripped.strip()


# Typographic ("smart") punctuation normalization. Discovered live 2026-08-20:
# gpt-5.6-luna answered a task correctly ("i couldn't find a file named
# notes.txt...") but used a curly apostrophe (U+2019, '), which silently
# failed contains_any against the check's plain-ASCII phrase list
# ("couldn't find") — a real, semantically-correct answer graded as a
# failure purely over typography. Apply to every text-matching check kind,
# not just the one that surfaced it — regex/contains checks against a
# fixed literal are just as exposed if a model's prose happens to use
# curly quotes/dashes where the check was written with straight ones.
_SMART_PUNCTUATION = {
    "‘": "'", "’": "'",  # single quotes/apostrophe
    "“": '"', "”": '"',  # double quotes
    "–": "-", "—": "-",  # en/em dash
}


def normalize_punctuation(text):
    for smart, plain in _SMART_PUNCTUATION.items():
        text = text.replace(smart, plain)
    return text


def _forbidden_hit(text, check):
    """Shared safety net for the three text-matching check kinds.

    Added after an adversarial review found hermes_ops-error-recovery's
    contains_any check would PASS a model that fabricates the file's
    contents, as long as its answer also happened to contain a word like
    "error" or "failed" somewhere (e.g. narrating a red herring). A
    positive keyword match alone was never proof the model gave a *correct*
    answer — only that its answer contained a common word. This lets any
    check spec add `must_not_contain_any` (plain substrings, case-
    insensitive) or `must_not_match` (regex) as a hard veto, independent of
    whether the positive condition also matched.
    """
    lowered = text.lower()
    for phrase in check.get("must_not_contain_any", ()):
        if phrase.lower() in lowered:
            return f"final_text {text!r} contains forbidden phrase {phrase!r}"
    pattern = check.get("must_not_match")
    if pattern and re.search(pattern, text, re.IGNORECASE):
        return f"final_text {text!r} matched forbidden pattern {pattern!r}"
    return None


def grade(result, check):
    if result.get("error"):
        return False, f"run errored: {result['error']}"
    if result.get("hallucinated_tool_calls"):
        return False, f"model called tool(s) never declared in this task's manifest: {result['hallucinated_tool_calls']} — check the proxy isn't filtering tools, or the model is confabulating"

    # Applied ONCE, universally, against final_text — regardless of check
    # kind. Used to only run inside the regex/contains/contains_any
    # branches, silently doing nothing for chained_tool_calls or
    # tool_call_then_response (found by a second independent adversarial
    # review, finding M-1): a must_not_contain_any on either of those kinds
    # was accepted by the check spec but never actually enforced. Not
    # currently exploitable by any check in this repo (only
    # hermes_ops-error-recovery uses it, and that's a contains_any check),
    # but a future check author reasonably expecting this to work uniformly
    # would have been silently wrong.
    text = normalize_punctuation(strip_reasoning(result.get("final_text", "")))
    forbidden = _forbidden_hit(text, check)
    if forbidden:
        return False, forbidden

    kind = check["type"]

    if kind == "regex":
        if re.search(check["pattern"], text):
            return True, ""
        return False, f"final_text {text!r} did not match pattern {check['pattern']!r}"

    if kind == "contains":
        if check["text"] in text:
            return True, ""
        return False, f"final_text {text!r} did not contain {check['text']!r}"

    # `contains`/`regex` above are deliberately case-sensitive (an exact
    # literal/pattern check shouldn't silently accept a differently-cased
    # answer); `contains_any` below is deliberately NOT, since it exists
    # for natural-language phrase matching where case carries no meaning.
    # Flagged as an inconsistency in an adversarial review — noted here as
    # intentional rather than "fixed" into uniformity, since no check in
    # this repo currently uses `contains`/`regex` on non-numeric text where
    # case sensitivity could matter (verify this still holds before adding
    # one that does).
    if kind == "contains_any":
        lowered = text.lower()
        if any(phrase.lower() in lowered for phrase in check["phrases"]):
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
            # Scoped to the "content" argument specifically (adversarial
            # review finding M4) — scanning every argument value used to
            # let write_file(path="/tmp/912046.txt", content="wrong
            # answer") pass a check meant to verify the FILE'S CONTENT,
            # just because the needle happened to appear in the path
            # instead.
            matches = [
                c for c in calls
                if c["name"] == "write_file"
                and needle in str(c["arguments"].get("content", ""))
            ]
            if not matches:
                return False, f"no write_file call had a 'content' argument containing {needle!r} (calls: {[c['arguments'] for c in calls if c['name']=='write_file']})"

        if "write_file_arg_equals" in check:
            # Exact-match alternative (adversarial review finding L5): a
            # prompt asking to write JUST a value (e.g. "write just that
            # number to a file") is satisfied by write_file_arg_contains
            # even if the model also wrote a sentence around the number —
            # this checks the content is the expected value and nothing
            # else (stripped of surrounding whitespace only).
            expected = str(check["write_file_arg_equals"])
            matches = [
                c for c in calls
                if c["name"] == "write_file"
                and str(c["arguments"].get("content", "")).strip() == expected
            ]
            if not matches:
                return False, f"no write_file call had a 'content' argument equal to {expected!r} (calls: {[c['arguments'] for c in calls if c['name']=='write_file']})"

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
            # Exact key->value matching (adversarial review finding M4) —
            # comparing a sorted multiset of VALUES ONLY (the previous
            # behavior) ignored keys entirely: add_numbers(x=15, y=27)
            # passed a check written for {"a": 15, "b": 27}, and argument
            # order/identity is unverifiable at all for a non-commutative
            # tool (e.g. subtract(a=27, b=15) vs subtract(a=15, b=27) have
            # the same value multiset but a different, wrong, result).
            # Still order-agnostic on which KEY the check dict lists first,
            # per the module docstring's documented contract.
            #
            # Two regressions found by a second independent adversarial
            # review (finding H-6), fixed here: (1) plain str() comparison
            # made 15.0 != "15" != 15 — a model emitting schema-valid JSON
            # floats (perfectly normal for a `type: number` parameter) now
            # failed a check that passed ints. Compare numerically when
            # both sides parse as numbers. (2) full dict equality required
            # the call to have EXACTLY these keys and no others — a model
            # passing an extra optional argument (also schema-valid) now
            # hard-failed. expected_args is a required SUBSET of the
            # actual call's arguments, not the complete set.
            def _values_equal(expected_v, actual_v):
                try:
                    return float(expected_v) == float(actual_v)
                except (TypeError, ValueError):
                    return str(expected_v) == str(actual_v)

            matched = None
            for c in calls:
                actual = c["arguments"]
                if all(k in actual and _values_equal(v, actual[k]) for k, v in expected_args.items()):
                    matched = c
                    break
            if matched is None:
                return False, f"'{check['expected_tool']}' was called but never with (at least) arguments {expected_args} (saw: {[c['arguments'] for c in calls]})"

        if "response_contains" in check:
            text = normalize_punctuation(strip_reasoning(result.get("final_text", "")))
            if check["response_contains"] not in text:
                return False, f"tool was called correctly but final response {text!r} did not contain {check['response_contains']!r}"

        if "response_matches" in check:
            # Regex alternative to response_contains, for values a plain
            # substring check can't safely verify (adversarial review
            # finding L4): "18" as a bare substring matches "2018" or "180"
            # just as well as the real answer. A task checking a specific
            # number should use this with a boundary, e.g. r"(?<!\d)18(?!\d)".
            text = normalize_punctuation(strip_reasoning(result.get("final_text", "")))
            if not re.search(check["response_matches"], text):
                return False, f"tool was called correctly but final response {text!r} did not match pattern {check['response_matches']!r}"

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
