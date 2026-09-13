"""Tests for runner/quant_ledger_audit.py — the reproducible quant ledger.

Two layers:

1. test_live_log_reproduces_pins — runs the derivation against the committed
   append-only results/log.jsonl and asserts every pinned count. This is the
   reproducibility gate: the moment a future benchmark run appends rows that
   change the ledger, this test fails loudly and the pins (plus any SUMMARY.md
   aggregate they back) must be updated deliberately.

2. test_derivation_on_synthetic_log — exercises the counting logic against a
   hand-built mini-log so a logic regression is caught without depending on
   the live (growing) log.

Run with: uv run --locked python -m unittest discover -s runner/tests -v
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import quant_ledger_audit as qla  # noqa: E402


def _row(model, engine, passed, task=qla.TASK_ID, suite=qla.SUITE, h_err=False):
    return {
        "model": model,
        "inference_engine": engine,
        "suite": suite,
        "task_id": task,
        "pass": passed,
        "harness_error": h_err,
        "config_hash": "aabbccddeeff",
        "runner_git_sha": "deadbeefcafe",
    }


class LiveLogReproductionTest(unittest.TestCase):
    """Pin the ledger the quantisation conclusions cite, as of 2026-09-13."""

    def test_group_counts_reproduce(self):
        rows = qla.load_rows(qla.LOG_PATH)
        derived = qla.derive(rows)
        per_group = {tuple(k.split(" | ")): v for k, v in derived["per_group"].items()}
        self.assertEqual(qla.testwrite_rows(rows), qla.testwrite_rows(qla.load_rows(qla.LOG_PATH)))
        for key, (p, n) in qla.PINNED_GROUPS.items():
            got = per_group.get(key)
            self.assertIsNotNone(got, f"missing group {key}")
            self.assertEqual(
                (got["passes"], got["total"]),
                (p, n),
                f"ledger drifted for {key} — update pins + SUMMARY.md deliberately",
            )

    def test_aggregates_reproduce(self):
        rows = qla.load_rows(qla.LOG_PATH)
        derived = qla.derive(rows)
        for name, (p, n) in qla.PINNED_AGGREGATES.items():
            got = derived["aggregates"][name]
            self.assertEqual(
                (got["passes"], got["total"]),
                (p, n),
                f"aggregate {name} drifted — update pins + SUMMARY.md deliberately",
            )

    def test_check_passes_on_live_log(self):
        rows = qla.load_rows(qla.LOG_PATH)
        derived = qla.derive(rows)
        self.assertEqual(qla.check_pins(derived), [])


class SyntheticLogTest(unittest.TestCase):
    """Logic checks on a hand-built log, independent of the live file."""

    def _write(self, rows):
        fd = tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False)
        self.addCleanup(Path(fd.name).unlink, missing_ok=True)
        for r in rows:
            fd.write(json.dumps(r) + "\n")
        fd.close()
        return Path(fd.name)

    def test_counting_and_scoping(self):
        # One pass + one fail for stock 4-bit, one fail for DWQ, one llama.cpp row.
        rows = [
            _row("mlx-community/Qwen3.6-35B-A3B-4bit", "mei", True),
            _row("mlx-community/Qwen3.6-35B-A3B-4bit", "mei", False),
            _row("mlx-community/Qwen3.6-35B-A3B-4bit-DWQ", "mei", False),
            _row("ornith-ai/Ornith-1.5-35B-A3B-GGUF:Q4_K_M", "llama.cpp", True),
            # non-testwrite task must not count
            _row("mlx-community/Qwen3.6-35B-A3B-4bit", "mei", True, task="kiem_mini-rename"),
            # harness-error row still counts (it is a model/engine result)
            _row("mlx-community/Qwen3.6-35B-A3B-4bit", "mei", False, h_err=True),
        ]
        derived = qla.derive(qla.load_rows(self._write(rows)))

        self.assertEqual(derived["log_rows"], 6)
        self.assertEqual(derived["testwrite_rows"], 5)

        stock = derived["per_group"].get("mlx-community/Qwen3.6-35B-A3B-4bit | mei")
        assert stock is not None
        self.assertEqual((stock["passes"], stock["total"], stock["harness_errors"]), (1, 3, 1))

        # DWQ is NOT a uniform-4-bit member even though it is Mei.
        four_bit = derived["aggregates"]["mlx_uniform_4bit"]
        self.assertEqual((four_bit["passes"], four_bit["total"]), (1, 3))
        all_mei = derived["aggregates"]["all_mei"]
        self.assertEqual((all_mei["passes"], all_mei["total"]), (1, 4))

    def test_scope_excludes_mixed_quants(self):
        rows = [
            _row("mlx-community/Qwen3.6-35B-A3B-4bit-DWQ", "mei", True),
            _row("EigenLabs/Qwen3.6-35B-A3B-MLX-mixed-4bit", "mei", True),
            _row("mlx-community/Qwen3.5-9B-8bit", "mei", True),
        ]
        derived = qla.derive(qla.load_rows(self._write(rows)))
        self.assertEqual(derived["aggregates"]["mlx_uniform_4bit"]["total"], 0)
        self.assertEqual(derived["aggregates"]["all_mei"]["total"], 3)

    def test_check_detects_drift(self):
        rows = [_row("mlx-community/Qwen3.6-35B-A3B-4bit", "mei", True)]
        derived = qla.derive(qla.load_rows(self._write(rows)))
        self.assertNotEqual(qla.check_pins(derived), [])


if __name__ == "__main__":
    unittest.main()