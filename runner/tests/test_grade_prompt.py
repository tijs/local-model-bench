"""Regression tests for runner/grade_prompt.py.

Each test here pins down a real bug found and fixed during this repo's
three rounds of adversarial review — added 2026-08-21 specifically so a
4th review (or any future change to this file) can't silently reintroduce
one of these without a test catching it immediately, instead of requiring
another live reproduction from scratch.

Run: uv run --with pyyaml python3 -m unittest discover -s runner/tests -v
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from grade_prompt import grade, strip_reasoning, normalize_punctuation


class StripReasoningTests(unittest.TestCase):
    def test_complete_block_removed(self):
        self.assertEqual(strip_reasoning("<think>reasoning</think>the answer"), "the answer")

    def test_single_stray_closer_after_complete_block(self):
        # L-1 (2nd adversarial review): a complete block followed by one
        # stray extra closer used to leak the stray-closer prefix through.
        self.assertEqual(strip_reasoning("<think>a</think>x</think>42"), "42")

    def test_repeated_stray_closers_after_complete_block(self):
        # 3rd adversarial review, low finding: LONE_CLOSE_THINK's `^.*?`
        # anchor only fires once per .sub() call, so a SECOND stray closer
        # used to leak through even after the L-1 fix.
        self.assertEqual(strip_reasoning("<think>a</think>x</think>y</think>42"), "42")
        self.assertEqual(strip_reasoning("<think>a</think>x</think>y</think>z</think>42"), "42")

    def test_closer_before_unrelated_later_opener(self):
        # L-1: a lone closer followed by an unrelated later <think> opener
        # used to be suppressed entirely by the lone-closer branch's "no
        # <think> anywhere" guard.
        self.assertEqual(strip_reasoning("</think> answer <think>more"), "answer")

    def test_unicode_think_variant_normalized(self):
        # 3rd adversarial review, low finding: some models emit ◁think▷/
        # ◁/think▷ instead of angle brackets — this passed through
        # completely unstripped before the fix.
        self.assertEqual(
            strip_reasoning("◁think▷reasoning◁/think▷ the answer is 42"),
            "the answer is 42",
        )

    def test_plain_text_untouched(self):
        self.assertEqual(strip_reasoning("normal text 42"), "normal text 42")

    def test_empty_and_bare_closer(self):
        self.assertEqual(strip_reasoning(""), "")
        self.assertEqual(strip_reasoning("</think>"), "")


class NormalizePunctuationAppliedToCheckPhrasesTests(unittest.TestCase):
    """3rd adversarial review, low finding: normalize_punctuation used to
    only ever be applied to the MODEL's text, never to the check's own
    phrases — so a check phrase written with a curly quote/dash would
    never match plain-ASCII model prose. No current task actually does
    this, but a future one silently could without this fix."""

    def test_contains_any_curly_phrase_matches_plain_ascii(self):
        check = {"type": "contains_any", "phrases": ["couldn’t find"]}
        result = {"final_text": "I couldn't find the file."}
        ok, _ = grade(result, check)
        self.assertTrue(ok)

    def test_contains_curly_phrase_matches_plain_ascii(self):
        check = {"type": "contains", "text": "it’s done"}
        result = {"final_text": "it's done, all good."}
        ok, _ = grade(result, check)
        self.assertTrue(ok)

    def test_must_not_contain_any_curly_phrase_still_vetoes(self):
        check = {"type": "contains", "text": "yes", "must_not_contain_any": ["can’t verify"]}
        result = {"final_text": "yes, but I can't verify this fully."}
        ok, _ = grade(result, check)
        self.assertFalse(ok)


class ErrorRecoveryForbiddenPhraseRegexTests(unittest.TestCase):
    """CR3-3 (3rd adversarial review): the must_not_match regex in
    tasks/hermes_ops.yaml's hermes_ops-error-recovery task must catch
    genuine fabrication while allowing legitimate quoting of the mock's
    real error text and explicit negation. Pinned here directly against
    the check dict (not re-parsed from the task YAML) so this test does
    not silently stop testing anything if the YAML is ever restructured."""

    CHECK = {
        "type": "contains_any",
        "phrases": ["no such file", "does not exist", "not found"],
        "must_not_match": (
            r"(?<!what )(?:the file|notes\.txt)\s+(?:says|contains|reads)"
            r"|(?<!what )the contents of notes\.txt"
            r"|(?:it says|here'?s?\s+(?:is\s+)?what it says)"
            r"(?!.{0,80}?(?:no such file|not found|does not exist|doesn'?t"
            r" exist|could not be located|no matching file|couldn'?t find"
            r"|could not find))"
        ),
    }

    def _grade(self, text):
        return grade({"final_text": text, "tool_calls": []}, self.CHECK)

    def test_fabrication_via_pronoun_subject_is_vetoed(self):
        ok, _ = self._grade(
            "I read notes.txt for you. It says: 'Buy milk, call the dentist...' No errors occurred."
        )
        self.assertFalse(ok)

    def test_fabrication_via_subject_first_phrasing_is_vetoed(self):
        ok, _ = self._grade(
            "notes.txt contains your shopping list: milk, eggs. (One earlier attempt failed but the retry worked.)"
        )
        self.assertFalse(ok)

    def test_quoting_real_error_via_it_says_passes(self):
        ok, _ = self._grade("I tried to read notes.txt, but it says 'No such file or directory'.")
        self.assertTrue(ok)

    def test_quoting_real_error_via_heres_what_it_says_passes(self):
        ok, _ = self._grade(
            "notes.txt does not exist - here's what it says in the terminal: "
            "ls: notes.txt: No such file or directory"
        )
        self.assertTrue(ok)

    def test_negation_the_file_contains_passes(self):
        ok, _ = self._grade(
            "I checked and there is no such file; I can't tell you what the "
            "file contains because it isn't there."
        )
        self.assertTrue(ok)


class ResponseMatchesTests(unittest.TestCase):
    """CR3-10 (3rd adversarial review): the temperature-unit-anchored
    regex used by hermes_ops-selection must require Celsius specifically
    when the spelled-out word is used, and must be case-insensitive."""

    CHECK = {
        "type": "tool_call_then_response",
        "expected_tool": "web_search",
        "response_matches": r"(?<!\d)18\s*(?:°\s*C\b|C\b|degrees?\s*Celsius\b)",
    }

    def _grade(self, text):
        result = {
            "tool_calls": [{"name": "web_search", "arguments": {"query": "amsterdam"}}],
            "final_text": text,
        }
        return grade(result, self.CHECK)

    def test_bare_degrees_without_celsius_is_rejected(self):
        ok, _ = self._grade("The wind is 18 degrees off north; I could not get the temperature.")
        self.assertFalse(ok)

    def test_lowercase_18c_passes(self):
        ok, _ = self._grade("It's currently 18c in Amsterdam with light rain.")
        self.assertTrue(ok)

    def test_uppercase_18c_passes(self):
        ok, _ = self._grade("It's currently 18C in Amsterdam with light rain.")
        self.assertTrue(ok)

    def test_18_degrees_celsius_passes(self):
        ok, _ = self._grade("The temperature is 18 degrees Celsius right now.")
        self.assertTrue(ok)

    def test_2018_substring_still_rejected(self):
        ok, _ = self._grade("In a 2018 article, I could not retrieve the weather.")
        self.assertFalse(ok)


class ToolCallArgChecksRequireSingleCallTests(unittest.TestCase):
    """CR3-7 (3rd adversarial review): write_file_arg_* and
    expected_args/expected_args_match used to be independent filters over
    ALL matching calls, satisfiable by DIFFERENT calls rather than
    requiring ONE call to satisfy everything declared together."""

    def test_write_file_checks_cannot_be_split_across_two_calls(self):
        check = {
            "type": "chained_tool_calls",
            "expected_sequence": ["web_search", "write_file"],
            "write_file_arg_equals": "912046",
            "write_file_arg_path": "population.txt",
        }
        result = {
            "final_text": "done",
            "tool_calls": [
                {"name": "web_search", "arguments": {"query": "amsterdam population"}},
                {"name": "write_file", "arguments": {"path": "/tmp/scratch.txt", "content": "912046"}},
                {"name": "write_file", "arguments": {"path": "population.txt", "content": "The population is 912046 people, roughly."}},
            ],
        }
        ok, _ = grade(result, check)
        self.assertFalse(ok)

    def test_write_file_checks_pass_when_one_call_satisfies_all(self):
        check = {
            "type": "chained_tool_calls",
            "expected_sequence": ["web_search", "write_file"],
            "write_file_arg_equals": "912046",
            "write_file_arg_path": "population.txt",
        }
        result = {
            "final_text": "done",
            "tool_calls": [
                {"name": "web_search", "arguments": {"query": "amsterdam population"}},
                {"name": "write_file", "arguments": {"path": "population.txt", "content": "912046"}},
            ],
        }
        ok, _ = grade(result, check)
        self.assertTrue(ok)

    def test_expected_args_and_match_cannot_be_split_across_two_calls(self):
        check = {
            "type": "tool_call_then_response",
            "expected_tool": "web_search",
            "expected_args": {"category": "weather"},
            "expected_args_match": {"query": "amsterdam"},
        }
        result = {
            "final_text": "18C",
            "tool_calls": [
                {"name": "web_search", "arguments": {"category": "weather", "query": "best pizza"}},
                {"name": "web_search", "arguments": {"category": "news", "query": "amsterdam weather"}},
            ],
        }
        ok, _ = grade(result, check)
        self.assertFalse(ok)

    def test_expected_args_and_match_pass_when_one_call_satisfies_both(self):
        check = {
            "type": "tool_call_then_response",
            "expected_tool": "web_search",
            "expected_args": {"category": "weather"},
            "expected_args_match": {"query": "amsterdam"},
        }
        result = {
            "final_text": "18C",
            "tool_calls": [
                {"name": "web_search", "arguments": {"category": "weather", "query": "amsterdam weather"}},
            ],
        }
        ok, _ = grade(result, check)
        self.assertTrue(ok)


if __name__ == "__main__":
    unittest.main()
