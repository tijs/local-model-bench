"""Declared request seeds must reach HTTP and durable generation metadata."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from run_prompt import (
    build_chat_body,
    call_backend_streaming,
    normalize_generation_overrides,
)
from test_generation_overrides import RecordingSSEServer


class RequestSeedTests(unittest.TestCase):
    def test_seed_is_optional_and_validated_before_use(self):
        kwargs = {
            "model": "m",
            "messages": [],
            "tools": None,
            "temperature": 1,
            "max_tokens": 10,
        }
        self.assertNotIn("seed", build_chat_body(**kwargs))
        for value in (-1, 2**32, True, 1.0, "17"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                normalize_generation_overrides({"seed": value})
        self.assertEqual(
            normalize_generation_overrides({"seed": 2**32 - 1}), {"seed": 2**32 - 1}
        )

    def test_seed_zero_and_nonzero_survive_real_http_and_metadata(self):
        for seed in (0, 17):
            with self.subTest(seed=seed), RecordingSSEServer() as server:
                response, _, _ = call_backend_streaming(
                    server.url,
                    "m",
                    [{"role": "user", "content": "hello"}],
                    None,
                    1.0,
                    5,
                    10,
                    seed=seed,
                )
                self.assertEqual(server.httpd.last_request_body["seed"], seed)
                self.assertEqual(response["generation"]["seed"], seed)
