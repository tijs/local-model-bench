"""Paired-context evidence must retain exact counts, native timing and partials."""

import copy
import json
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import qualify_llama_context as qualification


def response(tokens=17):
    return {
        "tokens_predicted": 128,
        "tokens_evaluated": tokens,
        "content": "1, 2, 3, 4",
        "truncated": False,
        "stop_type": "limit",
        "timings": {
            "prompt_n": tokens,
            "cache_n": 0,
            "predicted_n": 127,
            "predicted_ms": 2540,
            "predicted_per_second": 50,
        },
    }


class LlamaContextTests(unittest.TestCase):
    def test_native_decode_rate_and_output_count_are_not_recomputed(self):
        actual = response()
        self.assertEqual(qualification.observed(actual, 17)["completion_tokens"], 128)
        # Native engine rate is127/2.54=50;128/2.54 is intentionally different.
        self.assertEqual(actual["timings"]["predicted_per_second"], 50)

    def test_cached_truncated_wrong_count_or_bad_rate_are_refused(self):
        for key, value in (
            ("tokens_predicted", 127),
            ("tokens_predicted", True),
            ("tokens_evaluated", 18),
            ("truncated", True),
            ("stop_type", "eos"),
            ("content", ""),
            ("cache_n", 1),
            ("prompt_n", 16),
            ("predicted_per_second", 0),
            ("predicted_per_second", True),
            ("predicted_per_second", float("nan")),
        ):
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                actual = response()
                target = actual["timings"] if key in actual["timings"] else actual
                target[key] = value
                qualification.observed(actual, 17)

    def test_complete_client_loop_and_invalid_response_preserve_raw_evidence(self):
        for bad_loaded in (False, True):
            requests = []

            class Handler(BaseHTTPRequestHandler):
                def log_message(self, format, *args):
                    pass

                def reply(self, body):
                    data = json.dumps(body).encode()
                    self.send_response(200)
                    self.send_header("Content-Length", str(len(data)))
                    self.end_headers()
                    self.wfile.write(data)

                def do_GET(self):
                    self.reply({"data": []})

                def do_POST(self, requests=requests, bad_loaded=bad_loaded):
                    body = json.loads(
                        self.rfile.read(int(self.headers["Content-Length"]))
                    )
                    if self.path == "/tokenize":
                        self.reply(
                            {"tokens": list(range(len(body["content"].split())))}
                        )
                    else:
                        requests.append(body)
                        n = len(body["prompt"])
                        self.reply(response(n - 1 if bad_loaded and n == 1024 else n))

            server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                with tempfile.TemporaryDirectory() as folder:
                    output = Path(folder)
                    cfg = {
                        "context_cap": 65536,
                        "benchmark_endpoint": f"http://127.0.0.1:{server.server_port}/v1",
                        "benchmark_launch_command": "llama-server --model /fixture.gguf",
                        "model_sha256": "a" * 64,
                        "runtime": {
                            "binary_sha256": "b" * 64,
                            "revision": "c" * 40,
                            "shared_libraries": {"libfixture.dylib": "d" * 64},
                        },
                        "context_speed_qualification": {
                            "repeats": 5,
                            "loaded_tokens": 1024,
                            "decode_tokens": 128,
                        },
                    }
                    process = Mock()
                    process.poll.return_value = None
                    # The supervisor saves the committed config before its child starts.
                    (output / "config.yaml").write_text(json.dumps(cfg))
                    with (
                        patch.object(
                            qualification.subprocess, "Popen", return_value=process
                        ),
                        patch.object(
                            qualification,
                            "verify_llama_runtime",
                            return_value=cfg["runtime"],
                        ),
                        patch.object(qualification, "sha256", return_value="a" * 64),
                    ):
                        rc = qualification.child(cfg, output)
                    self.assertEqual(rc, 1 if bad_loaded else 0)
                    self.assertEqual(qualification.succeeded(output), not bad_loaded)
                    saved = json.loads((output / "qualification.json").read_text())
                    self.assertTrue(saved["server_stopped"])
                    process.terminate.assert_called_once()
                    raw = (output / "responses.jsonl").read_text().splitlines()
                    self.assertEqual(len(raw), 2 if bad_loaded else 14)
                    for request in requests:
                        self.assertFalse(request["cache_prompt"])
                        self.assertEqual(
                            (
                                request["temperature"],
                                request["top_k"],
                                request["n_predict"],
                            ),
                            (0, 1, 128),
                        )
                        self.assertEqual(request["presence_penalty"], 0)
                    if bad_loaded:
                        self.assertEqual(len(saved["rows"]), 1)
                        continue
                    self.assertEqual(
                        sum(r["phase"] == "measured" for r in saved["rows"]), 10
                    )
                    # Every mutable evidence dimension is tied to the raw response.
                    for mutate in (
                        lambda q: q["rows"].pop(),
                        lambda q: q["rows"][0].update(decode_tps=99),
                        lambda q: q.update(post_run_model_sha256="c" * 64),
                        lambda q: q.update(
                            post_run_runtime_identity={"binary_sha256": "c" * 64}
                        ),
                        lambda q: q.update(server_stopped=False),
                    ):
                        changed = copy.deepcopy(saved)
                        mutate(changed)
                        (output / "qualification.json").write_text(json.dumps(changed))
                        self.assertFalse(qualification.succeeded(output))
                    changed = copy.deepcopy(saved)
                    for row in changed["rows"]:
                        if row["context"] == "loaded":
                            row["observable"]["prompt_tokens"] = 1000
                            row["response"]["tokens_evaluated"] = 1000
                            row["response"]["timings"]["prompt_n"] = 1000
                    (output / "qualification.json").write_text(json.dumps(changed))
                    self.assertFalse(qualification.succeeded(output))
                    (output / "qualification.json").write_text(json.dumps(saved))
                    prompts = json.loads((output / "prompts.json").read_text())
                    prompts["loaded"][0] += 1
                    (output / "prompts.json").write_text(json.dumps(prompts))
                    self.assertFalse(qualification.succeeded(output))
            finally:
                server.shutdown()
                server.server_close()
                thread.join()


if __name__ == "__main__":
    unittest.main()
