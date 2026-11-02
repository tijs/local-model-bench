"""Plot costs must use recorded wired bytes and complete comparable observations."""

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from build_four_model_summary import COLORS, GIB, load_points, memory_cost, wired_bytes


def sample(pages):
    return {
        "host_vm_stat": f"Mach Virtual Memory Statistics: (page size of 16384 bytes)\nPages wired down: {pages}.\n",
        "resident_bytes": 999999999999,
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
                (self.root / entry["config"]).write_text('{"model_bytes": 1000000}')
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
                        {"run_id": entry[key], "pass": True} for _ in range(n)
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

    def test_incomplete_rows_refused(self):
        path = self.root / "results/automation/log.jsonl"
        path.write_text("\n".join(path.read_text().splitlines()[:-1]) + "\n")
        with self.assertRaises(ValueError):
            self.load()


if __name__ == "__main__":
    unittest.main()
