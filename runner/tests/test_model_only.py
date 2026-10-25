"""Current model-only scope must never dispatch retired runtime work."""

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import run_bench as rb


class ModelOnlyScopeTests(unittest.TestCase):
    def test_public_prompt_cli_rejects_retired_suite_without_scope(self):
        import subprocess

        root = Path(rb.__file__).resolve().parents[1]
        result = subprocess.run(
            [
                sys.executable,
                str(root / "runner/run_prompt_suite.py"),
                "--suite",
                "hermes_ops",
                "--base-url",
                "http://never.invalid/v1",
                "--model",
                "test",
                "--inference-engine",
                "mei",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("application runtime suites are retired", result.stderr)

    def test_direct_sanity_defaults_to_current_scope(self):
        from run_prompt_suite import active_suite_scope

        self.assertEqual(active_suite_scope("sanity"), "model-only-v1")
        self.assertEqual(active_suite_scope("model_tools"), "model-only-v1")
        with self.assertRaises(ValueError):
            active_suite_scope("../hermes_ops")

    def test_report_failure_is_not_success(self):
        from types import SimpleNamespace

        with patch.object(rb, "run", return_value=SimpleNamespace(returncode=1)):
            self.assertFalse(rb._model_report())

    def test_config_snapshot_keeps_admitted_bytes_and_custom_cleanup(self):
        with tempfile.TemporaryDirectory() as td, patch.object(rb, "REPO", Path(td)):
            content = b"model: admitted\n"
            path = rb.admitted_config_snapshot(content, "testhash")
            self.assertEqual(path.read_bytes(), content)
            with self.assertRaises(ValueError):
                rb.admitted_config_snapshot(b"changed", "testhash")
            config = {
                "required_runner_environment": {"MEI_RUNTIME_BASE": "/isolated/runtime"}
            }
            self.assertEqual(
                rb.mei_stop_command(config)[-2:],
                ["--runtime-base", "/isolated/runtime"],
            )

    def test_default_does_not_select_coding(self):
        args = rb.build_arg_parser().parse_args(["--config", "x.yaml"])
        self.assertIsNone(args.coding_suites)
        self.assertEqual(rb.MODEL_ONLY_SUITES, ("sanity", "model_tools"))

    def test_retired_stages_refuse_before_engine_work(self):
        for stage, suites in [("coding", None), ("all", ["kiem_mini"])]:
            with self.assertRaises(ValueError):
                rb.validate_model_only_scope(stage, suites)

    def test_current_task_catalog_is_neutral_and_bounded(self):
        root = Path(rb.__file__).resolve().parents[1]
        suite = yaml.safe_load((root / "tasks/model_tools.yaml").read_text())
        self.assertEqual(suite["benchmark_scope"], "model-only-v1")
        self.assertEqual(len(suite["tasks"]), 8)
        self.assertLessEqual(suite["max_turns"], 8)
        for task in suite["tasks"]:
            self.assertTrue(task["id"].startswith("model_tools-"))
            spec = task["prompt_spec"]
            self.assertFalse(spec["tool_loop_warnings"])
            for key in ["system_prompt_file", "tools_file"]:
                path = root / spec[key]
                self.assertNotIn("hermes", path.read_text().lower())

    def test_active_orchestration_has_no_retired_driver_calls(self):
        import inspect

        body = inspect.getsource(rb._run_one_impl)
        self.assertNotIn("reset_bench_profile", body)
        self.assertNotIn('"run_fixture_suite.py"', body)
        self.assertNotIn('"--hermes-provider"', body)
        self.assertNotIn('"--suite", "hermes_ops"', body)

    def test_dispatches_only_current_suites_and_provenance(self):
        root = Path(rb.__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as td:
            config = Path(td) / "config.yaml"
            config.write_text(
                yaml.safe_dump(
                    {
                        "model": "test",
                        "inference_engine": "api",
                        "orchestration": {
                            "raw_port": None,
                            "api_base_url": "http://local.invalid/v1",
                            "api_key_env": "BENCH_TEST_KEY",
                            "viable": "full",
                            "hermes_provider": "must-not-be-used",
                        },
                    }
                )
            )
            calls = []

            def run(command, **kwargs):
                from types import SimpleNamespace

                calls.append(command)
                if "--suite" in command:
                    suite = command[command.index("--suite") + 1]
                    spec = yaml.safe_load(
                        (root / "tasks" / f"{suite}.yaml").read_text()
                    )
                    rows = [
                        {"task_id": t["id"], "pass": True, "trial": 1}
                        for t in spec["tasks"]
                    ]
                    Path(command[command.index("--summary-out") + 1]).write_text(
                        json.dumps(rows)
                    )
                    self.assertEqual(
                        command[command.index("--benchmark-scope") + 1], "model-only-v1"
                    )
                return SimpleNamespace(returncode=0)

            with (
                patch.dict("os.environ", {"BENCH_TEST_KEY": "test-only"}),
                patch.object(rb, "run", side_effect=run),
                patch.object(rb, "admitted_config_snapshot", return_value=config),
            ):
                self.assertTrue(rb.run_one(config))
            self.assertEqual(
                [c[c.index("--suite") + 1] for c in calls if "--suite" in c],
                ["sanity", "model_tools"],
            )
            self.assertFalse(any("hermes" in str(c).lower() for c in calls))

    def test_model_report_never_mixes_historical_or_profile_identity(self):
        from build_model_report import render

        current = {
            "model": "test",
            "suite": "model_tools",
            "config_hash": "cfg",
            "runner_git_sha": "abcdef1234567",
            "pass": True,
            "benchmark_scope": "model-only-v1",
            "generation_profile": "model_card",
        }
        text = render([dict(current, model="old", benchmark_scope=None), current])
        self.assertIn("model_card", text)
        self.assertNotIn("| old |", text)

    def test_harness_errors_and_incomplete_summaries_fail_closed(self):
        rows = [
            {"task_id": "a", "pass": True, "trial": 1},
            {"task_id": "b", "pass": False, "trial": 1},
        ]
        self.assertTrue(rb.complete_model_summary(rows, {"a", "b"}, 1))
        self.assertFalse(rb.complete_model_summary(rows[:1], {"a", "b"}, 1))
        self.assertFalse(rb.complete_model_summary(rows * 2, {"a", "b"}, 1))
        self.assertFalse(rb.complete_model_summary(rows * 2, {"a", "b"}, 2))
        self.assertFalse(
            rb.complete_model_summary(
                [dict(rows[0], harness_error=True), rows[1]], {"a", "b"}, 1
            )
        )


if __name__ == "__main__":
    unittest.main()
