"""Focused regression tests for runner/plot_leaderboard.py.

Run: uv run --locked python -m unittest runner.tests.test_plot_leaderboard -v

These tests never write to the repo's real results/ directory: any renderer is
pointed at a tempdir via mocked pyplot, so no PNG is produced on disk. The
regression they pin: the chart's axis label must be DERIVED from
build_leaderboard.CODING_SCORE_WEIGHTS, not a hardcoded copy of the formula --
2026-09-09 the scored "time" axis was replaced by "ttft" but the chart kept
labeling the axis "time 20%" until this fix. Same for the gate legend
threshold, which must track GATE_HERMES_OPS_THRESHOLD.
"""
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import plot_leaderboard as pl  # noqa: E402
import build_leaderboard as bl  # noqa: E402

_WEIGHTS = bl.CODING_SCORE_WEIGHTS
_THRESHOLD = bl.GATE_HERMES_OPS_THRESHOLD


class ScoreAxisLabelTests(unittest.TestCase):
    def test_label_lists_current_axes_with_weights(self):
        label = pl._score_axis_label()
        # Every axis currently scored must appear in the label...
        for axis, weight in _WEIGHTS.items():
            self.assertIn(f"{axis} {weight:.0%}", label, axis)
        # ...and the stale "time" axis (replaced by ttft 2026-09-09) must not.
        self.assertNotIn("time 20%", label)
        self.assertIn("ttft", label)

    def test_label_tracks_weight_changes_through_patch(self):
        # The whole point of deriving the label: if CODING_SCORE_WEIGHTS
        # changes shape, the label follows instead of silently lying about
        # what was scored.
        patched = {"pass": 0.4, "speed": 0.3, "ttft": 0.2, "turns": 0.1}
        with mock.patch.object(pl, "CODING_SCORE_WEIGHTS", patched):
            label = pl._score_axis_label()
        self.assertIn("pass 40%", label)
        self.assertIn("speed 30%", label)
        self.assertIn("ttft 20%", label)
        self.assertIn("turns 10%", label)
        self.assertNotIn("time", label)


class GateLegendThresholdTests(unittest.TestCase):
    def test_render_chart_legend_uses_threshold_constant(self):
        # A mocked axes captures the legend labels; the PASS handle must carry
        # the CURRENT gate threshold, not a hardcoded "≥ 50%".
        captured = {}

        fake_fig = mock.MagicMock(name="fig")
        fake_ax = mock.MagicMock(name="ax")
        fake_ax.barh.return_value = []  # no bars -> no per-bar text calls
        fake_ax.legend.side_effect = lambda **kw: captured.update(
            labels=[h.get_label() for h in kw["handles"]])

        with mock.patch.object(pl.plt, "subplots", return_value=(fake_fig, fake_ax)):
            pl.render_chart([{
                "label": "m (mei, Q4_K_M)", "model": "m",
                "gate_pass": True, "score": 0.5, "coding_pass_rate": 1.0,
                "n_coding": 1, "avg_tps_val": 1.0,
            }], "unused.png")

        self.assertTrue(any(
            f"hermes_ops ≥ {_THRESHOLD:.0%}" in lab for lab in captured["labels"]), captured)
        self.assertTrue(any("ranked below all gate-passers" in lab
                            for lab in captured["labels"]), captured)


if __name__ == "__main__":
    unittest.main()