"""Regression tests for runner/run_bench.py's speed gate.

Run: uv run --locked python -m unittest discover -s runner/tests -v
"""
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import run_bench as rb


class HermesOpsTpsValuesTests(unittest.TestCase):
    """_hermes_ops_tps_values reads tokens_per_second from a hermes_ops
    --summary-out file — every task actually run, not one probe task (see
    MIN_HERMES_OPS_TOKENS_PER_SECOND's own comment for why a single-task
    probe was tried and rejected: the smallest-completion task reads
    systematically low even for genuinely fast models)."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _summary(self, rows):
        p = Path(self.tmp) / "summary.json"
        p.write_text(json.dumps(rows))
        return p

    def test_reads_every_row_tokens_per_second(self):
        p = self._summary([
            {"task_id": "hermes_ops-selection", "tokens_per_second": 5.0},
            {"task_id": "hermes_ops-chaining", "tokens_per_second": 7.0},
        ])
        self.assertEqual(rb._hermes_ops_tps_values(p), [5.0, 7.0])

    def test_harness_error_rows_excluded(self):
        # A harness crash on one task isn't evidence about the MODEL's
        # speed — same exclusion build_leaderboard.py's avg tok/s uses.
        p = self._summary([
            {"task_id": "hermes_ops-selection", "tokens_per_second": 5.0},
            {"task_id": "hermes_ops-chaining", "tokens_per_second": None, "harness_error": True},
        ])
        self.assertEqual(rb._hermes_ops_tps_values(p), [5.0])

    def test_missing_summary_file_returns_none(self):
        # Don't gate on nothing — a harness crash that prevented the
        # summary from being written isn't evidence the model is slow.
        self.assertIsNone(rb._hermes_ops_tps_values(Path(self.tmp) / "missing.json"))

    def test_unparseable_summary_returns_none(self):
        p = Path(self.tmp) / "bad.json"
        p.write_text("not json")
        self.assertIsNone(rb._hermes_ops_tps_values(p))

    def test_all_rows_missing_tokens_per_second_returns_none(self):
        p = self._summary([{"task_id": "hermes_ops-selection", "tokens_per_second": None}])
        self.assertIsNone(rb._hermes_ops_tps_values(p))


class SpeedGateFailureRecordTests(unittest.TestCase):
    """_record_speed_gate_failure writes to results/speed_gate.jsonl, a
    dedicated append-only log kept separate from log.jsonl (whose task/
    suite-keyed schema every grouping/flakiness check in
    build_leaderboard.py assumes) and separate from the config YAML files
    (which stay hand-authored, not rewritten by this automated check)."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.repo = Path(self.tmp)
        (self.repo / "results").mkdir()
        self._orig_repo = rb.REPO
        rb.REPO = self.repo

    def tearDown(self):
        rb.REPO = self._orig_repo
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_writes_one_jsonl_row_with_expected_fields(self):
        rb._record_speed_gate_failure(
            "m", "mlx", Path("configs/m/mlx.yaml"), "hash123", [0.18, 0.22, 0.31], 0.237,
        )
        rows = [json.loads(l) for l in (self.repo / "results" / "speed_gate.jsonl").read_text().splitlines()]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["model"], "m")
        self.assertEqual(rows[0]["measured_tokens_per_second"], [0.18, 0.22, 0.31])
        self.assertEqual(rows[0]["avg_tokens_per_second"], 0.237)
        self.assertEqual(rows[0]["threshold_tokens_per_second"], rb.MIN_HERMES_OPS_TOKENS_PER_SECOND)

    def test_appends_rather_than_overwrites(self):
        rb._record_speed_gate_failure("m1", "mlx", Path("c1.yaml"), "h1", [0.1], 0.1)
        rb._record_speed_gate_failure("m2", "gguf", Path("c2.yaml"), "h2", [0.2], 0.2)
        rows = [json.loads(l) for l in (self.repo / "results" / "speed_gate.jsonl").read_text().splitlines()]
        self.assertEqual(len(rows), 2)


class MinTokensPerSecondValueTests(unittest.TestCase):
    """Guards the actual cutoff value — a deliberate user decision (10
    tok/s), not something that should silently drift back to the earlier
    1.0 tok/s bar this replaced."""

    def test_threshold_is_ten(self):
        self.assertEqual(rb.MIN_HERMES_OPS_TOKENS_PER_SECOND, 10.0)


if __name__ == "__main__":
    unittest.main()
