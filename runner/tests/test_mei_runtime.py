"""Offline Mei runtime isolation: all launch/stop/health calls are mocks.

Only temporary fixture files are written. No real stop/unload script, model
server, installed profile, or historical runtime directory is accessed.
"""
import argparse
import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bench_common as bc
import run_bench as rb
import run_mei_acceptance as acceptance


class MeiStopCommandTests(unittest.TestCase):
    def test_explicit_override_is_one_argv_value_and_wins_over_environment(self):
        base = "/offline fixture/mei-runtime-lfm25"
        with mock.patch.dict(os.environ, {"MEI_RUNTIME_BASE": "/unused/shared-runtime"}):
            self.assertEqual(bc.mei_stop_command({"mei_runtime_base": base}, Path("/repo")), [
                "bash", "/repo/runner/stop_mei_server.sh", "--runtime-base", base])

    def test_omitted_override_preserves_stop_script_defaults_and_environment(self):
        # No Python default is injected: the existing shell script still owns
        # both MEI_RUNTIME_BASE and its historical fallback for old configs.
        with mock.patch.dict(os.environ, {"MEI_RUNTIME_BASE": "/offline/env-runtime"}):
            self.assertEqual(bc.mei_stop_command({}, Path("/repo")), [
                "bash", "/repo/runner/stop_mei_server.sh"])

    def test_home_relative_override_is_expanded_without_shell_execution(self):
        self.assertEqual(bc.mei_stop_command({"mei_runtime_base": "~/offline-runtime"}, Path("/repo"))[-1],
                         str(Path.home() / "offline-runtime"))

    def test_invalid_explicit_override_never_falls_back_to_shared_runtime(self):
        for value in (None, "", "  ", False, 1, [], {}, "relative/runtime", "$HOME/runtime"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                bc.mei_stop_command({"mei_runtime_base": value}, Path("/repo"))


class MeiRuntimeRunnerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="mei-runtime-offline-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.config = self.root / "configs" / "offline-model" / "mei.yaml"
        self.config.parent.mkdir(parents=True)
        self.model = self.root / "model"
        self.model.mkdir()
        (self.model / "config.json").write_text("{}\n")
        self.runtime = self.root / "runtime with spaces"

    def write_config(self, override=True):
        cfg = {
            "model": "offline-model",
            "inference_engine": "mei",
            "benchmark_launch_command": f"bash runner/start_mei_server.sh --model-dir {self.model}",
            "benchmark_endpoint": "http://127.0.0.1:8029/v1",
            "orchestration": {
                "raw_port": 8029, "served_model_id": "offline-model",
                "hermes_profile": "bench-lfm25", "viable": "full"},
        }
        if override:
            cfg["mei_runtime_base"] = str(self.runtime)
        self.config.write_text(yaml.safe_dump(cfg))
        return cfg

    def expected_stop(self, override=True):
        cmd = ["bash", str(self.root / "runner" / "stop_mei_server.sh")]
        return cmd + (["--runtime-base", str(self.runtime)] if override else [])

    def run_bench_until_health_failure(self, override):
        self.write_config(override)
        with mock.patch.object(rb, "REPO", self.root), \
                mock.patch.object(rb, "run", return_value=subprocess.CompletedProcess([], 0)) as run, \
                mock.patch.object(rb.subprocess, "Popen") as launch, \
                mock.patch.object(rb, "wait_for_health", return_value=False), \
                mock.patch.object(rb, "clear_kv_cache_dir"), \
                mock.patch.object(rb.shutil, "disk_usage", return_value=mock.Mock(free=100 * 1024 ** 3)), \
                mock.patch("builtins.open", mock.mock_open()), \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertIsNone(rb.run_one(self.config))
        launch.assert_called_once()  # mocked: no server was started
        calls = [call.args[0] for call in run.call_args_list]
        stops = [cmd for cmd in calls if any(str(x).endswith("stop_mei_server.sh") for x in cmd)]
        self.assertEqual(stops, [self.expected_stop(override)] * 2)
        self.assertEqual(calls[0], self.expected_stop(override))  # before mocked unload/launch
        self.assertEqual(calls[-1], self.expected_stop(override))  # outer finally
        self.assertFalse(self.runtime.exists())

    def test_bench_prelaunch_and_failed_health_cleanup_use_configured_runtime(self):
        self.run_bench_until_health_failure(override=True)

    def test_bench_prelaunch_and_failed_health_cleanup_keep_legacy_default(self):
        self.run_bench_until_health_failure(override=False)

    def test_bench_finally_stops_configured_runtime_on_success_and_exception(self):
        self.write_config()
        for failure in (None, RuntimeError("offline fixture failure")):
            with self.subTest(failure=failure), \
                    mock.patch.object(rb, "REPO", self.root), \
                    mock.patch.object(rb, "_run_one_impl", return_value=True, side_effect=failure), \
                    mock.patch.object(rb, "run") as run:
                if failure:
                    with self.assertRaisesRegex(RuntimeError, "offline fixture failure"):
                        rb.run_one(self.config)
                else:
                    self.assertTrue(rb.run_one(self.config))
            run.assert_called_once_with(self.expected_stop())

    def run_acceptance_fixture(self, override, health_failure=False, probe_rc=0,
                               *, skip_context=True, skip_cache=True):
        self.write_config(override)
        events = []
        process = mock.Mock()
        process.terminate.side_effect = lambda: events.append("terminate-wrapper")

        def fake_subprocess(cmd, **kwargs):
            is_stop = any(str(x).endswith("stop_mei_server.sh") for x in cmd)
            events.append("stop-server" if is_stop else "probe")
            return subprocess.CompletedProcess(cmd, 0 if is_stop else probe_rc, stdout="", stderr="")

        with mock.patch.object(acceptance, "REPO", self.root), \
                mock.patch.object(acceptance, "MEI_MODEL_ROOT", self.root / "unused-model-root"), \
                mock.patch.dict(os.environ, {"HOME": str(self.root / "home")}), \
                mock.patch.object(acceptance.subprocess, "Popen", return_value=process) as launch, \
                mock.patch.object(acceptance, "wait_ready",
                                  side_effect=RuntimeError("offline health failure") if health_failure else None), \
                mock.patch.object(acceptance.subprocess, "run", side_effect=fake_subprocess) as run:
            record = acceptance.run_config(self.config, argparse.Namespace(
                skip_context=skip_context, skip_cache=skip_cache))
        launch.assert_called_once()  # mocked: no server was started
        stop_calls = [c for c in run.call_args_list
                      if any(str(x).endswith("stop_mei_server.sh") for x in c.args[0])]
        self.assertEqual(len(stop_calls), 1)
        self.assertEqual(stop_calls[0].args[0], self.expected_stop(override))
        probe_calls = [c.args[0] for c in run.call_args_list
                       if any(str(x).endswith("probe_mei.py") for x in c.args[0])]
        self.assertEqual(len(probe_calls), 0 if health_failure else 1)
        if probe_calls:
            self.assertEqual("--skip-cache" in probe_calls[0], skip_cache)
            self.assertEqual("--skip-context" in probe_calls[0], skip_context)
            self.assertEqual(probe_calls[0][probe_calls[0].index("--context-cap") + 1], "65536")
        self.assertLess(events.index("stop-server"), events.index("terminate-wrapper"))
        process.terminate.assert_called_once_with()
        process.wait.assert_called_once_with(timeout=30)
        self.assertFalse(self.runtime.exists())
        self.assertEqual(json.loads((Path(record["output_root"]) / "record.json").read_text())["status"],
                         record["status"])
        return record

    def test_acceptance_cleanup_uses_configured_runtime_on_pass_and_probe_failure(self):
        for rc in (0, 1):
            with self.subTest(probe_rc=rc):
                record = self.run_acceptance_fixture(override=True, probe_rc=rc)
                self.assertEqual(record["status"], "passed" if rc == 0 else "failed")

    def test_cache_disabled_admission_skips_only_cache_and_preserves_probe_failure(self):
        # Explicit mocks exercise CLI forwarding, not live admission outcomes.
        # --skip-cache must not imply --skip-context or turn a failed probe green.
        for rc in (0, 1):
            with self.subTest(probe_rc=rc):
                record = self.run_acceptance_fixture(
                    override=True, probe_rc=rc, skip_context=False, skip_cache=True)
                self.assertEqual(record["probe_rc"], rc)
                self.assertEqual(record["status"], "passed" if rc == 0 else "failed")

    def test_acceptance_cleanup_preserves_default_without_override(self):
        self.assertEqual(self.run_acceptance_fixture(override=False)["status"], "passed")

    def test_acceptance_health_exception_still_stops_exact_runtime_before_wrapper(self):
        record = self.run_acceptance_fixture(override=True, health_failure=True)
        self.assertEqual(record["status"], "error")
        self.assertIn("offline health failure", record["error"])

    def test_acceptance_invalid_runtime_fails_before_any_launch_or_cleanup(self):
        cfg = self.write_config()
        cfg["mei_runtime_base"] = None
        self.config.write_text(yaml.safe_dump(cfg))
        with mock.patch.object(acceptance.subprocess, "Popen") as launch, \
                mock.patch.object(acceptance.subprocess, "run") as run, \
                self.assertRaises(ValueError):
            acceptance.run_config(self.config, argparse.Namespace(skip_context=True, skip_cache=True))
        launch.assert_not_called()
        run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
