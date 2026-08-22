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
  {"type": "contains_any", "phrases": ["couldn't find", "not found"]}
  {"type": "tool_call_then_response",
   "expected_tool": "add_numbers",
   "expected_args": {"a": 15, "b": 27},        // required SUBSET of the actual
                                                // call's args, order-agnostic on
                                                // which key the dict lists first,
                                                // numeric-aware value comparison
                                                // (15 == 15.0), extra args allowed
   "expected_args_match": {"query": "(?i)amsterdam"},  // optional: per-arg regex
   "response_contains": "42",                  // or "response_matches": "regex"
  }
  {"type": "chained_tool_calls",
   "expected_sequence": ["web_search", "write_file"],
   "write_file_arg_contains": "912046",        // substring match on "content" arg
   "write_file_arg_equals": "912046",          // exact match (whitespace-stripped)
   "write_file_arg_path": "population.txt"}    // suffix match on "path" arg

Any check dict may also carry, checked BEFORE the kind-specific logic,
against final_text, regardless of kind:
  "must_not_contain_any": ["fabricated content marker", ...]  // hard veto —
     a match here fails the check even if the positive condition also matched
  "must_not_match": "regex"                                   // same, as a regex

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
    """Applies each pattern independently in sequence, not as mutually
    exclusive if/elif branches (a second independent adversarial review,
    finding L-1, found two real leaks in the previous if/elif version):
    a complete block followed by a STRAY extra closer
    ("<think>a</think>x</think>42" left "x</think>42" — the closer-leak
    check only ran when the FIRST sub() made no change at all, so it never
    fired here even though a stray closer remained), and a closer
    appearing BEFORE an (unrelated) later opener
    ("</think> answer <think>more" — the lone-closer branch explicitly
    required NO "<think>" anywhere in the text, so a later, unrelated
    opener suppressed it entirely, leaking everything through unstripped).
    Now: strip complete blocks, then strip a remaining leading lone-closer,
    then strip a remaining trailing unclosed opener — each independently,
    so any combination of the three shapes in one string is handled.

    Two more gaps closed here (3rd adversarial review, low findings):
    (1) LONE_CLOSE_THINK's `^.*?</think>` anchor only ever fires ONCE per
    `.sub()` call (it can only match at the true start of the string), so
    TWO stray closers after one complete block
    ("<think>a</think>x</think>y</think>42") left "y</think>42" leaking
    through — confirmed live. Now loops, stripping one leading stray
    closer at a time until none remain. (2) Some models emit reasoning
    delimiters as ◁think▷/◁/think▷ (U+25C1/U+25B7 glyphs) instead of angle
    brackets — confirmed live that this passed through completely
    unstripped. Normalized to the standard spelling up front so every
    pattern below handles both without duplicating each regex."""
    text = text or ""
    text = text.replace("◁think▷", "<think>").replace("◁/think▷", "</think>")
    stripped = THINK_BLOCK.sub("", text)
    while "</think>" in stripped and "<think>" not in stripped.split("</think>", 1)[0]:
        new_stripped = LONE_CLOSE_THINK.sub("", stripped, count=1)
        if new_stripped == stripped:
            break
        stripped = new_stripped
    if "<think>" in stripped and "</think>" not in stripped.split("<think>", 1)[1]:
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
    # normalize_punctuation applied to each CHECK phrase too, not just the
    # model's text (3rd adversarial review, low finding): the original
    # 2026-08-20 fix only normalized final_text, so a check phrase written
    # with a curly quote/dash would never match plain-ASCII model prose —
    # the same typography-fairness gap this normalization exists to
    # prevent, just on the other side of the comparison. Confirmed live:
    # a phrase "couldn't find" (curly apostrophe) failed to match "I
    # couldn't find the file." (plain ASCII). No current task's check
    # phrases actually use smart punctuation, so this was latent, not yet
    # exploited.
    lowered = text.lower()
    for phrase in check.get("must_not_contain_any", ()):
        if normalize_punctuation(phrase).lower() in lowered:
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

    # Universal add-on, same spot/pattern as must_not_contain_any/
    # must_not_match above (methodology review, finding F8/R7): every
    # existing check kind assumes the correct answer involves calling a
    # specific tool — nothing tested the opposite case, a question where
    # the correct behavior is a direct answer from the model's own
    # knowledge with NO tool call at all. A model that reaches for
    # web_search/execute_code/etc. on a question that needs neither is a
    # real, gradeable mistake (needlessly slower, and a red flag for
    # over-triggering tool use in general), not an equally-valid choice.
    if check.get("must_not_call_tools") and result.get("tool_calls"):
        called = [c["name"] for c in result["tool_calls"]]
        return False, f"model called tool(s) {called} for a question that expected a direct answer with no tool use"

    kind = check["type"]

    if kind == "regex":
        if re.search(check["pattern"], text):
            return True, ""
        return False, f"final_text {text!r} did not match pattern {check['pattern']!r}"

    if kind == "contains":
        if normalize_punctuation(check["text"]) in text:
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
        if any(normalize_punctuation(phrase).lower() in lowered for phrase in check["phrases"]):
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

        # write_file_arg_contains/_equals/_path are ANDed on the SAME call
        # (3rd adversarial review, finding CR3-7) — each used to be checked
        # independently against ALL write_file calls, so a model making
        # multiple write_file calls could satisfy each condition with a
        # DIFFERENT call and still pass, e.g. one call with the right
        # content but wrong path, and a second with the right path but
        # wrong content: neither call alone is correct, but the check
        # (checking "does ANY call have the right content" and separately
        # "does ANY call have the right path") passed anyway. Confirmed
        # live with exactly that two-call case against
        # hermes_ops-chaining's real check. A prompt asking for one
        # correct write_file call requires ONE call to satisfy every
        # declared condition together.
        write_file_checks = {
            k: check[k] for k in
            ("write_file_arg_contains", "write_file_arg_equals", "write_file_arg_path")
            if k in check
        }
        if write_file_checks:
            def _call_satisfies(c):
                if c["name"] != "write_file":
                    return False
                args = c["arguments"]
                if "write_file_arg_contains" in write_file_checks and \
                        write_file_checks["write_file_arg_contains"] not in str(args.get("content", "")):
                    return False
                if "write_file_arg_equals" in write_file_checks and \
                        str(args.get("content", "")).strip() != str(write_file_checks["write_file_arg_equals"]):
                    return False
                if "write_file_arg_path" in write_file_checks and \
                        not str(args.get("path", "")).endswith(write_file_checks["write_file_arg_path"]):
                    return False
                return True

            if not any(_call_satisfies(c) for c in calls):
                write_file_calls = [c["arguments"] for c in calls if c["name"] == "write_file"]
                return False, (
                    f"no single write_file call satisfied all of {write_file_checks} "
                    f"together (calls: {write_file_calls})"
                )

        return True, ""

    if kind == "tool_call_then_response":
        calls = [c for c in result.get("tool_calls", []) if c["name"] == check["expected_tool"]]
        if not calls:
            return False, f"tool '{check['expected_tool']}' was never called (called: {[c['name'] for c in result.get('tool_calls', [])]})"

        expected_args = check.get("expected_args")
        patterns = check.get("expected_args_match")

        # expected_args and expected_args_match are ANDed on the SAME call
        # (3rd adversarial review, finding CR3-7) — each used to narrow
        # `calls` independently, so a model making multiple calls to the
        # right tool could satisfy expected_args with one call and
        # expected_args_match with a DIFFERENT call, and still pass, even
        # though no single call actually had both the right argument value
        # and the right argument content. Confirmed live: web_search calls
        # {category: weather, query: "best pizza"} and {category: news,
        # query: "amsterdam weather"} together passed a check requiring
        # {category: weather} AND query matching "amsterdam", despite
        # neither call alone satisfying both. Combined into one predicate
        # so a single call must satisfy everything declared.
        def _values_equal(expected_v, actual_v):
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
            try:
                return float(expected_v) == float(actual_v)
            except (TypeError, ValueError):
                return str(expected_v) == str(actual_v)

        def _call_ok(c):
            actual = c["arguments"]
            if expected_args and not all(
                k in actual and _values_equal(v, actual[k]) for k, v in expected_args.items()
            ):
                return False
            if patterns and not all(
                # Per-argument regex assertions (adversarial review finding
                # M-3): mock_tool_responses is keyed by TOOL NAME only, and
                # `expected_args: {}` (falsy) skips argument checking
                # entirely — so hermes_ops-selection, a task titled "Pick
                # the right tool out of 41 available", never verified the
                # model searched for anything relevant. A model calling
                # web_search(query="best pizza") got the mocked
                # Amsterdam-weather result back and passed as long as "18"
                # appeared somewhere in its answer. This grades tool USE,
                # not just tool SELECTION.
                re.search(pattern, str(actual.get(k, "")), re.IGNORECASE)
                for k, pattern in patterns.items()
            ):
                return False
            return True

        if not expected_args and not patterns:
            # no specific arguments required — any call to the right tool counts
            matched = calls[0]
        else:
            matched = next((c for c in calls if _call_ok(c)), None)
            if matched is None:
                return False, (
                    f"'{check['expected_tool']}' was called but no single call satisfied "
                    f"expected_args={expected_args} and expected_args_match={patterns} together "
                    f"(saw: {[c['arguments'] for c in calls]})"
                )

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
            # re.IGNORECASE added (3rd adversarial review, finding CR3-10):
            # this was the only case-sensitive text-matching check kind in
            # the file (contains/regex are deliberately case-sensitive for
            # exact-literal checks; contains_any and expected_args_match
            # already fold case) — confirmed live that a correct lowercase
            # "18c" answer failed hermes_ops-selection's response_matches
            # check purely on casing, the same fairness gap the
            # smart-quote normalization elsewhere in this file exists to
            # prevent.
            if not re.search(check["response_matches"], text, re.IGNORECASE):
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
