"""Plot costs must use recorded wired bytes and complete comparable observations."""

import json
import sys
import tempfile
import unittest
from dataclasses import asdict, replace
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from build_four_model_summary import (
    COLORS,
    GIB,
    aggregate_points,
    export,
    load_points,
    memory_cost,
    wired_bytes,
)


def sample(pages):
    return {
        "host_vm_stat": f"Mach Virtual Memory Statistics: (page size of 16384 bytes)\nPages wired down: {pages}.\n",
        "resident_bytes": 999999999999,
        "kernel_pressure_level": 1,
        "swap_used_mib": 1024,
        "disk_free_bytes": 20 * GIB,
        "free_percent": 30,
    }


class WiredMemoryTests(unittest.TestCase):
    def test_page_size_and_median_baseline_not_process_rss(self):
        self.assertEqual(wired_bytes(sample(1234)), 1234 * 16384)
        base, peak, increase = memory_cost(
            [sample(100), sample(500), sample(110)], [sample(250), sample(300)]
        )
        self.assertEqual(base, 110 * 16384 / GIB)
        self.assertEqual(peak, 300 * 16384 / GIB)
        assert increase is not None
        self.assertAlmostEqual(increase, 190 * 16384 / GIB)

    def test_negative_host_delta_is_unavailable_not_free_model(self):
        self.assertIsNone(memory_cost([sample(500)], [sample(200)])[2])

    def test_missing_samples_or_counters_fail_loudly(self):
        for base, run in (([], [sample(1)]), ([sample(1)], []), ([{}], [sample(1)])):
            with (
                self.subTest(base=base, run=run),
                self.assertRaises((ValueError, KeyError)),
            ):
                memory_cost(base, run)


class ComparisonCoverageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.spec = {
            "models": {str(i): name for i, name in enumerate(COLORS)},
            "seeds": [17, 29],
            "cohorts": ["seed17.json", "seed29.json"],
            "benchmark_release": "fixture",
            "release_commit": "a" * 40,
        }
        logs = {"standin": [], "automation": []}
        self.manifests = []
        for seed in (17, 29):
            cohort = {
                "benchmark_release": "fixture",
                "release_commit": "a" * 40,
                "trials": 1,
                "models": [],
            }
            for i in range(4):
                stem = f"model{i}-seed{seed}"
                entry = {
                    "model": str(i),
                    "engine": "llama.cpp" if i == 3 else "mei",
                    "household_run": stem + "-h",
                    "python_run": stem + "-p",
                    "config": stem + ".yaml",
                    "supervision": stem,
                }
                (self.root / entry["config"]).write_text(
                    '{"model_bytes": 1000000, "resource_monitor_policy": {"admission_mode": "capacity"}}'
                )
                for folder, key, n in (
                    ("standin", "household_run", 12),
                    ("automation", "python_run", 3),
                ):
                    directory = self.root / "results" / folder / "runs" / entry[key]
                    directory.mkdir(parents=True)
                    manifest = directory / "manifest.json"
                    manifest.write_text(
                        json.dumps(
                            {
                                "status": "completed",
                                "generation_overrides": {"seed": seed},
                                "runtime_identity": {"binary": str(i)},
                            }
                        )
                    )
                    self.manifests.append(manifest)
                    logs[folder] += [
                        {"run_id": entry[key], "pass": True, "wall_seconds": 10}
                        for _ in range(n)
                    ]
                directory = self.root / stem
                directory.mkdir()
                (directory / "outcome.json").write_text(
                    json.dumps(
                        {"returncode": 0, "stop_reason": None, "elapsed_seconds": 600}
                    )
                )
                (directory / "baseline.jsonl").write_text(
                    json.dumps(sample(100)) + "\n"
                )
                (directory / "invocation.json").write_text(
                    json.dumps({"initial": sample(100)})
                )
                (directory / "resources.jsonl").write_text(
                    json.dumps(sample(300)) + "\n"
                )
                cohort["models"].append(entry)
            (self.root / f"seed{seed}.json").write_text(json.dumps(cohort))
        for folder, rows in logs.items():
            (self.root / "results" / folder / "log.jsonl").write_text(
                "".join(json.dumps(x) + "\n" for x in rows)
            )

    def load(self):
        # Frozen-source/row integrity is independently tested by the existing
        # comparison reader; this fixture isolates added coverage/cost guards.
        with patch("build_four_model_summary.render_campaign"):
            return load_points(self.root, self.spec)

    def test_exactly_eight_observations_with_engine_and_cost(self):
        points = self.load()
        self.assertEqual(len(points), 8)
        self.assertEqual({p.engine for p in points}, {"mei", "llama.cpp"})
        self.assertTrue(all(p.household == 12 and p.python == 3 for p in points))
        self.assertTrue(all(p.wall_minutes == 10 for p in points))
        self.assertTrue(all(p.task_seconds == 10 for p in points))

    def test_task_duration_includes_failures_and_both_tracks_with_equal_run_weight(
        self,
    ):
        for folder in ("standin", "automation"):
            path = self.root / "results" / folder / "log.jsonl"
            rows = [json.loads(line) for line in path.read_text().splitlines()]
            for row in rows:
                if row["run_id"].startswith("model0-seed17"):
                    row.update(
                        wall_seconds=20 if folder == "standin" else 100,
                        **{"pass": False},
                    )
                elif row["run_id"].startswith("model0-seed29"):
                    row["wall_seconds"] = 8 if folder == "standin" else 48
            path.write_text("".join(json.dumps(row) + "\n" for row in rows))
        points = self.load()
        self.assertEqual(points[0].task_seconds, 36)
        self.assertEqual(points[1].task_seconds, 16)
        self.assertEqual(aggregate_points(points)[0].task_seconds, 26)
        self.assertEqual(points[0].household, 0)
        self.assertEqual(points[0].python, 0)

    def test_task_duration_refuses_missing_or_invalid_attempt_times(self):
        path = self.root / "results/automation/log.jsonl"
        rows = [json.loads(line) for line in path.read_text().splitlines()]
        for bad in (None, True, -1, 0, float("nan"), float("inf"), "10"):
            with self.subTest(bad=bad):
                rows[0]["wall_seconds"] = bad
                path.write_text("".join(json.dumps(row) + "\n" for row in rows))
                with self.assertRaisesRegex(ValueError, "positive finite wall time"):
                    self.load()

    def test_repeats_pool_task_quality_and_average_costs(self):
        points = self.load()
        points[0] = replace(
            points[0], household=9, python=2, wall_minutes=8, wired_increase_gib=18
        )
        points[1] = replace(
            points[1], household=11, python=3, wall_minutes=12, wired_increase_gib=22
        )
        averages = aggregate_points(list(reversed(points)))
        self.assertEqual(len(averages), 4)
        first = averages[0]
        self.assertEqual(first.label, "Base Qwen3.6")
        self.assertEqual((first.seeds, first.run_weights), ((17, 29), (0.5, 0.5)))
        self.assertEqual((first.household_passed, first.household_attempts), (20, 24))
        self.assertEqual((first.python_passed, first.python_attempts), (5, 6))
        self.assertAlmostEqual(first.household_success_percent, 100 * 20 / 24)
        self.assertAlmostEqual(first.python_success_percent, 100 * 5 / 6)
        self.assertEqual(first.wall_minutes, 10)
        self.assertEqual(first.wired_increase_gib, 20)
        self.assertEqual(
            [p.engine for p in averages], ["mei", "mei", "mei", "llama.cpp"]
        )

    def test_missing_memory_does_not_silently_drop_a_repeat(self):
        points = self.load()
        points[0] = replace(points[0], wired_increase_gib=None)
        first = aggregate_points(points)[0]
        self.assertIsNone(first.wired_increase_gib)
        self.assertEqual(first.runs, 2)
        self.assertEqual(first.household_attempts, 24)

    def test_averages_reject_missing_duplicate_or_mixed_profiles(self):
        points = self.load()
        for invalid in (
            points[:-1],
            [points[0], *points[:-1]],
            [replace(points[0], engine="llama.cpp"), *points[1:]],
            [replace(points[0], weight_gib=99), *points[1:]],
        ):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                aggregate_points(invalid)

    def test_export_keeps_all_observations_and_adds_four_model_averages(self):
        original = [asdict(p) for p in self.load()]
        output = self.root / "results/charts"
        output.mkdir()
        with (
            patch("build_four_model_summary.render_campaign"),
            patch("build_four_model_summary.figures", return_value=[]),
        ):
            export(self.root, self.spec, self.root / "results/SUMMARY.md", output)
        data = json.loads((output / "metrics.json").read_text())
        self.assertEqual(data["observations"], original)
        self.assertEqual(len(data["model_averages"]), 4)
        self.assertEqual(data["aggregation"]["run_weights"], {"17": 0.5, "29": 0.5})
        self.assertEqual(len((output / "metrics.csv").read_text().splitlines()), 9)
        self.assertEqual(
            len((output / "model-averages.csv").read_text().splitlines()), 5
        )

    def test_mismatched_seed_and_changed_runtime_refused(self):
        path = self.manifests[-1]
        original = json.loads(path.read_text())
        for change in (
            {"generation_overrides": {"seed": 17}},
            {"runtime_identity": {"binary": "other"}},
            {"status": "interrupted"},
        ):
            with self.subTest(change=change):
                path.write_text(json.dumps({**original, **change}))
                with self.assertRaises(ValueError):
                    self.load()
        path.write_text(json.dumps(original))

    def test_critical_boundary_failure_is_not_a_qualified_point(self):
        path = self.root / "results/standin/log.jsonl"
        rows = [json.loads(line) for line in path.read_text().splitlines()]
        rows[0]["critical_safety_failure"] = True
        path.write_text("".join(json.dumps(row) + "\n" for row in rows))
        with self.assertRaisesRegex(ValueError, "Critical boundary"):
            self.load()

    def test_duplicate_seed_cohort_is_rejected(self):
        self.spec["cohorts"] = ["seed17.json", "seed17.json"]
        with self.assertRaisesRegex(ValueError, "duplicate"):
            self.load()

    def test_resource_stop_conditions_refused_even_with_zero_exit(self):
        path = self.root / "model0-seed17/resources.jsonl"
        for changes in (
            [{"kernel_pressure_level": 4}],
            [{"kernel_pressure_level": 2}, {"kernel_pressure_level": 2}],
            [{"swap_used_mib": 3073}],
            [{"disk_free_bytes": 9 * GIB}],
        ):
            with self.subTest(changes=changes):
                path.write_text(
                    "".join(json.dumps({**sample(300), **x}) + "\n" for x in changes)
                )
                with self.assertRaisesRegex(ValueError, "Resource-ineligible"):
                    self.load()
        # An isolated warning is explicitly permitted by the capacity policy.
        path.write_text(json.dumps({**sample(300), "kernel_pressure_level": 2}) + "\n")
        self.assertEqual(len(self.load()), 8)

    def test_incomplete_rows_refused(self):
        path = self.root / "results/automation/log.jsonl"
        path.write_text("\n".join(path.read_text().splitlines()[:-1]) + "\n")
        with self.assertRaises(ValueError):
            self.load()


if __name__ == "__main__":
    unittest.main()
