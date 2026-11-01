"""Native release probes retain the same ownership and resource limits as tasks."""

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import run_mei_acceptance as acceptance
from test_capacity_admission import config


def native_config():
    cfg = config()
    cfg.update(
        inference_engine="mei",
        orchestration={"served_model_id": "fixture/model"},
        mei_source_commit="a" * 40,
        vmlx_commit="b" * 40,
        required_runner_environment={"MEI_RUNTIME_BASE": "/tmp/native-fixture"},
        benchmark_launch_command="launcher --runtime-base /tmp/native-fixture",
    )
    cfg["resource_monitor_policy"]["launch_baseline_samples"] = 7
    return cfg


def point(pressure=1):
    return {
        "physical_memory_bytes": 32 * 1024**3,
        "kernel_pressure_level": pressure,
        "free_percent": 20,
        "swap_used_mib": 100,
        "disk_free_bytes": 50 * 1024**3,
    }


def args(output):
    return argparse.Namespace(
        output=output, deadline=30, skip_context=False, skip_cache=False
    )


class NativeAcceptanceSupervisionTests(unittest.TestCase):
    def test_unpinned_or_conflicting_runtime_is_rejected_before_launch(self):
        with patch.object(acceptance, "verify_mei_runtime"):
            acceptance.validate_owned_config(native_config())
            for change in (
                {"mei_source_commit": ""},
                {"vmlx_commit": "unknown"},
                {"required_runner_environment": {}},
                {"benchmark_launch_command": "launcher --runtime-base"},
                {"benchmark_launch_command": "launcher --runtime-base /tmp/other"},
            ):
                with self.subTest(change=change), self.assertRaises(ValueError):
                    acceptance.validate_owned_config(native_config() | change)

    def test_native_scope_config_requires_committed_bytes(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            path = root / "native.yaml"
            path.write_text("benchmark_scope: mei-native-v1\ninference_engine: mei\n")
            subprocess.run(["git", "-C", folder, "add", "native.yaml"], check=True)
            subprocess.run(
                [
                    "git",
                    "-C",
                    folder,
                    "-c",
                    "user.name=Fixture",
                    "-c",
                    "user.email=fixture@example.invalid",
                    "commit",
                    "-qm",
                    "fixture",
                ],
                check=True,
            )
            with patch.object(acceptance, "REPO", root):
                self.assertEqual(
                    acceptance.committed_native_config(path)[0]["benchmark_scope"],
                    "mei-native-v1",
                )
                path.write_text(path.read_text() + "context_cap: 1\n")
                with self.assertRaises(ValueError):
                    acceptance.committed_native_config(path)

    def test_pressure_at_baseline_declines_without_starting_child(self):
        with (
            tempfile.TemporaryDirectory() as folder,
            patch.object(acceptance, "sample", return_value=point(2)),
            patch.object(acceptance.time, "sleep"),
            patch.object(acceptance.subprocess, "Popen") as launch,
            patch.object(acceptance, "git_sha", return_value="a" * 12),
        ):
            output = Path(folder) / "attempt"
            self.assertEqual(
                acceptance.monitor_child(
                    native_config(), b"fixture", args(output), ["never"]
                ),
                2,
            )
            launch.assert_not_called()
            self.assertFalse(
                json.loads((output / "outcome.json").read_text())["runner_started"]
            )

    def test_critical_pressure_stops_entire_real_owned_session(self):
        real_sleep = time.sleep
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "attempt"
            ready = output / "descendant.pid"
            code = (
                "import subprocess,sys,time; from pathlib import Path; "
                "p=subprocess.Popen([sys.executable,'-c','import time; time.sleep(60)']); "
                f"Path({str(ready)!r}).write_text(str(p.pid)); time.sleep(60)"
            )

            def observe(pid, _output):
                if pid == os.getpid():
                    return point()
                deadline = time.monotonic() + 5
                while not ready.exists() and time.monotonic() < deadline:
                    real_sleep(0.01)
                return point(4)

            with (
                patch.object(acceptance, "sample", side_effect=observe),
                patch.object(acceptance.time, "sleep"),
            ):
                result = acceptance.monitor_child(
                    native_config(),
                    b"fixture",
                    args(output),
                    [sys.executable, "-c", code],
                )
            self.assertEqual(result, 1)
            outcome = json.loads((output / "outcome.json").read_text())
            self.assertIn("critical", outcome["stop_reason"])
            self.assertFalse(outcome["full_native_admission"])
            self.assertTrue(ready.exists())
            status = subprocess.run(
                ["ps", "-p", ready.read_text(), "-o", "stat="],
                capture_output=True,
                text=True,
                check=False,
            ).stdout.strip()
            self.assertTrue(not status or status.startswith("Z"), status)

    def test_low_percentage_allows_capacity_but_zero_exit_is_not_evidence(self):
        with (
            tempfile.TemporaryDirectory() as folder,
            patch.object(
                acceptance, "sample", return_value=point() | {"free_percent": 1}
            ),
            patch.object(acceptance.time, "sleep"),
        ):
            output = Path(folder) / "attempt"
            self.assertEqual(
                acceptance.monitor_child(
                    native_config(),
                    b"fixture",
                    args(output),
                    [sys.executable, "-c", "pass"],
                ),
                1,
            )
            self.assertFalse(
                json.loads((output / "outcome.json").read_text())[
                    "full_native_admission"
                ]
            )

    def test_backend_diagnostic_never_claims_full_native_and_fails_closed(self):
        for verdict in (True, False, "exception"):
            with (
                self.subTest(verdict=verdict),
                tempfile.TemporaryDirectory() as folder,
                patch.object(acceptance, "sample", return_value=point()),
                patch.object(acceptance.time, "sleep"),
            ):
                output = Path(folder) / "attempt"

                def check(path, output=output, verdict=verdict):
                    self.assertEqual(path, output)
                    if verdict == "exception":
                        raise ValueError("missing backend evidence")
                    return verdict

                rc = acceptance.monitor_child(
                    native_config(), b"fixture", args(output),
                    [sys.executable, "-c", "pass"], diagnostic_check=check,
                )
                outcome = json.loads((output / "outcome.json").read_text())
                self.assertEqual(rc, 0 if verdict is True else 1)
                self.assertFalse(outcome["full_native_admission"])
                self.assertTrue(outcome["diagnostic_only"])

    def test_missing_or_failed_native_probe_cannot_qualify(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder)
            (output / "record.json").write_text('{"status":"passed"}')
            (output / "probe.json").write_text('{"status":"passed","probes":{}}')
            self.assertFalse(
                acceptance.probe_succeeded(output, skip_context=False, skip_cache=False)
            )
            names = [
                "models_identity",
                "mei_status",
                "plain_completion",
                "tool_nonstreaming",
                "tool_streaming",
                "tool_call_history_replay",
                "parity_stream_vs_nonstream",
                "cache_repeat_1",
                "cache_repeat_2",
                "cache_growing_turn1",
                "cache_growing_turn2_reuses_slot",
                "context_exact_cap",
                "context_over_cap_rejected",
            ]
            probes = {name: {"status": "passed"} for name in names}
            (output / "probe.json").write_text(
                json.dumps({"status": "passed", "probes": probes})
            )
            self.assertTrue(
                acceptance.probe_succeeded(output, skip_context=False, skip_cache=False)
            )
            probes["context_exact_cap"]["status"] = "failed"
            (output / "probe.json").write_text(
                json.dumps({"status": "passed", "probes": probes})
            )
            self.assertFalse(
                acceptance.probe_succeeded(output, skip_context=False, skip_cache=False)
            )

    def test_launcher_and_teardown_use_exact_isolated_runtime(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            model = root / "model"
            model.mkdir()
            (model / "config.json").write_text("{}")
            mei = root / "mei"
            (mei / "tools").mkdir(parents=True)
            (mei / "tools/probe_mei.py").write_text("# pinned probe fixture")
            runtime = root / "runtime"
            cfg = native_config() | {
                "orchestration": {"served_model_id": "fixture/model"},
                "required_runner_environment": {"MEI_RUNTIME_BASE": str(runtime)},
                "benchmark_launch_command": f"launcher --model-dir {model} --mei-repo {mei} --runtime-base {runtime}",
            }
            path = root / "native.json"
            path.write_text(json.dumps(cfg))
            run_args = args(root / "output")
            process = Mock()
            with (
                patch.object(acceptance, "REPO", root),
                patch.object(acceptance, "wait_ready"),
                patch.object(acceptance, "verify_mei_runtime", return_value={}),
                patch.object(
                    acceptance.subprocess, "Popen", return_value=process
                ) as launch,
                patch.object(
                    acceptance.subprocess,
                    "run",
                    return_value=subprocess.CompletedProcess([], 0, "", ""),
                ) as command,
            ):
                acceptance.run_config(path, run_args)
            self.assertEqual(
                launch.call_args.kwargs["env"]["MEI_RUNTIME_BASE"], str(runtime)
            )
            teardown = command.call_args_list[-1]
            self.assertEqual(teardown.args[0][-2:], ["--runtime-base", str(runtime)])
            self.assertEqual(teardown.kwargs["env"]["MEI_RUNTIME_BASE"], str(runtime))

    def test_skipped_context_is_diagnostic_even_with_successful_child(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "attempt"
            basic = [
                "models_identity",
                "mei_status",
                "plain_completion",
                "tool_nonstreaming",
                "tool_streaming",
                "tool_call_history_replay",
                "parity_stream_vs_nonstream",
                "cache_repeat_1",
                "cache_repeat_2",
                "cache_growing_turn1",
                "cache_growing_turn2_reuses_slot",
            ]
            report = {
                "status": "passed",
                "probes": {name: {"status": "passed"} for name in basic},
            }
            code = (
                "from pathlib import Path; "
                f"p=Path({str(output)!r}); "
                f"(p/'probe.json').write_text({json.dumps(report)!r}); "
                f"(p/'record.json').write_text({json.dumps({'status': 'passed'})!r})"
            )
            run_args = args(output)
            run_args.skip_context = True
            with (
                patch.object(acceptance, "sample", return_value=point()),
                patch.object(acceptance.time, "sleep"),
            ):
                result = acceptance.monitor_child(
                    native_config(), b"fixture", run_args, [sys.executable, "-c", code]
                )
            self.assertEqual(result, 0, (output / "child.log").read_text())
            self.assertFalse(
                json.loads((output / "outcome.json").read_text())[
                    "full_native_admission"
                ]
            )
