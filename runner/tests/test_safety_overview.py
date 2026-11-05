"""Repeated quality must retain safety failures and both complete runs."""

import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from build_safety_overview import aggregate


class SafetyOverviewTests(unittest.TestCase):
    def test_critical_failure_is_retained_in_equal_coverage_average(self):
        household = {
            "runtime_identity": {"binary": "same"},
            "passed": 12,
            "critical": 0,
            "rows": [{"wall_seconds": 2.0}] * 12,
        }
        python = {"passed": 3, "rows": [{"wall_seconds": 4.0}] * 3}
        other = copy.deepcopy(household)
        other.update(passed=11, critical=1)
        python2 = copy.deepcopy(python)
        python2["passed"] = 2
        result = aggregate(
            "model",
            "MiniCPM",
            [
                (household, python, ("profile",), ("hash",)),
                (other, python2, ("profile",), ("hash",)),
            ],
        )
        self.assertEqual(
            (
                result["household_passes"],
                result["python_passes"],
                result["critical_failures"],
            ),
            (23, 5, 1),
        )
        self.assertAlmostEqual(result["mean_task_seconds"], 2.4)

    def test_incomplete_or_changed_profile_cannot_be_averaged(self):
        h = {
            "runtime_identity": {"binary": "same"},
            "passed": 12,
            "critical": 0,
            "rows": [{"wall_seconds": 1}] * 12,
        }
        p = {"passed": 3, "rows": [{"wall_seconds": 1}] * 3}
        with self.assertRaises(ValueError):
            aggregate("m", "M", [(h, p, ("a",), ("hash",)), (h, p, ("b",), ("hash",))])
        p["rows"].pop()
        with self.assertRaises(ValueError):
            aggregate("m", "M", [(h, p, ("a",), ("hash",)), (h, p, ("a",), ("hash",))])
