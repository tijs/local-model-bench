"""Resource supervisor declines unsafe launches and records terminal outcomes."""

import hashlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import run_bench
import supervise_bench as monitor


def sample(free=90, pressure=1, swap=0.0, disk=50 * 1024**3):
    return {
        "time": "2026-10-29T20:00:00+00:00",
        "physical_memory_bytes": 32 * 1024**3,
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

    def test_stable_baseline_requires_every_sample_to_pass(self):
        self.assertTrue(monitor.baseline_ready([sample(free=84)] * 7, 84, 2))
        for points in (
            [sample(free=83), sample(free=84)],
            [sample(pressure=2), sample()],
            [sample(free=84), sample(free=87)],
            [sample(swap=0), sample(swap=64)],
            [sample(disk=9 * 1024**3), sample()],
            [],
        ):
            with self.subTest(points=points):
                self.assertFalse(monitor.baseline_ready(points, 84, 2))

    def test_probe_requires_bounded_nonranking_identity(self):
        cfg = {
            "resource_probe": True,
            "diagnostic_only": True,
            "orchestration": {"rank_eligible": False},
            "resource_monitor_policy": {"launch_baseline_samples": 7},
        }
        self.assertEqual(monitor.admission_settings(cfg, 900, 1), (7, 2))
        for change, deadline, trials in (
            ({"diagnostic_only": False}, 900, 1),
            ({"orchestration": {"rank_eligible": True}}, 900, 1),
            ({"resource_monitor_policy": {"launch_baseline_samples": 1}}, 900, 1),
            ({}, 901, 1),
            ({}, 900, 2),
            ({"resource_probe": "true"}, 900, 1),
        ):
            with (
                self.subTest(change=change, deadline=deadline, trials=trials),
                self.assertRaises(ValueError),
            ):
                monitor.admission_settings(cfg | change, deadline, trials)

    def test_unstable_baseline_is_preserved_and_never_launches(self):
        cfg_data = {
            "resource_monitor_policy": {
                "launch_min_free_percent": 84,
                "launch_baseline_samples": 7,
            },
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cfg = root / "config.yaml"
            with (
                patch.object(monitor, "REPO", root),
                patch.object(monitor, "committed_config", return_value=(cfg_data, b"")),
                patch.object(
                    monitor,
                    "sample",
                    side_effect=[sample(pressure=2)] + [sample(free=84)] * 6,
                ),
                patch.object(monitor.time, "sleep") as sleep,
                patch.object(monitor.subprocess, "Popen") as launch,
            ):
                self.assertEqual(monitor.supervise(cfg, root / "evidence"), 2)
            launch.assert_not_called()
            self.assertEqual(sleep.call_count, 6)
            self.assertEqual(
                len((root / "evidence/baseline.jsonl").read_text().splitlines()), 7
            )
            invocation = json.loads((root / "evidence/invocation.json").read_text())
            self.assertIn(
                "incomplete GPU", invocation["memory_accounting"]["owned_processes"]
            )

    def test_probe_rejects_direct_runner_before_runtime_preparation(self):
        with tempfile.TemporaryDirectory() as directory:
            cfg = Path(directory) / "probe.yaml"
            content = b"resource_probe: true\n"
            cfg.write_bytes(content)
            with (
                patch.dict(os.environ, {}, clear=True),
                patch.object(run_bench, "verify_mei_runtime") as prepare,
                self.assertRaisesRegex(ValueError, "supervise_bench"),
            ):
                run_bench.run_one(cfg)
            prepare.assert_not_called()

    def test_stable_84_probe_launches_once_with_exact_admitted_config(self):
        cfg_data = {
            "resource_probe": True,
            "diagnostic_only": True,
            "orchestration": {"rank_eligible": False},
            "resource_monitor_policy": {
                "launch_min_free_percent": 84,
                "launch_baseline_samples": 7,
            },
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            process = SimpleNamespace(pid=12345, returncode=0)
            session = SimpleNamespace(
                leader_exited=lambda: True, stop=lambda **kwargs: None
            )
            with (
                patch.object(monitor, "REPO", root),
                patch.object(
                    monitor,
                    "committed_config",
                    return_value=(cfg_data, b"exact config"),
                ),
                patch.object(monitor, "sample", return_value=sample(free=84)),
                patch.object(monitor.time, "sleep"),
                patch.object(
                    monitor.subprocess, "Popen", return_value=process
                ) as launch,
                patch.object(monitor, "OwnedSession", return_value=session),
            ):
                self.assertEqual(
                    monitor.supervise(root / "probe.yaml", root / "evidence", 900), 0
                )
            launch.assert_called_once()
            self.assertEqual(
                launch.call_args.kwargs["env"]["BENCH_ADMITTED_CONFIG_SHA256"],
                hashlib.sha256(b"exact config").hexdigest(),
            )
            self.assertEqual(
                (root / "evidence/config.yaml").read_bytes(), b"exact config"
            )

    def test_capacity_probe_ignores_percent_but_keeps_critical_stop(self):
        from test_capacity_admission import config

        cfg_data = config()
        cfg_data.update(
            resource_probe=True,
            diagnostic_only=True,
            orchestration={"rank_eligible": False},
        )
        cfg_data["resource_monitor_policy"]["launch_baseline_samples"] = 7
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            process = SimpleNamespace(pid=12345, returncode=None)

            def stop(**kwargs):
                (root / "evidence/context-capacity.json").write_text(
                    '{"status":"running","steps":[]}'
                )
                process.returncode = 130

            session = SimpleNamespace(leader_exited=lambda: False, stop=stop)
            with (
                patch.object(monitor, "REPO", root),
                patch.object(
                    monitor,
                    "committed_config",
                    return_value=(cfg_data, b"capacity config"),
                ),
                patch.object(
                    monitor,
                    "sample",
                    side_effect=[sample(free=83)] * 7
                    + [sample(free=9), sample(free=9, pressure=4)],
                ),
                patch.object(monitor.time, "sleep"),
                patch.object(
                    monitor.subprocess, "Popen", return_value=process
                ) as launch,
                patch.object(monitor, "OwnedSession", return_value=session),
            ):
                self.assertEqual(
                    monitor.supervise(root / "probe.yaml", root / "evidence", 3600), 1
                )
            launch.assert_called_once()
            outcome = json.loads((root / "evidence/outcome.json").read_text())
            self.assertEqual(outcome["stop_reason"], "critical memory pressure")
            self.assertTrue(outcome["model_started"])
            invocation = json.loads((root / "evidence/invocation.json").read_text())
            self.assertIsNone(invocation["resource_policy"]["launch_min_free_percent"])
            self.assertIsNone(invocation["resource_policy"]["stop_min_free_percent"])
            self.assertIn("capacity_admission.py", invocation["supervisor_versions"])

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
