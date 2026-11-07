"""Reject incomplete or invalid runtime qualification evidence."""

import copy
import json
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from unittest.mock import Mock, patch

import yaml
from tokenizers import Tokenizer, models, pre_tokenizers

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import qualify_mei_release as qualification
from qualify_mei_release import observable, qualification_settings, succeeded


class QualificationTests(unittest.TestCase):
    def test_interrupt_during_stop_keeps_failure_evidence_and_terminates(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder)
            (output / "invocation.json").write_text(
                json.dumps({"runner_git_sha": "a" * 12})
            )
            process = Mock()
            receipt = {
                "actual_command": ["/bin/bash"],
                "environment": {},
                "stop_command": ["/bin/bash"],
            }
            cfg = {
                "context_cap": 65536,
                "benchmark_endpoint": "http://127.0.0.1:1/v1",
                "orchestration": {"served_model_id": "fixture"},
                "benchmark_launch_command": "bash runner/start_mei_server.sh --model-dir /fixture",
                "required_runner_environment": {"MEI_RUNTIME_BASE": folder},
                "mei_clean_speed_launch": {"mode": "fixture"},
                "mei_qualification": {
                    "repeats": 1,
                    "loaded_tokens": 1024,
                    "decode_tokens": 32,
                    "status_timeout": 1,
                },
            }
            original_write = qualification.write_json
            qualification_writes = 0

            def flaky_write(path, value):
                nonlocal qualification_writes
                if path.name == "qualification.json":
                    qualification_writes += 1
                    if qualification_writes == 2:
                        raise OSError("injected checkpoint failure")
                return original_write(path, value)

            with (
                patch.object(
                    qualification,
                    "prepare_prompts",
                    return_value={"short": "short", "loaded": "long"},
                ),
                patch.object(qualification, "acceptance_identity", return_value=None),
                patch.object(
                    qualification, "launch_receipt", return_value=(b"launch", receipt)
                ),
                patch.object(qualification, "git_bytes", return_value=b"stop"),
                patch.object(qualification, "write_json", side_effect=flaky_write),
                patch.object(qualification.subprocess, "Popen", return_value=process),
                patch.object(
                    qualification.subprocess, "run", side_effect=KeyboardInterrupt
                ),
                patch.object(
                    qualification,
                    "wait_ready",
                    side_effect=RuntimeError("fixture stop"),
                ),
            ):
                self.assertEqual(qualification.child(cfg, output), 1)
            result = json.loads((output / "qualification.json").read_text())
            self.assertEqual(result["status"], "failed")
            self.assertFalse(result["server_stopped"])
            self.assertIn("injected checkpoint failure", result["evidence_error"])
            process.terminate.assert_called_once()

    def test_failed_teardown_still_terminates_owned_process_after_interrupt(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder)
            (output / "invocation.json").write_text(
                json.dumps({"runner_git_sha": "a" * 12})
            )
            process = Mock()
            receipt = {
                "actual_command": ["/bin/bash"],
                "environment": {},
                "stop_command": ["/bin/bash"],
            }
            cfg = {
                "context_cap": 65536,
                "benchmark_endpoint": "http://127.0.0.1:1/v1",
                "orchestration": {"served_model_id": "fixture/model"},
                "benchmark_launch_command": "bash runner/start_mei_server.sh --model-dir /fixture",
                "required_runner_environment": {"MEI_RUNTIME_BASE": folder},
                "mei_clean_speed_launch": {"mode": "fixture"},
                "mei_qualification": {
                    "repeats": 1,
                    "loaded_tokens": 1024,
                    "decode_tokens": 32,
                    "status_timeout": 1,
                },
            }

            def delayed_failure(*args, **kwargs):
                partial = json.loads((output / "qualification.json").read_text())
                self.assertEqual(partial["status"], "failed")
                self.assertFalse(partial["server_stopped"])
                self.assertIn("KeyboardInterrupt", partial["error"])
                self.assertEqual(kwargs["timeout"], 7)
                return Mock(returncode=1, stderr=b"failed")

            with (
                patch.object(
                    qualification,
                    "prepare_prompts",
                    return_value={"short": "short", "loaded": "long"},
                ),
                patch.object(qualification, "acceptance_identity", return_value=None),
                patch.object(
                    qualification, "launch_receipt", return_value=(b"launch", receipt)
                ),
                patch.object(qualification, "git_bytes", return_value=b"stop"),
                patch.object(qualification.subprocess, "Popen", return_value=process),
                patch.object(
                    qualification.subprocess, "run", side_effect=delayed_failure
                ),
                patch.object(
                    qualification, "wait_ready", side_effect=KeyboardInterrupt
                ),
            ):
                self.assertEqual(qualification.child(cfg, output), 1)
            process.terminate.assert_called_once()
            process.wait.assert_called_once()
            result = json.loads((output / "qualification.json").read_text())
            self.assertFalse(result["server_stopped"])
            self.assertIn("teardown failed", result["cleanup_error"])

    def test_opt_in_clean_launch_streams_verified_bytes_and_tears_down_on_error(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder)
            (output / "invocation.json").write_text(
                json.dumps({"runner_git_sha": "a" * 12})
            )
            process = Mock()
            payload = b"# committed fixture launcher\n"
            receipt = {
                "mode": "fixture",
                "actual_command": ["/bin/bash", "-s", "--", "--model-dir", "/fixture"],
                "environment": {
                    "HOME": "/tmp",
                    "PATH": "/usr/bin:/bin:/usr/sbin:/sbin",
                },
                "stop_command": ["/bin/bash", "-s", "--", "--runtime-base", folder],
            }
            cfg = {
                "context_cap": 65536,
                "benchmark_endpoint": "http://127.0.0.1:1/v1",
                "orchestration": {"served_model_id": "fixture/model"},
                "benchmark_launch_command": "bash runner/start_mei_server.sh --model-dir /fixture",
                "required_runner_environment": {"MEI_RUNTIME_BASE": folder},
                "mei_clean_speed_launch": {"mode": "fixture"},
                "mei_qualification": {
                    "repeats": 1,
                    "loaded_tokens": 1024,
                    "decode_tokens": 32,
                    "status_timeout": 1,
                },
            }
            with (
                patch.object(
                    qualification,
                    "prepare_prompts",
                    return_value={"short": "short", "loaded": "long"},
                ),
                patch.object(qualification, "acceptance_identity", return_value=None),
                patch.object(
                    qualification, "launch_receipt", return_value=(payload, receipt)
                ),
                patch.object(
                    qualification, "git_bytes", return_value=b"# fixture stopper\n"
                ),
                patch.object(
                    qualification.subprocess, "Popen", return_value=process
                ) as launch,
                patch.object(
                    qualification.subprocess, "run", return_value=Mock(returncode=0)
                ),
                patch.object(
                    qualification,
                    "wait_ready",
                    side_effect=RuntimeError("fixture stop"),
                ),
            ):
                self.assertEqual(qualification.child(cfg, output), 1)
            self.assertEqual((output / "launcher-executed.sh").read_bytes(), payload)
            self.assertEqual(
                json.loads((output / "clean-speed-launch.json").read_text()), receipt
            )
            self.assertEqual(launch.call_args.args[0], receipt["actual_command"])
            self.assertEqual(launch.call_args.kwargs["env"], receipt["environment"])
            self.assertEqual(launch.call_args.kwargs["stdin"], subprocess.PIPE)
            process.stdin.write.assert_called_once_with(payload)
            process.stdin.close.assert_called_once()
            process.terminate.assert_called_once()

    def test_explicit_total_memory_limit_must_take_effect_independently_of_cache(self):
        requested = 24 * 1024**3
        command = ["mei", "--memory-limit-bytes", str(requested)]
        status = {"maxTokens": 8192, "memory": {"memoryLimitBytes": requested}}
        self.assertEqual(
            qualification.serving_settings(status, command)[
                "observed_allocator_memory_limit_bytes"
            ],
            requested,
        )
        for actual in (None, True, str(requested), 0, -1, 24051816857):
            with self.subTest(actual=actual), self.assertRaises(ValueError):
                qualification.serving_settings(
                    {"maxTokens": 8192, "memory": {"memoryLimitBytes": actual}}, command
                )

    def test_auto_total_limit_reports_backend_value_and_zero_cache_remains_explicit(
        self,
    ):
        status = {
            "maxTokens": 8192,
            "memory": {"memoryLimitBytes": 24051816857, "cacheLimitBytes": 0},
        }
        command = ["mei", "--memory-limit-bytes", "0", "--cache-limit-bytes", "0"]
        self.assertEqual(
            qualification.serving_settings(status, command),
            {
                "normal_output_budget": 8192,
                "observed_allocator_memory_limit_bytes": 24051816857,
                "observed_allocator_cache_limit_bytes": 0,
            },
        )
        for actual in (None, True, "24051816857", 0, -1):
            with self.subTest(actual=actual), self.assertRaises(ValueError):
                qualification.serving_settings(
                    {
                        "maxTokens": 8192,
                        "memory": {"memoryLimitBytes": actual, "cacheLimitBytes": 0},
                    },
                    command,
                )

    def test_effective_allocator_limit_must_match_the_declared_profile(self):
        command = ["mei", "--cache-limit-bytes", "536870912"]
        status = {"maxTokens": 8192, "memory": {"cacheLimitBytes": 536870912}}
        self.assertEqual(
            qualification.serving_settings(status, command),
            {
                "normal_output_budget": 8192,
                "observed_allocator_cache_limit_bytes": 536870912,
            },
        )
        for actual in (None, True, "536870912", 134217728):
            with self.subTest(actual=actual), self.assertRaises(ValueError):
                qualification.serving_settings(
                    {"maxTokens": 8192, "memory": {"cacheLimitBytes": actual}}, command
                )
        with self.assertRaises(ValueError):
            qualification.serving_settings({"maxTokens": 8192}, command)
        with self.assertRaises(ValueError):
            qualification.serving_settings({"maxTokens": 0}, [])

    def test_live_acceptance_must_run_every_declared_test_without_skips(self):
        self.assertTrue(
            qualification.acceptance_succeeded(
                0, "Executed 9 tests, with 0 failures (0 unexpected)", 9
            )
        )
        for rc, log in (
            (1, "Executed 9 tests, with 0 failures"),
            (0, "Executed 0 tests, with 0 failures"),
            (0, "Executed 9 tests, with 9 tests skipped and 0 failures"),
            (0, "Executed 9 tests, with 1 failure"),
        ):
            self.assertFalse(qualification.acceptance_succeeded(rc, log, 9))

    def test_loaded_prompt_is_exactly_counted_and_ends_in_the_short_task(self):
        tokenizer = Tokenizer(
            models.WordLevel({"[UNK]": 0, "hello": 1}, unk_token="[UNK]")
        )
        tokenizer.pre_tokenizer = pre_tokenizers.WhitespaceSplit()
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            tokenizer.save(str(root / "tokenizer.json"))
            prompts = qualification.prepare_prompts(root, 1024)
            self.assertEqual(
                len(tokenizer.encode(prompts["loaded"], add_special_tokens=False).ids),
                1024,
            )
            self.assertTrue(prompts["loaded"].endswith(prompts["short"]))
            self.assertIn("integers from 1 to 100", prompts["short"])

    def test_live_client_loop_preserves_status_failure_and_excludes_warmups(self):
        for fail_status in (False, True):
            active = threading.Event()
            requests = []

            class Handler(BaseHTTPRequestHandler):
                def log_message(self, format: str, *args: object) -> None:
                    pass

                def reply(self, body, code=200):
                    data = json.dumps(body).encode()
                    self.send_response(code)
                    self.send_header("Content-Length", str(len(data)))
                    self.end_headers()
                    self.wfile.write(data)

                def do_GET(self, active=active, fail_status=fail_status):
                    is_active = active.is_set()
                    self.reply(
                        {
                            "status": "ok",
                            "maxTokens": 8192,
                            "scheduler": {"activeGenerations": int(is_active)},
                            "memory": {
                                "activeBytes": 512 if is_active else 256,
                                "cacheBytes": 32,
                                "peakBytes": 768,
                                "memoryLimitBytes": 2048 if is_active else 1024,
                                "cacheLimitBytes": 128,
                            },
                        },
                        500 if fail_status and is_active else 200,
                    )

                def do_POST(self, requests=requests, active=active):
                    body = json.loads(
                        self.rfile.read(int(self.headers["Content-Length"]))
                    )
                    requests.append(body)
                    loaded = body["prompt"].startswith(" hello")
                    active.set()
                    if loaded:
                        time.sleep(0.6)
                    active.clear()
                    self.reply(
                        {
                            "choices": [{"text": "hello", "finish_reason": "length"}],
                            "usage": {
                                "prompt_tokens": 1024 if loaded else 13,
                                "completion_tokens": 32,
                                "tokens_per_second": 40,
                            },
                        }
                    )

            server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
            worker = threading.Thread(target=server.serve_forever, daemon=True)
            worker.start()
            try:
                with tempfile.TemporaryDirectory() as folder:
                    output = Path(folder)
                    process = Mock()
                    cfg = {
                        "context_cap": 65536,
                        "benchmark_endpoint": f"http://127.0.0.1:{server.server_port}",
                        "orchestration": {"served_model_id": "fixture/model"},
                        "benchmark_launch_command": "fixture-launcher --model-dir /fixture",
                        "required_runner_environment": {"MEI_RUNTIME_BASE": folder},
                        "mei_qualification": {
                            "repeats": 1,
                            "loaded_tokens": 1024,
                            "decode_tokens": 32,
                            "status_timeout": 1,
                        },
                    }
                    with (
                        patch.object(
                            qualification.subprocess, "Popen", return_value=process
                        ),
                        patch.object(
                            qualification.subprocess,
                            "run",
                            return_value=Mock(returncode=0),
                        ),
                        patch.object(qualification, "wait_ready"),
                        patch.object(
                            qualification,
                            "prepare_prompts",
                            return_value={
                                "short": "list integers",
                                "loaded": " hello" * 1024,
                            },
                        ),
                        patch.object(
                            qualification, "verify_mei_runtime", return_value={}
                        ),
                        patch("builtins.print"),
                    ):
                        rc = qualification.child(cfg, output)
                    result = json.loads((output / "qualification.json").read_text())
                    self.assertEqual(rc, 1 if fail_status else 0)
                    self.assertEqual(
                        result["status"], "failed" if fail_status else "passed"
                    )
                    self.assertTrue(result["server_stopped"])
                    process.terminate.assert_called_once()
                    process.wait.assert_called_once()
                    samples = [
                        json.loads(line)
                        for line in (output / "status-samples.jsonl")
                        .read_text()
                        .splitlines()
                    ]
                    self.assertTrue(samples)
                    self.assertEqual(samples, result["status_samples"])
                    for sample in samples:
                        if sample["ok"]:
                            self.assertEqual(sample["memory"]["cacheLimitBytes"], 128)
                            self.assertEqual(
                                sample["memory"]["memoryLimitBytes"],
                                2048 if sample["active_generations"] else 1024,
                            )
                    if not fail_status:
                        active_samples = [
                            r for r in samples if r["active_generations"] > 0
                        ]
                        self.assertTrue(active_samples)
                        self.assertTrue(
                            all(
                                r["memory"]["memoryLimitBytes"] == 2048
                                for r in active_samples
                            )
                        )
                    measured = [
                        row for row in result["rows"] if row["phase"] == "measured"
                    ]
                    self.assertEqual(len(measured), 0 if fail_status else 2)
                    self.assertEqual(len(requests), 2 if fail_status else 6)
                    self.assertTrue(
                        all(
                            body["temperature"] == 0 and body["seed"] == 1
                            for body in requests
                        )
                    )
            finally:
                server.shutdown()
                server.server_close()
                worker.join()

    def test_predeclared_bounds_reject_bad_contexts_and_boolean_counts(self):
        config: dict[str, Any] = {
            "context_cap": 65536,
            "mei_qualification": {
                "repeats": 10,
                "loaded_tokens": 30000,
                "decode_tokens": 128,
                "status_timeout": 1,
            },
        }
        self.assertEqual(qualification_settings(config)["repeats"], 10)
        for field, value in (
            ("repeats", True),
            ("repeats", 0),
            ("loaded_tokens", 65536),
            ("decode_tokens", 0),
            ("status_timeout", float("nan")),
        ):
            bad = copy.deepcopy(config)
            bad["mei_qualification"][field] = value
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                qualification_settings(bad)
        with self.assertRaises(ValueError):
            qualification_settings(config | {"context_cap": 30000})

    def test_empty_or_invalid_completions_are_not_speed_observations(self):
        response: dict[str, Any] = {
            "choices": [{"text": "hello", "finish_reason": "length"}],
            "usage": {
                "completion_tokens": 32,
                "prompt_tokens": 30000,
                "tokens_per_second": 45.5,
            },
        }
        self.assertEqual(observable(response)["text"], "hello")
        legacy = copy.deepcopy(response)
        legacy["choices"][0] = {
            "message": {"content": "hello"},
            "finish_reason": "length",
        }
        self.assertEqual(observable(legacy), observable(response))
        ambiguous = copy.deepcopy(legacy)
        ambiguous["choices"][0]["text"] = "different"
        with self.assertRaises(ValueError):
            observable(ambiguous)
        for value in (0, -1, float("nan"), float("inf"), None, True):
            bad = copy.deepcopy(response)
            bad["usage"]["tokens_per_second"] = value
            with self.subTest(speed=value), self.assertRaises(ValueError):
                observable(bad)
        response["choices"][0]["text"] = ""
        with self.assertRaises(ValueError):
            observable(response)

    def test_missing_repeats_status_overlap_or_teardown_cannot_qualify(self):
        evidence: dict[str, Any] = {
            "status": "passed",
            "settings": {"repeats": 2},
            "server_stopped": True,
            "status_samples": [{"ok": True, "active_generations": 1}],
            "rows": [
                {
                    "phase": "measured",
                    "context": context,
                    "repeat": repeat,
                    "decode_tps": 40,
                }
                for context in ("short", "loaded")
                for repeat in (1, 2)
            ],
        }
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder)

            def check(result):
                (output / "qualification.json").write_text(json.dumps(result))
                return succeeded(output)

            self.assertTrue(check(evidence))
            (output / "config.yaml").write_text("invalid: [yaml")
            self.assertFalse(check(evidence))
            (output / "config.yaml").unlink()
            self.assertFalse(
                check(
                    evidence
                    | {"clean_speed_launch_required": True, "clean_speed_launch": {}}
                )
            )
            self.assertFalse(check(evidence | {"swift_acceptance_required": True}))
            self.assertTrue(
                check(
                    evidence
                    | {
                        "swift_acceptance_required": True,
                        "swift_acceptance": {"passed": True},
                    }
                )
            )
            cases = []
            missing = copy.deepcopy(evidence)
            missing["rows"].pop()
            cases.append(missing)
            duplicate = copy.deepcopy(evidence)
            duplicate["rows"][0] = duplicate["rows"][1]
            cases.append(duplicate)
            for key, value in (
                ("status_samples", []),
                ("status_samples", [{"ok": True, "active_generations": 0}]),
                ("status_samples", [{"ok": False, "active_generations": 1}]),
                ("server_stopped", False),
                ("status", "running"),
            ):
                cases.append(evidence | {key: value})
            invalid_rate = copy.deepcopy(evidence)
            invalid_rate["rows"][0]["decode_tps"] = float("nan")
            cases.append(invalid_rate)
            for case in cases:
                with self.subTest(case=case):
                    self.assertFalse(check(case))


