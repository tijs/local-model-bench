"""Coverage, provenance and lifecycle regressions for the added automation track."""

import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import run_automation_suite as suite
import run_bench as bench
from automation_references import REFERENCES
from automation_tasks import TASK_IDS
from build_automation_report import render
from run_automation_suite import validate_automation_config
from run_standin_suite import expected_request_model
from standin_tasks import TASK_IDS as HOUSEHOLD_IDS
from test_automation_tasks import ScriptClient


def config():
    return {
        "benchmark_scope": "peixinho-standin-v1",
        "python_automation": True,
        "standin_cache_policy": "fresh",
        "standin_generation_profile": "native",
        "generation_profiles": {"native": {"temperature": 0.6}},
        "standin_smoke": False,
    }


class AutomationIntegrationTests(unittest.TestCase):
    def test_cleanup_failure_does_not_skip_other_owned_sessions(self):
        stopped = []

        class Session:
            def __init__(self, name, fail=False):
                self.name, self.fail = name, fail

            def stop(self):
                stopped.append(self.name)
                if self.fail:
                    raise RuntimeError("cleanup fault")

        with self.assertRaises(ExceptionGroup):
            bench.stop_owned_processes([Session("server"), Session("proxy", True)])
        self.assertEqual(stopped, ["proxy", "server"])

    def test_llama_endpoint_alias_is_bound_to_exact_config_bytes(self):
        cfg = dict(config(), model="logical-model", inference_engine="llama.cpp")
        content = yaml.safe_dump(cfg).encode()
        self.assertEqual(
            expected_request_model(cfg, content),
            "bench-" + hashlib.sha256(content).hexdigest()[:12],
        )
        self.assertNotEqual(
            expected_request_model(cfg, content),
            expected_request_model(cfg, content + b"\n"),
        )

    def test_parent_reaps_owned_llama_group_on_failure_without_touching_other_process(
        self,
    ):
        child = None
        other = subprocess.Popen(
            [sys.executable, "-I", "-S", "-c", "import time;time.sleep(30)"],
            start_new_session=True,
        )
        try:
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "config.yaml"
                path.write_text(
                    yaml.safe_dump(
                        {
                            "model": "fixture",
                            "inference_engine": "llama.cpp",
                            "benchmark_scope": "model-only-v1",
                        }
                    )
                )

                def fail(*args, **kwargs):
                    nonlocal child
                    child = subprocess.Popen(
                        [
                            sys.executable,
                            "-I",
                            "-S",
                            "-c",
                            "import time;time.sleep(30)",
                        ],
                        start_new_session=True,
                    )
                    kwargs["owned_processes"].append(bench.OwnedSession(child))
                    raise RuntimeError("owned load failure")

                with (
                    patch.object(bench, "_run_one_impl", side_effect=fail),
                    self.assertRaisesRegex(RuntimeError, "owned load failure"),
                ):
                    bench.run_one(path)
                self.assertIsNotNone(child.poll())
                self.assertIsNone(other.poll())
        finally:
            if child is not None and child.poll() is None:
                child.kill()
                child.wait(timeout=3)
            other.terminate()
            other.wait(timeout=3)

    def suite_config(self):
        return dict(config(), model="fixture-model", inference_engine="fixture")

    def reference_client(self, _url, _model, messages, tools, **kwargs):
        if len(messages) == 2:
            prompt = messages[1]["content"]
            tid = (
                "reminder-repair"
                if prompt.startswith("Repair")
                else "expense-summary"
                if "summarize" in prompt
                else "shopping-csv"
            )
            self.script_client = ScriptClient(REFERENCES[tid])
        return self.script_client(_url, _model, messages, tools, **kwargs)

    def test_real_suite_persists_complete_separate_rows_and_report(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cfg = self.suite_config()
            rows, path = suite.run_suite(
                cfg,
                yaml.safe_dump(cfg).encode(),
                "unused",
                "test",
                1,
                "development",
                root,
                self.reference_client,
                _test_skip_admission=True,
            )
            self.assertEqual(len(rows), 3)
            self.assertTrue(all(r["pass"] for r in rows))
            manifest = json.loads((path / "manifest.json").read_text())
            self.assertEqual(manifest["status"], "completed")
            self.assertEqual(manifest["rows_completed"], 3)
            self.assertEqual(
                len((root / "results/automation/log.jsonl").read_text().splitlines()), 3
            )
            self.assertIn("3/3", render(rows, [manifest]))
            self.assertFalse((root / "results/standin/log.jsonl").exists())

    def test_grading_interrupt_persists_current_task_and_stops_remaining_tasks(self):
        calls = 0
        original = suite.execute_source

        def execute(*args, **kwargs):
            nonlocal calls
            calls += 1
            if calls == 3:  # preflight, visible agent run, first grading variant
                raise KeyboardInterrupt
            return original(*args, **kwargs)

        with (
            tempfile.TemporaryDirectory() as directory,
            patch.object(suite, "execute_source", side_effect=execute),
        ):
            root = Path(directory)
            cfg = self.suite_config()
            rows, path = suite.run_suite(
                cfg,
                yaml.safe_dump(cfg).encode(),
                "unused",
                "test",
                1,
                "development",
                root,
                self.reference_client,
                _test_skip_admission=True,
            )
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["failure_class"], "interrupted")
            manifest = json.loads((path / "manifest.json").read_text())
            self.assertEqual(manifest["status"], "interrupted")
            artifact = json.loads((root / rows[0]["result_path"]).read_text())
            self.assertEqual(artifact["script"], REFERENCES["shopping-csv"])
            self.assertEqual(len(artifact["responses"]), 3)
            self.assertIn("incomplete/unusable", render(rows, [manifest]))

    def test_changed_python_identity_stops_instead_of_scoring_model(self):
        original = suite.execute_source
        calls = 0

        def execute(*args, **kwargs):
            nonlocal calls
            calls += 1
            result = original(*args, **kwargs)
            if calls > 1:
                result["isolation"]["python_sha256"] = "0" * 64
            return result

        with (
            tempfile.TemporaryDirectory() as directory,
            patch.object(suite, "execute_source", side_effect=execute),
        ):
            cfg = self.suite_config()
            rows, path = suite.run_suite(
                cfg,
                yaml.safe_dump(cfg).encode(),
                "unused",
                "test",
                1,
                "development",
                Path(directory),
                self.reference_client,
                _test_skip_admission=True,
            )
            self.assertEqual(len(rows), 1)
            self.assertTrue(rows[0]["harness_error"])
            self.assertIn("identity changed", rows[0]["error"])
            self.assertEqual(
                json.loads((path / "manifest.json").read_text())["status"],
                "infrastructure_stopped",
            )

    def test_parent_routes_both_tracks_and_rejects_incomplete_automation(self):
        for missing in (False, True):
            with (
                self.subTest(missing=missing),
                tempfile.TemporaryDirectory() as directory,
            ):
                path = Path(directory) / "config.yaml"
                cfg = dict(
                    config(),
                    model="fixture",
                    inference_engine="mei",
                    orchestration={
                        "raw_port": None,
                        "api_base_url": "http://local.invalid/v1",
                        "api_key_env": "FAKE_KEY",
                        "served_model_id": "served",
                        "viable": "model_only",
                    },
                )
                path.write_text(yaml.safe_dump(cfg))
                commands = []

                def run(command, recorded=commands, omit=missing, **kwargs):
                    recorded.append(command)
                    selected = (
                        HOUSEHOLD_IDS
                        if "run_standin_suite.py" in str(command)
                        else TASK_IDS
                        if "run_automation_suite.py" in str(command)
                        else None
                    )
                    if selected is not None:
                        if omit and selected == TASK_IDS:
                            selected = selected[:-1]
                        Path(command[command.index("--summary-out") + 1]).write_text(
                            json.dumps(
                                [
                                    {"task_id": tid, "trial": 1, "pass": True}
                                    for tid in selected
                                ]
                            )
                        )
                    return SimpleNamespace(returncode=0)

                with (
                    patch.dict("os.environ", FAKE_KEY="test"),
                    patch.object(bench, "run", side_effect=run),
                    patch.object(bench, "verify_mei_runtime"),
                    patch.object(bench, "admitted_config_snapshot", return_value=path),
                    patch(
                        "run_standin_suite.committed_config",
                        return_value=(cfg, path.read_bytes()),
                    ),
                ):
                    result = bench.run_one(path)
                self.assertEqual(bool(result), not missing)
                self.assertTrue(
                    any("run_automation_suite.py" in str(c) for c in commands)
                )
                self.assertTrue(any("stop_mei_server.sh" in str(c) for c in commands))
                self.assertFalse(any("hermes" in str(c).lower() for c in commands))

    def test_unsupported_scope_cannot_silently_ignore_automation(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.yaml"
            path.write_text(
                yaml.safe_dump(
                    dict(self.suite_config(), benchmark_scope="model-only-v1")
                )
            )
            with self.assertRaisesRegex(ValueError, "requires the household"):
                bench.run_one(path)

    def test_requires_explicit_literal_opt_in(self):
        validate_automation_config(config())
        for value in (False, "true", 1, None):
            cfg = config()
            cfg["python_automation"] = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                validate_automation_config(cfg)

    def test_report_rejects_duplicate_unexpected_and_false_completion(self):
        manifest = {
            "run_id": "r",
            "planned": [{"task_id": "shopping-csv", "trial": 1}],
            "rows_completed": 1,
            "status": "completed",
            "model": "test",
            "inference_engine": "test",
            "config_hash": "cfg",
            "runner_git_sha": "sha",
            "partition": "development",
            "generation_profile": "native",
            "cache_policy": "fresh",
            "versions": {},
            "runtime_identity": None,
        }
        row = {
            k: v
            for k, v in manifest.items()
            if k not in ("planned", "rows_completed", "status")
        }
        row.update(
            benchmark_scope="python-automation-v1",
            task_id="shopping-csv",
            trial=1,
            invalid_tool_calls=0,
            wall_seconds=1,
            **{"pass": True},
        )
        self.assertIn("1/1", render([row], [manifest]))
        with self.assertRaises(ValueError):
            render([row, row], [manifest])
        with self.assertRaises(ValueError):
            render([], [manifest])
        wrong = copy.deepcopy(row)
        wrong["versions"] = {"new": "hash"}
        with self.assertRaises(ValueError):
            render([wrong], [manifest])
        wrong = copy.deepcopy(row)
        wrong["benchmark_scope"] = "peixinho-standin-v1"
        with self.assertRaises(ValueError):
            render([wrong], [manifest])

    def test_partial_is_marked_incomplete_in_report(self):
        manifest = {
            "run_id": "r",
            "planned": [{"task_id": "shopping-csv", "trial": 1}],
            "rows_completed": 0,
            "status": "interrupted",
            "model": "test",
            "inference_engine": "test",
            "config_hash": "cfg",
            "runner_git_sha": "sha",
            "partition": "development",
            "generation_profile": "native",
        }
        text = render([], [manifest])
        self.assertIn("incomplete/unusable", text)
        self.assertIn("0/1", text)


if __name__ == "__main__":
    unittest.main()
