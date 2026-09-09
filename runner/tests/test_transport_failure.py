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
import ast
import unittest
from pathlib import Path

RUNNER = Path(__file__).resolve().parent.parent

# Extract ONLY the classifier and its marker tuple, and exec them in a bare
# namespace. Executing run_prompt_suite.py as a module works in isolation but
# not alongside the other test modules, which change the working directory —
# the import then exits early and the module ends up half-populated, so the
# function under test silently disappears. Parsing out the two definitions has
# no import side effects and cannot be perturbed by test ordering.
_SOURCE = (RUNNER / "run_prompt_suite.py").read_text()
_tree = ast.parse(_SOURCE)
_wanted = {"_TRANSPORT_FAILURE_MARKERS", "_is_transport_failure"}
_nodes = [
    n for n in _tree.body
    if (isinstance(n, ast.FunctionDef) and n.name in _wanted)
    or (isinstance(n, ast.Assign)
        and any(getattr(t, "id", None) in _wanted for t in n.targets))
]
assert len(_nodes) == 2, (
    f"expected the marker tuple and the classifier in run_prompt_suite.py, found {len(_nodes)}")
_ns: dict = {}
exec(compile(ast.Module(body=_nodes, type_ignores=[]), "run_prompt_suite.py", "exec"), _ns)
_is_transport_failure = _ns["_is_transport_failure"]


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
                self.assertTrue(_is_transport_failure(text))

    def test_an_http_status_means_the_server_answered(self):
        # The context-cap rejection is a REAL engine response and must stay a
        # graded result — it is how the exact-cap probe is supposed to behave.
        for text in (
            "HTTP 400: request exceeded context cap: 65537 prompt tokens > 65536 allowed",
            "HTTP 500: engine_error",
            "HTTP 503: model loading",
        ):
            with self.subTest(text=text):
                self.assertFalse(_is_transport_failure(text))

    def test_model_and_harness_failures_are_untouched(self):
        for text in (
            "exceeded max_turns (40) without a final non-tool-call response",
            "stream stalled in phase 'stream_idle': no qualifying progress",
            "TIMEOUT (model/engine): task exceeded its 900s budget",
            None,
            "",
        ):
            with self.subTest(text=text):
                self.assertFalse(_is_transport_failure(text))


if __name__ == "__main__":
    unittest.main()
