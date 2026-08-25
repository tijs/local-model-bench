"""Guards that no task's prompt text leaks the harness's own internal
commentary to the candidate agent (M1 of the 2026-08-24 improvement plan).

The bug this pins down is a YAML foot-gun, not a typo: `#` inside a block
scalar (`prompt: |`) is NOT a comment — it is literal prompt content. Four
of kiem_mini's five task prompts ended with paragraphs of review notes
("Added 2026-08-22 (methodology review, findings F10 + F11): ... this is
difficulty 4 ... a real, easy-to-miss cross-representation consistency
bug"), which were delivered verbatim to every model that ever ran those
tasks — telling the agent both the intended difficulty and, in
kiem_mini-rename's case, a strong hint at the exact bug it was meant to
find on its own.

Run: uv run --locked python -m unittest discover -s runner/tests -v
"""
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import yaml

REPO = Path(__file__).resolve().parents[2]

# Vocabulary that only ever appears in harness/review commentary, never in
# a legitimate task instruction.
_METHODOLOGY_MARKERS = (
    "adversarial review",
    "methodology review",
    "improvement plan",
    "finding F",
    "finding H",
    "finding M",
    "finding CR",
    "held-out",
    "grading",
    "the grader",
    "difficulty 4",
    "difficulty capped",
    "AGENTS.md",
    "checks/",
)

# A line that begins with `#` inside a block scalar is the specific shape
# of the bug: a comment the author believed was a comment.
_COMMENT_LINE_RE = re.compile(r"^\s*#", re.MULTILINE)


def _all_prompt_texts():
    for task_file in sorted((REPO / "tasks").glob("*.yaml")):
        spec = yaml.safe_load(task_file.read_text())
        for task in spec.get("tasks") or []:
            if "prompt" in task:
                yield task_file.name, task["id"], "prompt", task["prompt"]
            prompt_spec = task.get("prompt_spec") or {}
            for key in ("user_prompt", "system_prompt"):
                if key in prompt_spec:
                    yield task_file.name, task["id"], key, prompt_spec[key]


class TaskPromptHygieneTests(unittest.TestCase):
    def test_no_prompt_contains_a_comment_line(self):
        for filename, task_id, key, text in _all_prompt_texts():
            with self.subTest(task=task_id, key=key):
                self.assertIsNone(
                    _COMMENT_LINE_RE.search(text),
                    f"{filename}:{task_id}.{key} contains a '#' line — inside a "
                    f"YAML block scalar that is prompt CONTENT, not a comment. "
                    f"Move the note above the `prompt:` key, at the task's own "
                    f"indentation, where YAML really does treat it as a comment.",
                )

    def test_no_prompt_leaks_methodology_vocabulary(self):
        for filename, task_id, key, text in _all_prompt_texts():
            lowered = text.lower()
            for marker in _METHODOLOGY_MARKERS:
                with self.subTest(task=task_id, key=key, marker=marker):
                    self.assertNotIn(
                        marker.lower(), lowered,
                        f"{filename}:{task_id}.{key} leaks internal methodology "
                        f"({marker!r}) to the candidate agent",
                    )

    def test_the_commentary_survives_as_a_real_yaml_comment(self):
        # Removing the leak must not lose the provenance — the notes are
        # genuinely useful, they were just in the wrong place.
        raw = (REPO / "tasks" / "kiem_mini.yaml").read_text()
        for phrase in (
            "methodology review, findings F10 + F11",
            "cross-representation consistency",
            "thinnest open-model",
            "no actual diagnosis was required",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, raw)


if __name__ == "__main__":
    unittest.main()
