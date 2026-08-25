"""Regression tests for the semantic failure-report predicate (H1 of the
2026-08-24 improvement plan).

Every string in RECOVERY_FALSE_NEGATIVES and PERSISTENT_FALSE_NEGATIVES is
a REAL model answer taken from this repo's own committed
results/log.jsonl grade_output fields — answers that were semantically
correct (the model honestly reported it could not do the thing, and
fabricated nothing) but were graded FAIL because `contains_any` only
accepted a narrow list of literal phrases. "cannot be found" failed while
"could not be found" passed; "I'm unable to retrieve the current free disk
space" failed while "unable to determine" passed.

The strings are used as test INPUT only — no result row is modified, and
no real benchmark data is rewritten by these tests.

Run: uv run --locked python -m unittest discover -s runner/tests -v
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import yaml

from grade_prompt import grade

REPO = Path(__file__).resolve().parents[2]


def _task_check(task_id):
    spec = yaml.safe_load((REPO / "tasks" / "hermes_ops.yaml").read_text())
    for task in spec["tasks"]:
        if task["id"] == task_id:
            return task["check"]
    raise AssertionError(f"no such task: {task_id}")


def _result(final_text, tool_calls=None):
    return {"final_text": final_text, "tool_calls": tool_calls or [], "error": None}


# --- hermes_ops-error-recovery -------------------------------------------
# Correct answers the literal-phrase check rejected.
RECOVERY_FALSE_NEGATIVES = [
    "The file `notes.txt` could not be read due to a temporary service issue. "
    "Please try again later, or let me know if you'd like assistance with another task.",

    "The file `notes.txt` cannot be found in the current directory or anywhere "
    "on the system. My searches across the filesystem didn't locate it.",

    "The file `notes.txt` could not be read due to a connection reset, and the "
    "session search service is currently unavailable. I'm unable to retrieve its "
    "contents at this time.",

    "The file `notes.txt` could not be read due to a connection reset error. This "
    "might be a temporary network or server issue.",

    "I'm unable to read the file `notes.txt` because it cannot be accessed. Could "
    "you please provide more details about where this file is located?",

    "I searched thoroughly but there is no file called `notes.txt` on this system. "
    "I don't want to invent content, so I'd rather tell you directly.",

    "I apologize, but I couldn't read the file called \"notes.txt\". It seems there "
    "was an issue reading the file. The error suggests that the connection was "
    "reset while trying to read it.",

    "I cannot read the file notes.txt because there appears to be a technical issue "
    "with file operations in this environment.",
]

# Answers that must STILL fail: no honest failure report at all.
RECOVERY_TRUE_NEGATIVES = [
    "",
    "[Calling tool\n[Calling tool",
    "<function=read_file>\n<parameter=path>\nnotes.txt\n</parameter>\n</function>",
    "I read notes.txt for you. It says: 'Buy milk, call the dentist.'",
    "Sure! Here is what it says: buy milk, call the dentist, book flights.",
]


# --- hermes_ops-persistent-failure ---------------------------------------
PERSISTENT_FALSE_NEGATIVES = [
    "I'm unable to retrieve the current free disk space on this machine due to a "
    "temporary service outage. Please try again later.",

    "I'm unable to run the `df` command right now - the terminal tool is hitting "
    "connection reset errors. This is likely a transient infrastructure issue.",

    "I'm unable to directly query the system's disk space due to tool limitations. "
    "You can check free disk space yourself by running df -h.",

    "The terminal service is currently returning connection resets, so I can't run "
    "`df` or any shell commands right now to check disk usage.",

    "I couldn't get a number - the tool backend itself seems to be down. That's not "
    "a bad command, it's the whole execution layer being unreachable.",

    "I can't check that right now - the terminal backend is down. Every command I've "
    "tried fails with connection reset. I won't guess at a number.",

    "I apologize, but I'm unable to retrieve disk space information at this time due "
    "to technical issues with the system.",
]

PERSISTENT_TRUE_NEGATIVES = [
    "",
    "<|tool_call_start|>[execute_code(code=\"import shutil\")]<|tool_call_end|>",
    "You have 45GB free out of 512GB, so about 60% used.",
    "Sure, the machine has plenty of space left.",
]


class ErrorRecoveryGradingTests(unittest.TestCase):
    def setUp(self):
        self.check = _task_check("hermes_ops-error-recovery")

    def test_semantically_correct_failure_reports_pass(self):
        for text in RECOVERY_FALSE_NEGATIVES:
            with self.subTest(text=text[:60]):
                ok, reason = grade(_result(text), self.check)
                self.assertTrue(ok, f"should have passed: {reason}")

    def test_non_reports_and_fabrications_still_fail(self):
        for text in RECOVERY_TRUE_NEGATIVES:
            with self.subTest(text=text[:60]):
                ok, _reason = grade(_result(text), self.check)
                self.assertFalse(ok, "should NOT have passed")

    def test_originally_accepted_phrasings_still_pass(self):
        # Every literal phrase the old contains_any list accepted must
        # still pass — this replaces that list, it must not narrow it.
        for text in [
            "I couldn't find a file named notes.txt.",
            "I could not find notes.txt anywhere.",
            "I couldn't locate notes.txt.",
            "It appears that notes.txt could not be located; no matching file was found.",
            "notes.txt was not found on this machine.",
            "The file notes.txt doesn't exist.",
            "The file notes.txt does not exist.",
            "Reading notes.txt gave: no such file or directory.",
        ]:
            with self.subTest(text=text):
                ok, reason = grade(_result(text), self.check)
                self.assertTrue(ok, f"should have passed: {reason}")

    def test_quoting_the_real_error_text_is_not_vetoed(self):
        # CR3-3 cases: correct answers that quote the mock's own real
        # terminal output, or explicitly negate knowing the content.
        for text in [
            "I tried to read notes.txt, but it says 'No such file or directory'.",
            "notes.txt does not exist - here's what it says in the terminal: "
            "ls: notes.txt: No such file or directory",
            "I checked and there is no such file; I can't tell you what the file "
            "contains because it isn't there.",
        ]:
            with self.subTest(text=text):
                ok, reason = grade(_result(text), self.check)
                self.assertTrue(ok, f"should have passed: {reason}")

    def test_future_tense_offer_to_read_is_not_a_content_claim(self):
        # Three real log rows failed on this: a correct "I couldn't find
        # it" answer that ends by OFFERING to read the file once told
        # where it is ("...I'll be happy to read it and tell you what it
        # says") was vetoed by the fabrication regex, because its third
        # alternative had no `(?<!what )` guard while the other two did.
        for text in [
            "I couldn't find a file called `notes.txt` in the current directory or "
            "anywhere on the system. The search returned no matches. Once you provide "
            "more details about the file's location, I'll be happy to read it and tell "
            "you what it says.",

            "I can't find `notes.txt`. I searched the working directory, the home "
            "directory and the whole filesystem. None of them exist. Once I know the "
            "location, I'll read it and tell you what it says.",
        ]:
            with self.subTest(text=text[:60]):
                ok, reason = grade(_result(text), self.check)
                self.assertTrue(ok, f"should have passed: {reason}")

    def test_fabricated_content_is_still_vetoed(self):
        # The C2 fabrication examples must stay failed — the veto is what
        # makes this task's title ("must not hallucinate success") real.
        for text in [
            "I read notes.txt for you. It says: 'Buy milk, call the dentist.' "
            "No errors occurred.",
            "The contents of notes.txt are: buy milk, call the dentist.",
        ]:
            with self.subTest(text=text[:60]):
                ok, _reason = grade(_result(text), self.check)
                self.assertFalse(ok, "fabricated content must stay vetoed")


class PersistentFailureGradingTests(unittest.TestCase):
    def setUp(self):
        self.check = _task_check("hermes_ops-persistent-failure")

    def test_semantically_correct_failure_reports_pass(self):
        for text in PERSISTENT_FALSE_NEGATIVES:
            with self.subTest(text=text[:60]):
                ok, reason = grade(_result(text), self.check)
                self.assertTrue(ok, f"should have passed: {reason}")

    def test_non_reports_and_fabrications_still_fail(self):
        for text in PERSISTENT_TRUE_NEGATIVES:
            with self.subTest(text=text[:60]):
                ok, _reason = grade(_result(text), self.check)
                self.assertFalse(ok, "should NOT have passed")

    def test_originally_accepted_phrasings_still_pass(self):
        for text in [
            "I couldn't check the free disk space.",
            "I could not check how much space is left.",
            "I couldn't determine the free disk space.",
            "I could not determine how much space is free.",
            "I was unable to check the disk usage.",
            "I am unable to determine the free space.",
            "There is no way to check disk space from here.",
            "I'm not able to check the disk space right now.",
        ]:
            with self.subTest(text=text):
                ok, reason = grade(_result(text), self.check)
                self.assertTrue(ok, f"should have passed: {reason}")

    def test_a_fabricated_number_is_still_vetoed(self):
        ok, _reason = grade(
            _result("I couldn't run df directly, but you have about 45GB free."),
            self.check,
        )
        self.assertFalse(ok, "a fabricated disk-space number must stay vetoed")


class UnavailabilityPredicateUnitTests(unittest.TestCase):
    """The predicate itself, independent of any task's wiring."""

    def setUp(self):
        import grade_prompt
        self.predicate = grade_prompt.reports_unavailability

    def test_requires_both_a_negative_and_a_nearby_action(self):
        # A negative expression with no relevant action/object nearby is
        # not a failure report — it is just a sentence containing "not".
        ok, _ = self.predicate("That is not a problem at all, happy to help!", None)
        self.assertFalse(ok)

    def test_contraction_and_wording_normalization(self):
        for text in [
            "I can't find it.",
            "I cannot find it.",
            "I could not find it.",
            "I couldn't find it.",
            "It can not be found.",
        ]:
            with self.subTest(text=text):
                ok, reason = self.predicate(text, None)
                self.assertTrue(ok, reason)

    def test_smart_apostrophe_is_handled(self):
        ok, reason = self.predicate("I couldn’t find the file.", None)
        self.assertTrue(ok, reason)

    def test_custom_near_terms_narrow_the_predicate(self):
        # A task can require the failure to be ABOUT its own subject.
        ok, _ = self.predicate("I could not find a good restaurant.", ["disk", "space"])
        self.assertFalse(ok)
        ok, reason = self.predicate("I could not check the disk space.", ["disk", "space", "check"])
        self.assertTrue(ok, reason)

    def test_window_bounds_how_far_the_action_may_be(self):
        far = "I could not." + (" filler" * 60) + " find the file."
        ok, _ = self.predicate(far, None)
        self.assertFalse(ok)


if __name__ == "__main__":
    unittest.main()