class DeclaredSpeedProfileTests(unittest.TestCase):
    def test_every_speed_profile_reaches_the_diagnostic_monitor(self):
        root = Path(__file__).resolve().parents[2]
        matrix = json.loads(
            (
                root / "artifacts/mei-upstream-qualification-20261106/speed-matrix.json"
            ).read_text()
        )
        with tempfile.TemporaryDirectory() as folder:
            for index, cell in enumerate(matrix["cells"]):
                with self.subTest(model=cell["model"], cell=cell["cell"]):
                    path = root / cell["config"]
                    content = path.read_bytes()
                    cfg = yaml.safe_load(content)
                    cfg["required_runner_environment"]["MEI_RUNTIME_BASE"] = str(
                        Path(folder) / f"runtime-{index}"
                    )
                    with (
                        patch(
                            "sys.argv",
                            [
                                "qualify_mei_release.py",
                                "--config",
                                str(path),
                                "--output",
                                str(Path(folder) / f"output-{index}"),
                            ],
                        ),
                        patch.object(
                            qualification,
                            "committed_native_config",
                            return_value=(cfg, content),
                        ),
                        patch.object(qualification, "validate_owned_config"),
                        patch.object(qualification.socket, "socket") as socket,
                        patch.object(
                            qualification, "monitor_child", return_value=0
                        ) as monitor,
                    ):
                        socket.return_value.__enter__.return_value.connect_ex.return_value = 1
                        self.assertEqual(qualification.main(), 0)
                        monitor.assert_called_once()
                        self.assertIs(
                            monitor.call_args.kwargs["diagnostic_check"],
                            qualification.succeeded,
                        )
                    self.assertFalse((Path(folder) / f"output-{index}").exists())


if __name__ == "__main__":
    unittest.main()
