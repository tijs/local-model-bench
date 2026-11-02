"""Require complete repeated observations and deterministic cross-arm output."""

import copy
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

SCRIPT = (
    Path(__file__).resolve().parents[2]
    / "artifacts/mei-stable-qualification-20261102/run_matrix.py"
)
SPEC = importlib.util.spec_from_file_location("qualification_matrix", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
matrix = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(matrix)


def complete_result():
    return {
        "status": "passed",
        "normal_output_budget": 8192,
        "rows": [
            {
                "context": context,
                "phase": phase,
                "repeat": repeat,
                "observable": {
                    "text": "1, 2, 3",
                    "prompt_tokens": 30000 if context == "loaded" else 13,
                    "completion_tokens": 128,
                    "finish_reason": "length",
                },
                "decode_tps": 40 + repeat,
            }
            for context in ("short", "loaded")
            for phase, repeats in (
                ("cold" if context == "short" else "cold_status", (0,)),
                ("warmup", (0,)),
                ("measured", range(1, 6)),
            )
            for repeat in repeats
        ],
    }


class MatrixAuditTests(unittest.TestCase):
    def test_repeated_output_is_complete_and_byte_identical(self):
        good = complete_result()
        self.assertEqual(set(matrix.observable_by_context(good)), {"short", "loaded"})
        missing = copy.deepcopy(good)
        missing["rows"].pop()
        duplicate = copy.deepcopy(good)
        duplicate["rows"][-1] = copy.deepcopy(duplicate["rows"][-2])
        changed = copy.deepcopy(good)
        changed["rows"][-1]["observable"]["text"] = "1,2,3"
        for bad in (missing, duplicate, changed):
            with self.assertRaises(ValueError):
                matrix.observable_by_context(bad)

    def test_cross_arm_parity_and_terminal_success_are_required(self):
        good = complete_result()
        baseline = matrix.observable_by_context(good)
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder)
            (output / "qualification.json").write_text(json.dumps(good))
            (output / "outcome.json").write_text('{"status": "passed"}')
            (output / "resources.jsonl").write_text(
                '{"kernel_pressure_level": 1, "swap_used_mib": 1000}\n'
            )
            checked = matrix.audit(output, baseline)
            self.assertEqual(checked["median_decode_tps"], {"short": 43, "loaded": 43})
            changed = copy.deepcopy(baseline)
            changed["loaded"]["text"] = "1,2,3"
            with self.assertRaisesRegex(ValueError, "A1 control"):
                matrix.audit(output, changed)
            (output / "outcome.json").write_text('{"status": "interrupted"}')
            with self.assertRaisesRegex(ValueError, "did not complete"):
                matrix.audit(output, baseline)


if __name__ == "__main__":
    unittest.main()
