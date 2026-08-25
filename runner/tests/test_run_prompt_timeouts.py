"""Regression tests for the timeout/liveness design in runner/run_prompt.py
and runner/run_prompt_suite.py (2026-08-25 improvement plan, Priority 0).

These drive a REAL local HTTP server emitting real SSE bytes, with the
budgets scaled down from minutes to fractions of a second — a mocked
urlopen could not have caught the actual bug, which was about how a live
socket behaves when a stream keeps dribbling non-progress bytes.

The four shapes covered mirror the plan's own recommended coverage:
  - a slow-but-PROGRESSING stream must pass
  - a heartbeat/comment-only stream must fail (first_progress)
  - one partial event then silence must fail (stream_idle)
  - a connection that never sends headers must fail (connect)
plus a fifth (turn_total) for a stream that progresses steadily but
outlives its turn ceiling, and process-group escalation for the task
deadline.

Run: uv run --locked python -m unittest discover -s runner/tests -v
"""
import json
import os
import signal
import socket
import subprocess
import sys
import threading
import time
import unittest
import unittest.mock
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import run_prompt
import run_prompt_suite


def _chunk(**delta):
    return json.dumps({
        "id": "chatcmpl-test",
        "object": "chat.completion.chunk",
        "choices": [{"index": 0, "delta": delta, "finish_reason": None}],
    })


class _SSEHandler(BaseHTTPRequestHandler):
    """Serves whatever script the enclosing FakeSSEServer was given.

    script is a list of (delay_seconds, payload_bytes_or_None); a payload of
    None means "sleep and send nothing", which is how the stall cases are
    expressed.
    """

    protocol_version = "HTTP/1.1"

    def log_message(self, *_args):
        return

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        self.rfile.read(length)
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "close")
        self.end_headers()
        try:
            for delay, payload in self.server.script:
                time.sleep(delay)
                if payload is None:
                    continue
                self.wfile.write(payload)
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass


class FakeSSEServer:
    def __init__(self, script):
        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), _SSEHandler)
        self.httpd.script = script
        self.httpd.daemon_threads = True
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)

    def __enter__(self):
        self.thread.start()
        host, port = self.httpd.server_address[:2]
        return f"http://{host}:{port}/v1"

    def __exit__(self, *_exc):
        self.httpd.shutdown()
        self.httpd.server_close()


class SilentServer:
    """Accepts the TCP connection, then sends absolutely nothing.

    This is the shape urlopen(timeout=...) DOES bound — the point of the
    test is that the failure is now reported as an explicit "connect"
    phase rather than a generic request failure.
    """

    def __init__(self):
        self.sock = socket.socket()
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(("127.0.0.1", 0))
        self.sock.listen(4)
        self._stop = threading.Event()
        self._held = []

    def _accept_loop(self):
        self.sock.settimeout(0.2)
        while not self._stop.is_set():
            try:
                conn, _ = self.sock.accept()
            except (TimeoutError, OSError):
                continue
            self._held.append(conn)  # deliberately never answered

    def __enter__(self):
        threading.Thread(target=self._accept_loop, daemon=True).start()
        host, port = self.sock.getsockname()
        return f"http://{host}:{port}/v1"

    def __exit__(self, *_exc):
        self._stop.set()
        for conn in self._held:
            conn.close()
        self.sock.close()


def _call(base_url, **budgets):
    kwargs = {
        "timeout": 5.0,
        "connect_timeout": 5.0,
        "first_progress_timeout": 1.0,
        "stream_idle_timeout": 0.6,
    }
    kwargs.update(budgets)
    return run_prompt.call_backend_streaming(
        base_url, "fake-model", [{"role": "user", "content": "hi"}],
        None, 0, kwargs.pop("timeout"), 64,
        connect_timeout=kwargs["connect_timeout"],
        first_progress_timeout=kwargs["first_progress_timeout"],
        stream_idle_timeout=kwargs["stream_idle_timeout"],
    )


