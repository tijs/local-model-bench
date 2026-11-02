"""Paired TPS figures must retain balanced, exact-runtime context measurements."""

import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from context_speed_summary import (
    SpeedObservation,
    SpeedProfile,
    aggregate_context_speeds,
    context_speed_figure,
)


class ContextSpeedTests(unittest.TestCase):
    def setUp(self):
        self.profiles = [
            SpeedProfile(
                "Example", "mei", "a" * 64, "b" * 40, ("run1", "run2"), 17, 30000
            )
        ]
        self.rows = [
            SpeedObservation(
                "Example",
                process,
                "a" * 64,
                "b" * 40,
                context,
                repeat,
                tokens,
                128,
                speed,
            )
            for process, short, long in (("run1", 40.0, 20.0), ("run2", 60.0, 30.0))
            for context, tokens, speed in (("short", 17, short), ("long", 30000, long))
            for repeat in range(1, 6)
        ]

    def test_each_process_has_equal_weight_for_each_context(self):
        point = aggregate_context_speeds(self.profiles, self.rows)[0]
        self.assertEqual((point.short_tps, point.long_tps), (50, 25))
        self.assertEqual(point.process_weights, (0.5, 0.5))
        self.assertEqual(point.repeats_per_process, 5)

    def test_every_repeat_contributes_to_arithmetic_means(self):
        speeds = {
            ("run1", "short"): (10, 20, 30, 40, 100),
            ("run2", "short"): (20, 30, 40, 50, 160),
            ("run1", "long"): (2, 4, 6, 8, 30),
            ("run2", "long"): (5, 10, 15, 20, 100),
        }
        rows = [
            replace(r, decode_tps=speeds[r.process_id, r.context][r.repeat - 1])
            for r in self.rows
        ]
        point = aggregate_context_speeds(self.profiles, rows)[0]
        # Process means are 40/60 and 10/30. Medians or selected repeats differ.
        self.assertEqual((point.short_tps, point.long_tps), (50, 20))

    def test_missing_duplicate_or_extra_observations_refused(self):
        for rows in (
            self.rows[:-1],
            self.rows + [self.rows[0]],
            self.rows + [replace(self.rows[0], repeat=0)],
        ):
            with self.subTest(rows=len(rows)), self.assertRaises(ValueError):
                aggregate_context_speeds(self.profiles, rows)

    def test_wrong_runtime_model_context_or_generated_count_refused(self):
        for changes in (
            {"runtime_sha256": "c" * 64},
            {"model_revision": "c" * 40},
            {"prompt_tokens": 18},
            {"completion_tokens": 127},
            {"process_id": "undeclared"},
            {"repeat": True},
        ):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                aggregate_context_speeds(
                    self.profiles, [replace(self.rows[0], **changes), *self.rows[1:]]
                )

    def test_invalid_rates_refused_without_dropping_samples(self):
        for speed in (float("nan"), float("inf"), 0.0, -1.0, True):
            with self.subTest(speed=speed), self.assertRaises(ValueError):
                aggregate_context_speeds(
                    self.profiles,
                    [replace(self.rows[0], decode_tps=speed), *self.rows[1:]],
                )

    def test_context_lengths_and_processes_must_be_distinct_and_pinned(self):
        for changes in (
            {"process_ids": ("run1", "run1")},
            {"short_tokens": 30000},
            {"runtime_sha256": "unpinned"},
        ):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                aggregate_context_speeds(
                    [replace(self.profiles[0], **changes)], self.rows
                )
        with self.assertRaisesRegex(ValueError, "lengths must match"):
            aggregate_context_speeds(
                [
                    *self.profiles,
                    replace(self.profiles[0], model="Other", long_tokens=20000),
                ],
                self.rows,
            )

    def test_exports_actual_token_counts_and_both_means_in_svg(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "paired"
            points = aggregate_context_speeds(self.profiles, self.rows)
            context_speed_figure(
                points,
                target,
                title="Controlled decode",
                provenance="Fixture only",
                colors={"Example": "#2378b5"},
            )
            svg = target.with_suffix(".svg").read_text()
            for label in (
                "17 tokens",
                "30,000 tokens",
                "50.0 TPS",
                "25.0 TPS",
                "Fixture only",
            ):
                self.assertIn(label, svg)
            self.assertTrue(target.with_suffix(".png").is_file())

    def test_preview_collision_rejected_before_loading_or_rendering(self):
        artifact = (
            Path(__file__).resolve().parents[2]
            / "artifacts/mei-stable-qualification-20261102"
        )
        sys.path.insert(0, str(artifact))
        import preview_context_speed

        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            for ext in (".png", ".svg", ".json"):
                with self.subTest(existing=ext):
                    old = folder / ("context-speed-layout-preview" + ext)
                    old.write_bytes(b"preserved")
                    with (
                        patch.object(preview_context_speed, "PREP", folder),
                        patch.object(
                            preview_context_speed, "context_speed_figure"
                        ) as render,
                    ):
                        with self.assertRaises(FileExistsError):
                            preview_context_speed.main()
                        render.assert_not_called()
                    self.assertEqual(old.read_bytes(), b"preserved")
                    old.unlink()


if __name__ == "__main__":
    unittest.main()
