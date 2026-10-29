"""Resource supervisor declines unsafe launches and records terminal outcomes."""

import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import supervise_bench as monitor


def sample(free=90, pressure=1, swap=0.0, disk=50 * 1024**3):
    return {
        "time": "2026-10-29T20:00:00+00:00",
        "free_percent": free,
        "kernel_pressure_level": pressure,
        "swap_used_mib": swap,
        "disk_free_bytes": disk,
        "owned_processes": [],
    }


class ResourceSupervisorTests(unittest.TestCase):
    def setUp(self):
        source = patch.object(monitor, "git_sha", return_value="1" * 12)
        source.start()
        self.addCleanup(source.stop)

    def test_registered_run_ids_match_nonce_config_and_scope(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for index, identifier in enumerate(("a" * 32, "b" * 32)):
                path = root / "results/automation/runs" / str(index) / "manifest.json"
                path.parent.mkdir(parents=True)
                path.write_text(
                    json.dumps(
                        {
                            "supervision_id": identifier,
                            "config_hash": "cfg",
                            "benchmark_scope": "python-automation-v1",
                            "run_id": f"run{index}",
                        }
                    )
                )
            with patch.object(monitor, "REPO", root):
                result = monitor.observed_run_ids("a" * 32, "cfg")
            self.assertEqual(result["python-automation-v1"], ["run0"])
            self.assertEqual(result["peixinho-standin-v1"], [])

    def test_all_stop_conditions_remain_independent(self):
        initial = sample()
        for current, low, warnings in [
            (sample(pressure=4), 0, 0),
            (sample(pressure=2), 0, 2),
            (sample(free=10), 2, 0),
            (sample(swap=2048), 0, 0),
            (sample(swap=16384), 0, 0),
            (sample(disk=9 * 1024**3), 0, 0),
        ]:
            with self.subTest(current=current):
                self.assertIsNotNone(
                    monitor.gate_reason(current, initial, low, warnings)
                )
        self.assertIsNone(monitor.gate_reason(sample(pressure=2), initial, 0, 1))
        self.assertIsNone(monitor.gate_reason(sample(), initial, 0, 0))

    def test_launch_floor_is_explicit_and_cannot_disable_checks(self):
        self.assertEqual(monitor.launch_floor({}), 85)
        for value in (True, 0, 69, 100, "85"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                monitor.launch_floor(
                    {"resource_monitor_policy": {"launch_min_free_percent": value}}
                )

    def test_dirty_source_is_rejected_before_output_or_launch(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with (
                patch.object(monitor, "git_sha", return_value="1" * 12 + "+dirty"),
                patch.object(monitor, "committed_config", return_value=({}, b"")),
                self.assertRaisesRegex(ValueError, "commit benchmark source"),
            ):
                monitor.supervise(root / "config.yaml", root / "evidence")
            self.assertFalse((root / "evidence").exists())

    def test_preflight_pressure_or_insufficient_headroom_never_launches(self):
        for initial in (sample(free=84), sample(pressure=2), sample(swap=16384)):
            with (
                self.subTest(initial=initial),
                tempfile.TemporaryDirectory() as directory,
            ):
                root = Path(directory)
                cfg = root / "config.yaml"
                cfg.write_text("fixture")
                with (
                    patch.object(monitor, "REPO", root),
                    patch.object(monitor, "committed_config", return_value=({}, b"")),
                    patch.object(monitor, "sample", return_value=initial),
                    patch.object(monitor.subprocess, "Popen") as launch,
                ):
                    result = monitor.supervise(cfg, root / "evidence")
                self.assertEqual(result, 2)
                launch.assert_not_called()
                outcome = json.loads((root / "evidence/outcome.json").read_text())
                self.assertFalse(outcome["model_started"])
                self.assertEqual(outcome["stop_reason"], "resource preflight declined")

    def test_sampler_failure_is_terminal_no_launch_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cfg = root / "config.yaml"
            cfg.write_text("fixture")
            with (
                patch.object(monitor, "REPO", root),
                patch.object(monitor, "committed_config", return_value=({}, b"")),
                patch.object(
                    monitor, "sample", side_effect=RuntimeError("counter unavailable")
                ),
                patch.object(monitor.subprocess, "Popen") as launch,
            ):
                self.assertEqual(monitor.supervise(cfg, root / "evidence"), 2)
            launch.assert_not_called()
            outcome = json.loads((root / "evidence/outcome.json").read_text())
            self.assertFalse(outcome["model_started"])
            self.assertIn("counter unavailable", outcome["stop_reason"])

    def test_warning_stop_records_policy_and_waits_for_owned_teardown(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cfg = root / "config.yaml"
            cfg.write_text("fixture")
            process = SimpleNamespace(pid=12345, returncode=None)

            class Session:
                def leader_exited(self):
                    return False

                def stop(self, grace_seconds):
                    self.grace = grace_seconds
                    process.returncode = 130

            session = Session()
            values = [sample(), sample(pressure=2), sample(pressure=2)]
            with (
                patch.object(monitor, "REPO", root),
                patch.object(monitor, "committed_config", return_value=({}, b"")),
                patch.object(monitor, "sample", side_effect=values),
                patch.object(monitor.subprocess, "Popen", return_value=process),
                patch.object(monitor, "OwnedSession", return_value=session),
                patch.object(monitor.time, "sleep"),
            ):
                self.assertEqual(monitor.supervise(cfg, root / "evidence"), 1)
            outcome = json.loads((root / "evidence/outcome.json").read_text())
            self.assertEqual(
                outcome["stop_reason"], "sustained warning memory pressure"
            )
            self.assertEqual(outcome["returncode"], 130)
            self.assertEqual(session.grace, 15)
            invocation = json.loads((root / "evidence/invocation.json").read_text())
            self.assertEqual(
                invocation["resource_policy"]["launch_min_free_percent"], 85
            )
            self.assertEqual(invocation["supervision_id"], outcome["supervision_id"])
            self.assertEqual(len(invocation["config_sha256"]), 64)
            self.assertEqual(
                set(invocation["supervisor_versions"]),
                {
                    "supervise_bench.py",
                    "owned_process.py",
                    "bench_common.py",
                    "run_standin_suite.py",
                },
            )
            self.assertEqual(
                len((root / "evidence/resources.jsonl").read_text().splitlines()), 2
            )

    def test_existing_evidence_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            out = root / "evidence"
            out.mkdir()
            (out / "child.log").write_text("preserved")
            with (
                patch.object(monitor, "committed_config", return_value=({}, b"")),
                self.assertRaises(FileExistsError),
            ):
                monitor.supervise(root / "config.yaml", out)
            self.assertEqual((out / "child.log").read_text(), "preserved")


if __name__ == "__main__":
    unittest.main()
