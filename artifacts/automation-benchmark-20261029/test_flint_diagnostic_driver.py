"""Model-free checks of diagnostic containment and terminal resource evidence."""

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

spec = importlib.util.spec_from_file_location(
    "flint_diag", Path(__file__).with_name("flint_full_diagnostic_v8p1.py")
)
assert spec is not None and spec.loader is not None
driver = importlib.util.module_from_spec(spec)
spec.loader.exec_module(driver)


def cfg(root):
    return {
        "model_bytes": 1024**3,
        "context_cap": 65536,
        "required_runner_environment": {"MEI_RUNTIME_BASE": str(root / "runtime")},
        "resource_monitor_policy": {"admission_mode": "capacity"},
        "capacity_plan": {
            "model_bytes": 1024**3,
            "context_tokens": 65536,
            "context_cache_bytes": 1024**3,
            "retained_cache_bytes": 0,
            "allocator_cache_bytes": 0,
            "workspace_allowance_bytes": 1024**3,
            "host_reserve_bytes": 1024**3,
            "derivation": "test budget",
        },
    }


def point(pressure=1):
    return {
        "time": "2026-11-01T12:00:00+00:00",
        "physical_memory_bytes": 32 * 1024**3,
        "kernel_pressure_level": pressure,
        "free_percent": 3,
        "swap_used_mib": 0,
        "disk_free_bytes": 50 * 1024**3,
    }


class DriverTests(unittest.TestCase):
    def test_replay_uses_exact_committed_prefix_and_excludes_terminal_response(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            folder = root / "artifacts/failed"
            folder.mkdir(parents=True)
            messages = [
                {"role": "system", "content": "contract"},
                {"role": "tool", "content": "saved feedback"},
                {
                    "role": "assistant",
                    "content": None,
                    "reasoning_content": "write now",
                },
            ]
            content = json.dumps(
                {"error": "empty_final", "messages": messages}
            ).encode()
            (folder / "python-expense-summary.json").write_bytes(content)
            with (
                patch.object(driver, "REPO", root),
                patch.object(driver, "FAILED_DIAGNOSTIC", folder),
                patch.object(driver.subprocess, "check_output", return_value=content),
            ):
                self.assertEqual(driver.replay_prefix("expense-summary"), messages[:-1])
                with self.assertRaisesRegex(ValueError, "only the two"):
                    driver.replay_prefix("shopping-csv")
            with (
                patch.object(driver, "REPO", root),
                patch.object(driver, "FAILED_DIAGNOSTIC", folder),
                patch.object(
                    driver.subprocess, "check_output", return_value=b"different"
                ),
                self.assertRaisesRegex(ValueError, "commit original"),
            ):
                driver.replay_prefix("expense-summary")

    def test_busy_port_never_launches_or_creates_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            with (
                patch.object(driver, "REPO", root),
                patch.object(
                    driver, "validate", return_value=(cfg(root), b"profile", {})
                ),
                patch.object(
                    driver.subprocess, "run", return_value=SimpleNamespace(returncode=0)
                ),
                patch.object(driver.subprocess, "Popen") as launch,
                self.assertRaisesRegex(RuntimeError, "occupied"),
            ):
                driver.supervise(root / "artifacts/out")
            launch.assert_not_called()
            self.assertFalse((root / "artifacts/out").exists())

    def test_critical_pressure_stops_owned_group_and_stays_unqualified(self):
        for cleanup_timeout in (False, True):
            with (
                self.subTest(cleanup_timeout=cleanup_timeout),
                tempfile.TemporaryDirectory() as directory,
            ):
                root = Path(directory).resolve()
                process = SimpleNamespace(pid=12345, returncode=None)

                def stop(proc=process, **kwargs):
                    proc.returncode = 130

                session = SimpleNamespace(leader_exited=lambda: False, stop=stop)

                def command(argv, cleanup_timeout=cleanup_timeout, **kwargs):
                    if argv[0] == "lsof":
                        return SimpleNamespace(returncode=1)
                    if cleanup_timeout:
                        raise driver.subprocess.TimeoutExpired(argv, 45)
                    return SimpleNamespace(returncode=0)

                with (
                    patch.object(driver, "REPO", root),
                    patch.object(
                        driver, "validate", return_value=(cfg(root), b"profile", {})
                    ),
                    patch.object(driver, "git_sha", return_value="a" * 12),
                    patch.object(
                        driver, "sample", side_effect=[point()] * 7 + [point(4)]
                    ),
                    patch.object(driver.time, "sleep"),
                    patch.object(driver.subprocess, "run", side_effect=command),
                    patch.object(
                        driver.subprocess, "Popen", return_value=process
                    ) as launch,
                    patch.object(driver, "OwnedSession", return_value=session),
                ):
                    self.assertEqual(driver.supervise(root / "artifacts/out"), 1)
                launch.assert_called_once()
                result = json.loads((root / "artifacts/out/outcome.json").read_text())
                self.assertIn("critical memory pressure", result["stop_reason"])
                self.assertFalse(result["qualified"])
                self.assertTrue(result["diagnostic_only"])
                self.assertEqual(result["returncode"], 130)
                self.assertFalse((root / "results").exists())


if __name__ == "__main__":
    unittest.main()
