"""Regression tests for runner/build_leaderboard.py.

Run: uv run --locked python -m unittest discover -s runner/tests -v
"""
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import build_leaderboard as bl


class HarnessErrorExclusionTests(unittest.TestCase):
    """CR3-6: harness_error rows (a genuine harness crash, e.g. an npm ci
    network blip — not a model failure) used to be counted exactly like
    a real trial everywhere: the main table's pass rate, the by-suite
    table, and the flaky-task grouping. Confirmed live with a synthetic
    2-pass/1-harness-crash group: pass rate read 67% (should be 100%,
    2/2 real trials) and the task was wrongly flagged "Flaky" (2/3)."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.repo = Path(self.tmp)
        (self.repo / "results").mkdir()
        self._orig_repo = bl.REPO
        bl.REPO = self.repo

    def tearDown(self):
        bl.REPO = self._orig_repo
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _write_log(self, rows):
        (self.repo / "results" / "log.jsonl").write_text(
            "\n".join(json.dumps(r) for r in rows) + "\n"
        )

    def _base_row(self, **overrides):
        row = {
            "suite": "hermes_ops",
            "task_id": "hermes_ops-selection",
            "task_type": "tool-selection",
            "model": "test-model",
            "backend": "mlx",
            "quant": None,
            "config_path": None,
            "config_hash": None,
            "runner_git_sha": "abc123",
            "trial": 1,
            "pass": True,
            "grade_output": "PASS",
        }
        row.update(overrides)
        return row

    def test_harness_error_row_excluded_from_pass_rate(self):
        self._write_log([
            self._base_row(trial=1, **{"pass": True}),
            self._base_row(trial=2, **{"pass": True}),
            self._base_row(trial=3, **{"pass": False, "harness_error": True}),
        ])
        bl.main()
        text = (self.repo / "results" / "LEADERBOARD.md").read_text()
        self.assertIn("| test-model | mlx | — | — | — | — | abc123 | 2 | 100% |", text)

    def test_harness_error_row_not_flagged_as_flaky(self):
        self._write_log([
            self._base_row(trial=1, **{"pass": True}),
            self._base_row(trial=2, **{"pass": True}),
            self._base_row(trial=3, **{"pass": False, "harness_error": True}),
        ])
        bl.main()
        text = (self.repo / "results" / "LEADERBOARD.md").read_text()
        flaky_section = text[text.index("## Flaky tasks"):text.index("## By suite")]
        self.assertIn("None observed", flaky_section)

    def test_harness_error_row_surfaced_in_own_section(self):
        self._write_log([
            self._base_row(trial=1, **{"pass": True}),
            self._base_row(trial=3, **{"pass": False, "harness_error": True, "grade_output": "HARNESS ERROR: network blip"}),
        ])
        bl.main()
        text = (self.repo / "results" / "LEADERBOARD.md").read_text()
        harness_section = text[text.index("## Harness errors"):]
        self.assertIn("network blip", harness_section)

    def test_genuine_flakiness_still_detected(self):
        # Regression guard: excluding harness_error rows must not also
        # suppress REAL model flakiness (a genuine pass/fail split with no
        # harness_error involved).
        self._write_log([
            self._base_row(trial=1, **{"pass": True}),
            self._base_row(trial=2, **{"pass": False}),
        ])
        bl.main()
        text = (self.repo / "results" / "LEADERBOARD.md").read_text()
        flaky_section = text[text.index("## Flaky tasks"):text.index("## By suite")]
        self.assertIn("hermes_ops-selection", flaky_section)
        self.assertIn("1/2", flaky_section)

    def test_omlx_factors_are_visible_and_not_called_full_fp16(self):
        cfg = self.repo / "configs" / "qwen" / "omlx-mtp.yaml"
        cfg.parent.mkdir(parents=True)
        cfg.write_text(
            "framework: omlx\nquant_family: oQ4e-fp16 mixed precision\n"
            "cache_mode: ssd-warm\nmtp_mode: lightning\n"
            "temperature: 1\nreasoning_mode: medium\n"
        )
        import hashlib
        config_hash = hashlib.sha256(cfg.read_bytes()).hexdigest()[:12]
        self._write_log([self._base_row(
            model="qwen", backend="omlx", config_path="configs/qwen/omlx-mtp.yaml",
            config_hash=config_hash,
        )])
        bl.main()
        text = (self.repo / "results" / "LEADERBOARD.md").read_text()
        self.assertIn("| omlx | oQ4e-fp16 mixed precision | ssd-warm | lightning |", text)


class PeakRssColumnTests(unittest.TestCase):
    """F7: peak RSS is reported as the MAX across a group's rows, not an
    average — the 32GB unified-memory ceiling is a hard capacity limit,
    so the worst observed footprint is what matters for "does this fit,"
    not a smoothed mean that could hide a run that came close to
    swapping."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.repo = Path(self.tmp)
        (self.repo / "results").mkdir()
        self._orig_repo = bl.REPO
        bl.REPO = self.repo

    def tearDown(self):
        bl.REPO = self._orig_repo
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _write_log(self, rows):
        (self.repo / "results" / "log.jsonl").write_text(
            "\n".join(json.dumps(r) for r in rows) + "\n"
        )

    def _base_row(self, **overrides):
        row = {
            "suite": "hermes_ops", "task_id": "hermes_ops-selection",
            "task_type": "tool-selection", "model": "test-model", "backend": "mlx",
            "quant": None, "config_path": None, "config_hash": None,
            "runner_git_sha": "abc123", "trial": 1, "pass": True, "grade_output": "PASS",
        }
        row.update(overrides)
        return row

    def test_peak_rss_reports_the_max_not_the_average(self):
        self._write_log([
            self._base_row(trial=1, peak_rss_gb=18.2),
            self._base_row(trial=2, peak_rss_gb=25.9),
        ])
        bl.main()
        text = (self.repo / "results" / "LEADERBOARD.md").read_text()
        # 25.9 (the max) must appear; the average (22.05) must not be what's shown.
        self.assertIn("25.9", text)
        self.assertNotIn("22.1", text)

    def test_peak_rss_blank_when_never_measured(self):
        self._write_log([self._base_row(trial=1)])  # no peak_rss_gb key at all
        bl.main()
        text = (self.repo / "results" / "LEADERBOARD.md").read_text()
        row_line = next(l for l in text.splitlines() if l.startswith("| test-model |"))
        self.assertIn("| — |", row_line)


if __name__ == "__main__":
    unittest.main()
