import io
import json
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mei_stream_timing import measure_chat_stream


class Response(io.BytesIO):
    headers = SimpleNamespace(get_content_type=lambda: "text/event-stream")


class StreamingTimingTests(unittest.TestCase):
    def measure(self, *, done=True):
        frames = [
            {"choices": [{"delta": {"role": "assistant"}}]},
            {"choices": [{"delta": {"reasoning_content": "think"}}]},
            {"choices": [{"delta": {"content": "answer"}}]},
            {"choices": [{"delta": {}, "finish_reason": "stop"}]},
            {"choices": [], "usage": {"prompt_tokens": 30_000, "completion_tokens": 2}},
        ]
        events = [(json.dumps(frame), True) for frame in frames]
        if done:
            events.append(("[DONE]", True))
        clock = iter([10, 11, 12, 14, 17, 18, 19, 20])
        with (
            patch("mei_stream_timing.urllib.request.urlopen", return_value=Response()),
            patch(
                "mei_stream_timing._read_sse_events", return_value=(x for x in events)
            ),
            patch("mei_stream_timing.time", SimpleNamespace(monotonic=clock.__next__)),
        ):
            return measure_chat_stream("http://127.0.0.1:8024/v1", {})

    def test_role_does_not_count_and_reasoning_precedes_visible_text(self):
        result = self.measure()
        self.assertEqual(result["headers_seconds"], 1)
        self.assertEqual(result["first_generated_seconds"], 4)
        self.assertEqual(result["first_visible_seconds"], 7)
        self.assertEqual(result["wall_seconds"], 10)
        self.assertEqual(result["reasoning"], "think")
        self.assertEqual(result["content"], "answer")

    def test_incomplete_stream_does_not_yield_timing(self):
        with self.assertRaisesRegex(ValueError, "without text, finish, usage or DONE"):
            self.measure(done=False)