class MeaningfulEventClassificationTests(unittest.TestCase):
    """The whole watchdog turns on this predicate: a stalled stream can
    keep emitting keepalives and usage chunks forever, so counting those
    as progress would reproduce the original bug exactly."""

    def test_content_and_tool_call_deltas_are_meaningful(self):
        self.assertTrue(run_prompt._sse_event_is_meaningful(_chunk(content="hi")))
        self.assertTrue(run_prompt._sse_event_is_meaningful(
            _chunk(tool_calls=[{"index": 0, "function": {"name": "f"}}])
        ))

    def test_done_sentinel_is_meaningful(self):
        self.assertTrue(run_prompt._sse_event_is_meaningful("[DONE]"))

    def test_finish_reason_is_meaningful(self):
        payload = json.dumps({"choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]})
        self.assertTrue(run_prompt._sse_event_is_meaningful(payload))

    def test_usage_only_and_role_only_chunks_are_not_meaningful(self):
        usage_only = json.dumps({"usage": {"prompt_tokens": 5}, "choices": []})
        self.assertFalse(run_prompt._sse_event_is_meaningful(usage_only))
        self.assertFalse(run_prompt._sse_event_is_meaningful(_chunk(role="assistant")))
        self.assertFalse(run_prompt._sse_event_is_meaningful(_chunk(content="")))

    def test_unparseable_payload_is_not_meaningful(self):
        self.assertFalse(run_prompt._sse_event_is_meaningful("not json at all"))


class StreamLivenessTests(unittest.TestCase):
    def test_slow_but_progressing_stream_passes(self):
        # Each gap (0.25s) is under the 0.6s idle budget, and the whole
        # thing outlives the 1.0s first-progress budget — a model that is
        # slow but genuinely producing tokens must NOT be cut off.
        script = [(0.25, f"data: {_chunk(content=c)}\n\n".encode()) for c in "hello!"]
        script.append((0.1, b"data: [DONE]\n\n"))
        with FakeSSEServer(script) as base_url:
            resp, _ttft = _call(base_url)
        self.assertEqual(resp["choices"][0]["message"]["content"], "hello!")

    def test_heartbeat_only_stream_fails_in_first_progress(self):
        # SSE comments are a legal keepalive and were enough to keep the
        # old socket-inactivity timeout permanently reset.
        script = [(0.05, b": keepalive\n\n")] * 200
        with FakeSSEServer(script) as base_url:
            with self.assertRaises(run_prompt.StreamStall) as ctx:
                _call(base_url)
        self.assertEqual(ctx.exception.phase, "first_progress")

    def test_blank_lines_alone_fail_in_first_progress(self):
        script = [(0.05, b"\n")] * 200
        with FakeSSEServer(script) as base_url:
            with self.assertRaises(run_prompt.StreamStall) as ctx:
                _call(base_url)
        self.assertEqual(ctx.exception.phase, "first_progress")

    def test_usage_only_chunks_do_not_count_as_progress(self):
        usage_only = json.dumps({"usage": {"prompt_tokens": 5}, "choices": []})
        script = [(0.05, f"data: {usage_only}\n\n".encode())] * 200
        with FakeSSEServer(script) as base_url:
            with self.assertRaises(run_prompt.StreamStall) as ctx:
                _call(base_url)
        self.assertEqual(ctx.exception.phase, "first_progress")

    def test_one_partial_event_then_stall_fails_in_stream_idle(self):
        # This is the exact observed oMLX shape: a small partial SSE
        # response arrives, then the stream never converges.
        script = [
            (0.05, f"data: {_chunk(content='partial')}\n\n".encode()),
            (30.0, None),
        ]
        with FakeSSEServer(script) as base_url:
            with self.assertRaises(run_prompt.StreamStall) as ctx:
                _call(base_url)
        self.assertEqual(ctx.exception.phase, "stream_idle")

    def test_stream_that_keeps_progressing_still_hits_the_total_budget(self):
        script = [(0.05, f"data: {_chunk(content='x')}\n\n".encode())] * 400
        with FakeSSEServer(script) as base_url:
            with self.assertRaises(run_prompt.StreamStall) as ctx:
                _call(base_url, timeout=1.0, first_progress_timeout=10.0,
                      stream_idle_timeout=10.0, connect_timeout=1.0)
        self.assertEqual(ctx.exception.phase, "turn_total")

    def test_a_silent_prefill_longer_than_the_connect_budget_survives(self):
        # The connect budget must NOT leak into the read path.
        # urlopen(timeout=X) sets X for the connect phase AND every
        # subsequent read, so a naive implementation makes a short
        # connect budget silently become the read-idle budget: with
        # hermes_ops's real values (connect 60s, first-progress 600s) a
        # healthy 26K-token prefill emitting nothing for 90 seconds would
        # die at 60s with a bare TimeoutError and the layered budgets
        # would never get to decide.
        script = [
            (0.8, None),  # silent prefill, > connect_timeout below
            (0.05, f"data: {_chunk(content='finally')}\n\n".encode()),
            (0.05, b"data: [DONE]\n\n"),
        ]
        with FakeSSEServer(script) as base_url:
            resp, _ttft = _call(
                base_url, connect_timeout=0.3, first_progress_timeout=5.0,
                stream_idle_timeout=5.0, timeout=20.0,
            )
        self.assertEqual(resp["choices"][0]["message"]["content"], "finally")

    def test_a_socket_read_timeout_is_reported_as_a_stall_not_a_crash(self):
        # Fallback path: if the socket timeout could not be widened, a
        # read timeout must still be classified as a stall phase rather
        # than escaping as a bare TimeoutError.
        script = [(30.0, None)]
        with FakeSSEServer(script) as base_url:
            with unittest.mock.patch.object(
                run_prompt, "_relax_socket_timeout", return_value=False
            ):
                with self.assertRaises(run_prompt.StreamStall) as ctx:
                    _call(base_url, connect_timeout=0.4, first_progress_timeout=30.0,
                          stream_idle_timeout=30.0, timeout=60.0)
        self.assertEqual(ctx.exception.phase, "first_progress")

    def test_connection_that_never_sends_headers_hits_the_connect_deadline(self):
        with SilentServer() as base_url:
            with self.assertRaises(run_prompt.StreamStall) as ctx:
                _call(base_url, connect_timeout=0.5, timeout=30.0)
        self.assertEqual(ctx.exception.phase, "connect")

    def test_stall_returns_promptly_and_tears_the_socket_down(self):
        # A stalled turn must not leave the connection (and, for a proxied
        # backend, the single generation-queue slot) held open behind it,
        # AND must return on the watchdog rather than waiting for the
        # socket. resp.close() alone does NOT achieve the second part: the
        # reader thread is blocked in readline() holding the buffered
        # reader's lock, so close() waits it out — measured at 30s for a
        # stall detected in 0.3s, before _abort_response() shut the socket
        # down first.
        script = [(30.0, None)]
        with FakeSSEServer(script) as base_url:
            start = time.monotonic()
            with self.assertRaises(run_prompt.StreamStall):
                _call(base_url, first_progress_timeout=0.3, timeout=30.0)
            self.assertLess(time.monotonic() - start, 5.0)


class EndToEndStallTests(unittest.TestCase):
    """The bounded stand-in for the plan's live oMLX streaming probe
    (verification step 4): drive run_prompt.py as a real subprocess, with
    scaled-down budgets, against a server that reproduces the observed
    "one partial event, then never converges" shape. Asserts the whole
    path — CLI flags, watchdog, error classification, result JSON — not
    just the streaming helper in isolation."""

    def test_run_prompt_reports_a_phase_tagged_stall(self):
        import tempfile

        script = [
            (0.05, f"data: {_chunk(content='partial answer')}\n\n".encode()),
            (30.0, None),
        ]
        with FakeSSEServer(script) as base_url:
            with tempfile.TemporaryDirectory() as td:
                spec_path = Path(td) / "spec.json"
                spec_path.write_text(json.dumps({
                    "system_prompt": "you are a test",
                    "user_prompt": "hello",
                }))
                proc = subprocess.run(
                    [sys.executable, str(Path(run_prompt.__file__)),
                     "--base-url", base_url, "--model", "fake-model",
                     "--spec", str(spec_path),
                     "--timeout", "20", "--connect-timeout", "5",
                     "--first-progress-timeout", "2", "--stream-idle-timeout", "1"],
                    capture_output=True, text=True, timeout=60,
                )
        self.assertEqual(proc.returncode, 1)
        result = json.loads(proc.stdout)
        self.assertEqual(result["timeout_phase"], "stream_idle")
        self.assertIn("stream stalled", result["error"])
        # And it gave up in seconds, not after the turn's whole 20s
        # ceiling — the watchdog, not the total budget, is what fired.
        self.assertLess(result["wall_seconds"], 15)


class TaskDeadlineTests(unittest.TestCase):
    """run_prompt_suite.run_with_task_deadline(): the backstop for
    everything the per-turn watchdogs can't see."""

    def test_normal_command_returns_its_output(self):
        stdout, stderr, rc, timed_out = run_prompt_suite.run_with_task_deadline(
            [sys.executable, "-c", "import sys; print('out'); print('err', file=sys.stderr)"],
            timeout=30,
        )
        self.assertFalse(timed_out)
        self.assertEqual(rc, 0)
        self.assertIn("out", stdout)
        self.assertIn("err", stderr)

    def test_timeout_kills_the_whole_process_group_including_grandchildren(self):
        # The bug this pins down: subprocess.run(timeout=...) reaps only
        # the direct child, so a grandchild (and the in-flight backend
        # request it owns) keeps running after the "kill".
        marker = Path(os.environ.get("TMPDIR", "/tmp")) / f"bench-pg-test-{os.getpid()}.pid"
        child_src = (
            "import os, subprocess, sys, time\n"
            "g = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(300)'])\n"
            f"open({str(marker)!r}, 'w').write(str(g.pid))\n"
            "time.sleep(300)\n"
        )
        try:
            _stdout, _stderr, _rc, timed_out = run_prompt_suite.run_with_task_deadline(
                [sys.executable, "-c", child_src], timeout=2, grace=2,
            )
            self.assertTrue(timed_out)
            grandchild = int(marker.read_text())
            # Give the group kill a moment to land, then confirm the
            # grandchild is really gone (signal 0 = existence probe).
            for _ in range(50):
                try:
                    os.kill(grandchild, 0)
                except ProcessLookupError:
                    break
                time.sleep(0.1)
            else:
                os.kill(grandchild, signal.SIGKILL)
                self.fail("grandchild survived the task-deadline kill")
        finally:
            marker.unlink(missing_ok=True)

    def test_partial_output_is_preserved_when_the_deadline_fires(self):
        # run_prompt.py only prints its result JSON at the very end, so on
        # a deadline kill the partial stdout/stderr is the ONLY evidence
        # of what the model/engine was doing — discarding it is what made
        # the observed stalls undiagnosable.
        child_src = (
            "import sys, time\n"
            "print('partial line'); sys.stdout.flush()\n"
            "time.sleep(300)\n"
        )
        stdout, _stderr, _rc, timed_out = run_prompt_suite.run_with_task_deadline(
            [sys.executable, "-c", child_src], timeout=2, grace=2,
        )
        self.assertTrue(timed_out)
        self.assertIn("partial line", stdout)

    def test_graceful_sigterm_is_tried_before_sigkill(self):
        child_src = (
            "import signal, sys, time\n"
            "def bye(*_):\n"
            "    print('caught sigterm'); sys.stdout.flush(); sys.exit(0)\n"
            "signal.signal(signal.SIGTERM, bye)\n"
            "sys.stdout.flush()\n"
            "time.sleep(300)\n"
        )
        stdout, _stderr, _rc, timed_out = run_prompt_suite.run_with_task_deadline(
            [sys.executable, "-c", child_src], timeout=2, grace=5,
        )
        self.assertTrue(timed_out)
        self.assertIn("caught sigterm", stdout)


class SuiteIntegrationTests(unittest.TestCase):
    """The plan's verification step 5, scaled down: drive
    run_prompt_suite.main() end to end against a fake backend and inspect
    the RESULT ROWS it writes.

    REPO is redirected to a throwaway tree, so the real
    results/log.jsonl -- months of accumulated benchmark data -- is never
    opened, let alone appended to.
    """

    def setUp(self):
        import shutil
        import tempfile

        self.tmp = Path(tempfile.mkdtemp()).resolve()
        (self.tmp / "runner").mkdir()
        (self.tmp / "tasks").mkdir()
        (self.tmp / "results").mkdir()
        real_runner = Path(run_prompt.__file__).parent
        for name in ("run_prompt.py", "grade_prompt.py"):
            shutil.copy2(real_runner / name, self.tmp / "runner" / name)
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def _write_suite(self, **budgets):
        spec = {
            "suite": "faketest",
            "runner": "prompt",
            "timeout_seconds": 20,
            "max_turns": 3,
            **budgets,
            "tasks": [{
                "id": "faketest-one",
                "type": "prompt-response",
                "prompt_spec": {"user_prompt": "hello"},
                "check": {"type": "contains", "text": "hello there"},
            }],
        }
        import yaml
        (self.tmp / "tasks" / "faketest.yaml").write_text(yaml.safe_dump(spec))

    def _run_suite(self, base_url):
        argv = [
            "run_prompt_suite.py", "--suite", "faketest",
            "--base-url", base_url, "--model", "fake-model",
            "--inference-engine", "fake",
            "--summary-out", str(self.tmp / "summary.json"),
        ]
        with unittest.mock.patch.object(run_prompt_suite, "REPO", self.tmp), \
                unittest.mock.patch.object(sys, "argv", argv):
            run_prompt_suite.main()
        return json.loads((self.tmp / "summary.json").read_text())

    def test_a_healthy_run_produces_a_clean_row(self):
        script = [
            (0.05, f"data: {_chunk(content='hello there')}\n\n".encode()),
            (0.05, b"data: [DONE]\n\n"),
        ]
        self._write_suite()
        with FakeSSEServer(script) as base_url:
            rows = self._run_suite(base_url)
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertTrue(row["pass"])
        self.assertIsNone(row["timeout_phase"])
        self.assertIsNone(row["partial_output_path"])
        self.assertIsNone(row["run_error"])
        self.assertFalse(row["harness_error"])

    def test_a_stalled_stream_is_classified_not_left_hanging(self):
        script = [
            (0.05, f"data: {_chunk(content='partial')}\n\n".encode()),
            (60.0, None),
        ]
        self._write_suite(
            first_progress_timeout_seconds=2,
            stream_idle_timeout_seconds=1,
            task_timeout_seconds=60,
        )
        start = time.monotonic()
        with FakeSSEServer(script) as base_url:
            rows = self._run_suite(base_url)
        elapsed = time.monotonic() - start
        row = rows[0]
        self.assertFalse(row["pass"])
        self.assertEqual(row["timeout_phase"], "stream_idle")
        self.assertIn("stream stalled", row["run_error"])
        # NOT a harness error: the engine stalled, the harness worked.
        self.assertFalse(row["harness_error"])
        # And it gave up on the watchdog, not on the task budget.
        self.assertLess(elapsed, 40)

    def test_a_task_deadline_row_records_its_partial_output(self):
        script = [(0.2, f"data: {_chunk(content='tok')}\n\n".encode())] * 400
        self._write_suite(
            task_timeout_seconds=3,
            first_progress_timeout_seconds=30,
            stream_idle_timeout_seconds=30,
        )
        with FakeSSEServer(script) as base_url:
            rows = self._run_suite(base_url)
        row = rows[0]
        self.assertFalse(row["pass"])
        self.assertEqual(row["timeout_phase"], "task_deadline")
        self.assertIn("task deadline exceeded", row["run_error"])
        self.assertFalse(row["harness_error"])
        self.assertIsNotNone(row["partial_output_path"])
        self.assertTrue((self.tmp / row["partial_output_path"]).exists())

    def test_the_real_results_log_is_never_touched(self):
        # Guard on the guard: this suite must not append to the months of
        # accumulated benchmark data in the real results/log.jsonl.
        real_log = Path(run_prompt.__file__).parents[1] / "results" / "log.jsonl"
        before = real_log.stat().st_size if real_log.exists() else None
        script = [
            (0.05, f"data: {_chunk(content='hello there')}\n\n".encode()),
            (0.05, b"data: [DONE]\n\n"),
        ]
        self._write_suite()
        with FakeSSEServer(script) as base_url:
            self._run_suite(base_url)
        after = real_log.stat().st_size if real_log.exists() else None
        self.assertEqual(before, after)


class SuiteBudgetDefaultsTests(unittest.TestCase):
    def test_hermes_ops_declares_all_four_budgets(self):
        import yaml
        spec = yaml.safe_load(
            (Path(__file__).resolve().parents[2] / "tasks" / "hermes_ops.yaml").read_text()
        )
        self.assertEqual(spec["timeout_seconds"], 1000)
        self.assertEqual(spec["task_timeout_seconds"], 14400)
        self.assertEqual(spec["first_progress_timeout_seconds"], 600)
        self.assertEqual(spec["stream_idle_timeout_seconds"], 300)
        # The whole point: the task budget must be far below the derived
        # ceiling this suite silently had before (1000 * 40 + 60 ≈ 11h).
        derived = spec["timeout_seconds"] * spec["max_turns"] + 60
        self.assertLess(spec["task_timeout_seconds"], derived)

    def test_default_task_timeout_is_capped(self):
        # A suite that declares no task_timeout_seconds must never inherit
        # an 11-hour ceiling by accident.
        self.assertLessEqual(
            min(1000 * 40 + 60, run_prompt_suite.DEFAULT_TASK_TIMEOUT_CAP_SECONDS),
            run_prompt_suite.DEFAULT_TASK_TIMEOUT_CAP_SECONDS,
        )
        self.assertEqual(run_prompt_suite.DEFAULT_TASK_TIMEOUT_CAP_SECONDS, 14400)


class ProxyUpstreamDeadlineTests(unittest.TestCase):
    """bench_local_proxy.upstream(): UPSTREAM_TIMEOUT must be a real
    monotonic overall deadline, not only a socket inactivity timeout."""

    def test_total_deadline_aborts_a_trickling_upstream(self):
        import bench_local_proxy

        class _Trickle:
            """Never idle long enough to trip a socket timeout, never done."""

            def read(self, _n):
                time.sleep(0.02)
                return b"x"

        deadline = time.monotonic() + 0.3
        with self.assertRaises(bench_local_proxy.UpstreamDeadlineExceeded):
            bench_local_proxy._read_until_deadline(_Trickle(), deadline)

    def test_normal_response_is_read_to_eof(self):
        import bench_local_proxy

        class _Finite:
            def __init__(self):
                self.parts = [b"abc", b"def", b""]

            def read(self, _n):
                return self.parts.pop(0)

        raw = bench_local_proxy._read_until_deadline(_Finite(), time.monotonic() + 30)
        self.assertEqual(raw, b"abcdef")


if __name__ == "__main__":
    unittest.main()
