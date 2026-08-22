"""Regression tests for runner/run_bench.py's speed gate.

Run: uv run --locked python -m unittest discover -s runner/tests -v
"""
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import run_bench as rb


class SpeedGateRetryTests(unittest.TestCase):
    """_check_speed_gate must retry exactly once on a below-threshold probe
    before failing the gate — grounded in real historical data
    (results/log.jsonl) showing a single noisy trial can dip this low on
    an otherwise-fine model (mlx-community/Qwen3-Coder-30B-A3B-Instruct-
    4bit: one 0.15 tok/s hermes_ops-selection outlier against a typical
    7-8 tok/s on the same task) — only two consecutive below-threshold
    results should be treated as a genuine gate failure."""

    def _fake_probe(self, sequence):
        it = iter(sequence)

        def _probe(base_url, model, request_model, backend, config_path):
            return next(it)

        return _probe

    def test_second_attempt_recovering_passes_the_gate(self):
        with patch.object(rb, "_run_hermes_ops_probe", side_effect=self._fake_probe([[0.2], [5.0]])):
            passed, measured = rb._check_speed_gate("http://x", "m", "m", "mlx", Path("c.yaml"))
        self.assertTrue(passed)
        self.assertEqual(measured, [0.2, 5.0])

    def test_two_consecutive_low_attempts_fails_the_gate(self):
        with patch.object(rb, "_run_hermes_ops_probe", side_effect=self._fake_probe([[0.18], [0.22]])):
            passed, measured = rb._check_speed_gate("http://x", "m", "m", "mlx", Path("c.yaml"))
        self.assertFalse(passed)
        self.assertEqual(measured, [0.18, 0.22])

    def test_first_attempt_at_or_above_threshold_never_retries(self):
        calls = []

        def _probe(base_url, model, request_model, backend, config_path):
            calls.append(1)
            return [3.0]

        with patch.object(rb, "_run_hermes_ops_probe", side_effect=_probe):
            passed, measured = rb._check_speed_gate("http://x", "m", "m", "mlx", Path("c.yaml"))
        self.assertTrue(passed)
        self.assertEqual(len(calls), 1)

    def test_probe_producing_no_data_does_not_fail_the_gate(self):
        # A harness crash on the probe isn't evidence the MODEL is slow —
        # the real hermes_ops run right after will surface whatever this
        # actually is, so this must not be treated as a gate failure.
        with patch.object(rb, "_run_hermes_ops_probe", return_value=None):
            passed, measured = rb._check_speed_gate("http://x", "m", "m", "mlx", Path("c.yaml"))
        self.assertTrue(passed)
        self.assertIsNone(measured)

    def test_exactly_at_threshold_passes(self):
        with patch.object(rb, "_run_hermes_ops_probe", return_value=[rb.MIN_HERMES_OPS_TOKENS_PER_SECOND]):
            passed, measured = rb._check_speed_gate("http://x", "m", "m", "mlx", Path("c.yaml"))
        self.assertTrue(passed)


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
        rb._record_speed_gate_failure("m", "mlx", Path("configs/m/mlx.yaml"), "hash123", [0.18, 0.22])
        rows = [json.loads(l) for l in (self.repo / "results" / "speed_gate.jsonl").read_text().splitlines()]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["model"], "m")
        self.assertEqual(rows[0]["measured_tokens_per_second"], [0.18, 0.22])
        self.assertEqual(rows[0]["threshold_tokens_per_second"], rb.MIN_HERMES_OPS_TOKENS_PER_SECOND)

    def test_appends_rather_than_overwrites(self):
        rb._record_speed_gate_failure("m1", "mlx", Path("c1.yaml"), "h1", [0.1])
        rb._record_speed_gate_failure("m2", "gguf", Path("c2.yaml"), "h2", [0.2])
        rows = [json.loads(l) for l in (self.repo / "results" / "speed_gate.jsonl").read_text().splitlines()]
        self.assertEqual(len(rows), 2)


if __name__ == "__main__":
    unittest.main()
