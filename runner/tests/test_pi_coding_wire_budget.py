"""Pi coding output-budget checks, without launching an inference server."""

import json
import sys
import tempfile
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pi_coding.workspace import TaskWorkspace


TOOLS = [
    {"function": {"name": name}}
    for name in ("read_file", "edit_file", "write_file", "run_tests")
]


class PiCodingWireBudgetTests(unittest.TestCase):
    def workspace(self, root):
        out = root / "task"
        out.mkdir()
        return TaskWorkspace(
            {"files": {"main.py": "pass\n"}}, out, time.monotonic(), 16384, 32768
        ), out

    def test_first_turn_uses_full_ceiling_and_later_pi_clamp_is_recorded(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace, out = self.workspace(Path(tmp))
            self.assertEqual(
                workspace.apply("request", {"max_tokens": 16384, "tools": TOOLS}),
                {"ok": True},
            )
            self.assertEqual(
                workspace.apply("request", {"max_tokens": 15000, "tools": TOOLS}),
                {"ok": True},
            )
            rows = [json.loads(line) for line in (out / "wire-budgets.jsonl").read_text().splitlines()]
            self.assertEqual([row["effective_max_tokens"] for row in rows], [16384, 15000])
            self.assertTrue(all(row["accepted"] for row in rows))

    def test_rejected_budget_is_recorded_and_cannot_exceed_ceiling(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace, out = self.workspace(Path(tmp))
            with self.assertRaisesRegex(RuntimeError, "effective=16385"):
                workspace.apply("request", {"max_tokens": 16385, "tools": TOOLS})
            rows = [json.loads(line) for line in (out / "wire-budgets.jsonl").read_text().splitlines()]
            self.assertEqual(len(rows), 1)
            self.assertFalse(rows[0]["accepted"])
            self.assertEqual(rows[0]["effective_max_tokens"], 16385)

    def test_first_request_cannot_start_with_a_reduced_budget(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace, out = self.workspace(Path(tmp))
            with self.assertRaisesRegex(RuntimeError, "first request"):
                workspace.apply("request", {"max_tokens": 8192, "tools": TOOLS})
            rows = [json.loads(line) for line in (out / "wire-budgets.jsonl").read_text().splitlines()]
            self.assertEqual(rows[0]["effective_max_tokens"], 8192)
            self.assertFalse(rows[0]["accepted"])


if __name__ == "__main__":
    unittest.main()
