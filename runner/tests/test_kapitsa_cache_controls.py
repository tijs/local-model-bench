import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from kapitsa_cache_controls import compare, signature


def response(cached=0, text="reasoning", call_id="random-id"):
    return {"choices": [{"finish_reason": "tool_calls", "message": {
        "content": None, "reasoning_content": text,
        "tool_calls": [{"id": call_id, "function": {
            "name": "add_numbers", "arguments": '{"a":15,"b":27}',
        }}],
    }}], "usage": {"prompt_tokens_details": {"cached_tokens": cached}}}


class KapitsaCacheControlTests(unittest.TestCase):
    def test_output_signature_ignores_dynamic_call_ids_but_keeps_reasoning_and_arguments(self):
        self.assertEqual(signature(response(call_id="a")), signature(response(call_id="b")))
        changed = copy.deepcopy(response())
        changed["choices"][0]["message"]["tool_calls"][0]["function"]["arguments"] = '{"a":14,"b":27}'
        self.assertNotEqual(signature(response()), signature(changed))
        self.assertNotEqual(signature(response()), signature(response(text="changed")))

    def test_cache_verdict_requires_cold_determinism_real_hit_and_two_cold_misses(self):
        self.assertTrue(compare(response(50), response(), response())["passed"])
        self.assertFalse(compare(response(), response(), response())["passed"])
        self.assertFalse(compare(response(50), response(1), response())["passed"])
        row = compare(response(50), response(text="a"), response(text="b"))
        self.assertFalse(row["cold_determinism"])
        self.assertFalse(row["cached_matches_cold"])
        self.assertFalse(row["passed"])
