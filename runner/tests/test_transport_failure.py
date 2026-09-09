"""A server that vanishes mid-run must be a HARNESS error, not a model failure.

Real incident 2026-09-09: a benchmark chain was killed to repoint it at a
different build, and two hermes_ops rows landed as ordinary graded FAILs
carrying `<urlopen error [Errno 61] Connection refused>`. run_prompt.py reports
an unreachable server as a normal `error` string and still exits with parseable
JSON, so run_prompt_suite.py's JSONDecodeError check could not see it. The row
was then indistinguishable from the model getting the task wrong, and counted
against its pass rate. The same would happen to any run whose server OOMs,
crashes, or is restarted underneath it.
"""
import importlib.util
import sys
import unittest
from pathlib import Path

RUNNER = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RUNNER))
_spec = importlib.util.spec_from_file_location("rps", RUNNER / "run_prompt_suite.py")
_rps = importlib.util.module_from_spec(_spec)
try:
    _spec.loader.exec_module(_rps)
except SystemExit:
    pass


class TransportFailureClassification(unittest.TestCase):
    def test_unreachable_server_is_a_transport_failure(self):
        for text in (
            "request failed: <urlopen error [Errno 61] Connection refused>",
            "request failed: <urlopen error [Errno 54] Connection reset by peer>",
            "RemoteDisconnected('Remote end closed connection without response')",
            "('Connection aborted.', ConnectionResetError(54, 'Connection reset by peer'))",
            "Failed to establish a new connection: [Errno 61]",
        ):
            with self.subTest(text=text):
                self.assertTrue(_rps._is_transport_failure(text))

    def test_an_http_status_means_the_server_answered(self):
        # The context-cap rejection is a REAL engine response and must stay a
        # graded result — it is how the exact-cap probe is supposed to behave.
        for text in (
            "HTTP 400: request exceeded context cap: 65537 prompt tokens > 65536 allowed",
            "HTTP 500: engine_error",
            "HTTP 503: model loading",
        ):
            with self.subTest(text=text):
                self.assertFalse(_rps._is_transport_failure(text))

    def test_model_and_harness_failures_are_untouched(self):
        for text in (
            "exceeded max_turns (40) without a final non-tool-call response",
            "stream stalled in phase 'stream_idle': no qualifying progress",
            "TIMEOUT (model/engine): task exceeded its 900s budget",
            None,
            "",
        ):
            with self.subTest(text=text):
                self.assertFalse(_rps._is_transport_failure(text))


if __name__ == "__main__":
    unittest.main()
