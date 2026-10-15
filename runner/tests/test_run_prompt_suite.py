"""Model-free config/CLI regression tests for the Hermes Ops connect budget.

The child prompt runner, grader, Git identity and RSS sampler are explicit mocks.
All suite/config snapshots and mock result rows live in disposable fixture roots;
no HTTP request, model/server launch or real result-ledger write is performed.
"""
import contextlib
import inspect
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bench_common
import run_prompt
import run_prompt_suite

REPO = Path(__file__).resolve().parents[2]
LFM_CONFIG = REPO / "configs" / "LiquidAI-LFM2.5-24B-A2B-MLX-4bit" / "mei.yaml"


class HermesOpsConnectTimeoutTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix="prompt-suite-connect-")
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name).resolve()
        (self.root / "tasks").mkdir()
        (self.root / "results").mkdir()
        stack = contextlib.ExitStack()
        self.addCleanup(stack.close)
        stack.enter_context(mock.patch.object(run_prompt_suite, "REPO", self.root))
        stack.enter_context(mock.patch.object(bench_common, "REPO", self.root))
        stack.enter_context(mock.patch.object(run_prompt_suite, "git_sha", return_value="offline-test"))
        self.snapshot = stack.enter_context(mock.patch.object(
            run_prompt_suite, "snapshot_config", wraps=bench_common.snapshot_config))
        self.runner = stack.enter_context(mock.patch.object(
            run_prompt_suite, "run_with_task_deadline",
            return_value=(json.dumps({"error": None, "wall_seconds": 0.01}), "", 0, False)))
        self.grader = stack.enter_context(mock.patch.object(
            run_prompt_suite.subprocess, "run",
            return_value=subprocess.CompletedProcess([], 0, stdout="mocked grade")))
        self.sampler = stack.enter_context(mock.patch.object(run_prompt_suite, "PeakRSSSampler"))
        self.sampler.return_value.start.return_value = self.sampler.return_value
        self.sampler.return_value.stop.return_value = None

    def _invoke(self, config=None, suite="hermes_ops", suite_connect_timeout=None):
        # Keep the canonical budgets, but replace ALL live tasks/prompts/tools
        # with one synthetic task whose child and grading calls are mocked.
        spec = yaml.safe_load((REPO / "tasks" / f"{suite}.yaml").read_text())
        spec["tasks"] = [{
            "id": "offline-connect-fixture", "type": "prompt-response",
            "prompt_spec": {"user_prompt": "offline fixture"},
            "check": {"type": "contains", "text": "offline fixture"},
        }]
        if suite_connect_timeout is not None:
            spec["connect_timeout_seconds"] = suite_connect_timeout
        (self.root / "tasks" / f"{suite}.yaml").write_text(yaml.safe_dump(spec))
        argv = [
            "run_prompt_suite.py", "--suite", suite,
            "--base-url", "http://127.0.0.1:1/v1", "--model", "offline-test",
            "--inference-engine", "fake",
            "--summary-out", str(self.root / "summary.json"),
        ]
        if config is not None:
            path = self.root / "config.yaml"
            path.write_text(yaml.safe_dump(config))
            argv += ["--config", str(path)]
        for call in (self.snapshot, self.runner, self.grader, self.sampler):
            call.reset_mock()
        with mock.patch.object(sys, "argv", argv), contextlib.redirect_stdout(io.StringIO()):
            run_prompt_suite.main()
        self.runner.assert_called_once()
        self.grader.assert_called_once()
        return self.runner.call_args.args[0]

    def _option(self, cmd, flag):
        self.assertEqual(cmd.count(flag), 1, cmd)
        return cmd[cmd.index(flag) + 1]

    def test_no_config_omits_override_and_uses_unchanged_60_second_default(self):
        self.assertEqual(run_prompt.DEFAULT_CONNECT_TIMEOUT, 60.0)
        default = inspect.signature(run_prompt.call_backend_streaming).parameters["connect_timeout"].default
        self.assertEqual(default, 60.0)
        cmd = self._invoke()
        self.assertNotIn("--connect-timeout", cmd)
        self.snapshot.assert_not_called()

    def test_empty_config_omits_override(self):
        cmd = self._invoke({})
        self.assertNotIn("--connect-timeout", cmd)
        self.assertEqual(self._option(cmd, "--temperature"), "0")

    def test_existing_model_configs_without_field_omit_override(self):
        configs = []
        for path in sorted((REPO / "configs").rglob("*.yaml")):
            cfg = yaml.safe_load(path.read_text())
            if (isinstance(cfg, dict) and "model" in cfg and "inference_engine" in cfg
                    and "hermes_ops_connect_timeout" not in cfg):
                configs.append((path, cfg))
        self.assertTrue(configs)
        checked = []
        for path, cfg in configs:
            with self.subTest(config=str(path.relative_to(REPO))):
                self.assertNotIn("hermes_ops_connect_timeout", cfg)
                self.assertNotIn("--connect-timeout", self._invoke(cfg))
                checked.append(path)
        self.assertEqual(set(checked), {path for path, _cfg in configs})

    def test_lfm_override_is_forwarded_with_all_other_budgets_and_sampler_unchanged(self):
        cfg = yaml.safe_load(LFM_CONFIG.read_text())
        cmd = self._invoke(cfg)
        self.assertEqual(self._option(cmd, "--connect-timeout"), "300")
        for flag, value in {
            "--timeout": "1000", "--first-progress-timeout": "600",
            "--stream-idle-timeout": "300", "--max-turns": "40",
            "--max-tokens": "4096", "--temperature": "0.1", "--top-k": "50",
            "--top-p": "0.0", "--min-p": "0", "--repetition-penalty": "1.05",
        }.items():
            with self.subTest(flag=flag):
                self.assertEqual(self._option(cmd, flag), value)
        self.assertEqual(self.runner.call_args.kwargs, {"timeout": 14400})
        self.assertNotIn("--reasoning-effort", cmd)
        self.assertNotIn("--no-response-retries", cmd)
        self.assertNotIn("--retry-delay", cmd)

    def test_positive_integer_and_fractional_seconds_are_forwarded(self):
        for seconds in (1, 300, 0.5, 300.25):
            with self.subTest(seconds=seconds):
                cmd = self._invoke({"hermes_ops_connect_timeout": seconds})
                self.assertEqual(self._option(cmd, "--connect-timeout"), str(seconds))

    def test_invalid_values_fail_before_snapshots_tasks_or_rows(self):
        values = (None, True, False, 0, 0.0, -1, -0.5, float("inf"),
                  float("-inf"), float("nan"), "300", "", [], {}, 10 ** 1000)
        for value in values:
            with self.subTest(value=value):
                with self.assertRaises(SystemExit) as ctx:
                    self._invoke({"hermes_ops_connect_timeout": value})
                self.assertIn("hermes_ops_connect_timeout", str(ctx.exception))
                self.assertIn("positive finite numeric seconds", str(ctx.exception))
                for call in (self.snapshot, self.runner, self.grader, self.sampler):
                    call.assert_not_called()
                self.assertFalse((self.root / "summary.json").exists())
                self.assertEqual(list((self.root / "results").iterdir()), [])

    def test_invalid_declared_value_is_validated_even_for_other_prompt_suites(self):
        with self.assertRaisesRegex(SystemExit, "hermes_ops_connect_timeout"):
            self._invoke({"hermes_ops_connect_timeout": True}, suite="sanity")
        self.runner.assert_not_called()
        self.snapshot.assert_not_called()

    def test_sanity_command_is_unchanged_by_valid_lfm_override(self):
        cfg = yaml.safe_load(LFM_CONFIG.read_text())
        with_override = self._invoke(cfg, suite="sanity")
        cfg.pop("hermes_ops_connect_timeout")
        without_override = self._invoke(cfg, suite="sanity")
        # Each task gets a new private spec path; compare every other argument.
        for cmd in (with_override, without_override):
            cmd[cmd.index("--spec") + 1] = "<private-spec>"
        self.assertEqual(with_override, without_override)
        self.assertNotIn("--connect-timeout", with_override)
        self.assertEqual(self._option(with_override, "--temperature"), "0")

    def test_suite_connect_budget_is_preserved_without_model_override(self):
        for config in (None, {}):
            with self.subTest(config=config):
                cmd = self._invoke(config, suite_connect_timeout=25)
                self.assertEqual(self._option(cmd, "--connect-timeout"), "25")

    def test_model_override_precedes_suite_budget_only_for_hermes_ops(self):
        for suite, expected in (("hermes_ops", "300"), ("sanity", "25")):
            with self.subTest(suite=suite):
                cmd = self._invoke({"hermes_ops_connect_timeout": 300}, suite=suite,
                                   suite_connect_timeout=25)
                self.assertEqual(self._option(cmd, "--connect-timeout"), expected)

    def test_override_cannot_leak_into_the_next_config(self):
        self.assertEqual(self._option(self._invoke({"hermes_ops_connect_timeout": 300}),
                                      "--connect-timeout"), "300")
        self.assertNotIn("--connect-timeout", self._invoke({}))


if __name__ == "__main__":
    unittest.main()
