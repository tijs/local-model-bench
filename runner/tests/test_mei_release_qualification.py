"""Reject incomplete or invalid runtime qualification evidence."""

import copy
import json
import sys
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from unittest.mock import Mock, patch

from tokenizers import Tokenizer, models, pre_tokenizers

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import qualify_mei_release as qualification
from qualify_mei_release import observable, qualification_settings, succeeded


class QualificationTests(unittest.TestCase):
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
                    self.reply(
                        {
                            "status": "ok",
                            "scheduler": {"activeGenerations": int(active.is_set())},
                        },
                        500 if fail_status else 200,
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
                    self.assertTrue((output / "status-samples.jsonl").read_text())
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


if __name__ == "__main__":
    unittest.main()
