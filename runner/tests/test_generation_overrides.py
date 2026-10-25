"""Tests for task-specific generation settings (2026-09-22, infrastructure
only): per-request sampling/reasoning overrides on runner/run_prompt.py and
the named generation_profiles mechanism in runner/run_prompt_suite.py /
runner/run_bench.py.

Policy invariants under test (user direction, 2026-09-22):
  - overrides are OPT-IN: a config without generation_profiles /
    hermes_ops_generation_profile or a run without --generation-profile
    produces the historic wire body (temperature + max_tokens only) — old
    rows and old configs are untouched;
  - profiles are EXPLICIT: a name that is not declared, a field name that is
    not supported, or a wrongly-typed value fails loudly (SystemExit /
    ValueError) instead of being silently dropped from the payload;
  - reasoning_effort is NEVER invented: a profile that does not declare it
    sends no reasoning_effort field, even when the config's human-facing
    top-level `reasoning_effort:` metadata says something;
  - effort values are forwarded EXACTLY (xhigh stays xhigh) so the
    capability/high vs practical/medium lane split is expressible;
  - the config-level selector applies to the hermes_ops suite only; a
    --generation-profile CLI flag can select a different lane per run.

No live inference backend is required: payloads are inspected through
run_prompt.build_chat_body(), a recording FakeSSEServer (same pattern as
test_run_prompt_timeouts.py), and the real run_prompt.py / run_prompt_suite.py
entry points.

Run: uv run --locked python -m unittest discover -s runner/tests -q
"""
import json
import shutil
import subprocess
import sys
import tempfile
import threading
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


class _RecordingHandler(BaseHTTPRequestHandler):
    """Serves a fixed healthy SSE script and records the FIRST request body."""

    protocol_version = "HTTP/1.1"

    def log_message(self, *_args):
        return

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length)
        try:
            self.server.last_request_body = json.loads(body)
        except (json.JSONDecodeError, UnicodeDecodeError):
            self.server.last_request_body = None
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "close")
        self.end_headers()
        try:
            self.wfile.write(f"data: {_chunk(content='hello there')}\n\n".encode())
            self.wfile.write(b"data: [DONE]\n\n")
            self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass


class RecordingSSEServer:
    def __init__(self):
        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), _RecordingHandler)
        self.httpd.daemon_threads = True
        self.httpd.last_request_body = None
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)

    @property
    def url(self):
        host, port = self.httpd.server_address[:2]
        return f"http://{host}:{port}/v1"

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *_exc):
        self.httpd.shutdown()
        self.httpd.server_close()


LEGACY_BODY = {
    "model": "m",
    "messages": [{"role": "user", "content": "hello"}],
    "max_tokens": 4096,
    "stream": True,
    "stream_options": {"include_usage": True},
}

# What the SUITE produces for a no-profile run: the legacy body PLUS an
# explicit temperature=0 (run_prompt_suite.py says 0 out loud to preserve
# the historic deterministic wire shape whenever no profile is selected).
LEGACY_SUITE_BODY = dict(LEGACY_BODY, temperature=0, model="fake-model")


class BuildChatBodyTests(unittest.TestCase):
    """Absent overrides must keep the exact historic wire shape; configured
    overrides must reach the payload verbatim."""

    def test_absent_overrides_produce_the_exact_legacy_body(self):
        # temperature=None is itself the "absent" case: no sampling fields
        # at all on the wire (the suite-level --temperature 0 guarantee is
        # tested separately below).
        body = run_prompt.build_chat_body(
            model="m", messages=[{"role": "user", "content": "hello"}],
            tools=None, temperature=None, max_tokens=4096,
        )
        self.assertEqual(body, LEGACY_BODY)
        self.assertNotIn("temperature", body)

    def test_explicit_temperature_zero_still_lands_in_the_body(self):
        # The suite's no-profile path passes --temperature 0 explicitly; a
        # caller-chosen 0 must be sent, only the silent default is gone.
        body = run_prompt.build_chat_body(
            model="m", messages=[{"role": "user", "content": "hello"}],
            tools=None, temperature=0, max_tokens=4096,
        )
        self.assertEqual(body["temperature"], 0)

    def test_temperature_is_a_first_class_optional_override(self):
        body = run_prompt.build_chat_body(
            model="m", messages=[{"role": "user", "content": "hello"}],
            tools=None, temperature=1.0, max_tokens=4096,
            top_p=0.95, reasoning_effort="xhigh",
        )
        self.assertEqual(body["temperature"], 1.0)
        self.assertNotIn("top_k", body)

    def test_tools_only_appear_when_given(self):
        tools = [{"type": "function", "function": {"name": "t", "parameters": {}}}]
        body = run_prompt.build_chat_body(
            model="m", messages=[{"role": "user", "content": "hi"}],
            tools=tools, temperature=0, max_tokens=4096,
        )
        self.assertEqual(body["tools"], tools)
        self.assertNotIn("top_p", body)

    def test_all_supported_overrides_reach_the_body_verbatim(self):
        body = run_prompt.build_chat_body(
            model="m", messages=[{"role": "user", "content": "hi"}],
            tools=None, temperature=0, max_tokens=4096,
            top_p=0.95, top_k=20, min_p=0,
            repetition_penalty=1.0, presence_penalty=1.5,
            frequency_penalty=0.0, reasoning_effort="xhigh",
        )
        self.assertEqual(body["top_p"], 0.95)
        self.assertEqual(body["top_k"], 20)
        self.assertEqual(body["min_p"], 0)
        self.assertEqual(body["repetition_penalty"], 1.0)
        self.assertEqual(body["presence_penalty"], 1.5)
        self.assertEqual(body["frequency_penalty"], 0.0)
        # forwarded exactly, never normalized to another effort vocabulary
        self.assertEqual(body["reasoning_effort"], "xhigh")
        self.assertEqual(body["temperature"], 0)
        self.assertEqual(body["max_tokens"], 4096)

    def test_partial_overrides_add_only_those_fields(self):
        body = run_prompt.build_chat_body(
            model="m", messages=[{"role": "user", "content": "hi"}],
            tools=None, temperature=0, max_tokens=4096,
            top_p=0.9, reasoning_effort="none",
        )
        self.assertEqual(body["top_p"], 0.9)
        self.assertEqual(body["reasoning_effort"], "none")
        for absent in ("top_k", "min_p", "repetition_penalty",
                       "presence_penalty", "frequency_penalty"):
            self.assertNotIn(absent, body)


class NormalizeGenerationOverridesTests(unittest.TestCase):
    """Malformed/unsupported overrides fail loudly, never silently dropped."""

    def test_none_and_empty_are_valid_noops(self):
        self.assertEqual(run_prompt.normalize_generation_overrides(None), {})
        self.assertEqual(run_prompt.normalize_generation_overrides({}), {})

    def test_valid_mapping_passes_through_untouched(self):
        profile = {"top_p": 0.95, "top_k": 20, "reasoning_effort": "high"}
        self.assertEqual(run_prompt.normalize_generation_overrides(profile), profile)

    def test_unknown_field_fails_naming_the_field(self):
        with self.assertRaises(ValueError) as ctx:
            run_prompt.normalize_generation_overrides({"temprature": 1.0})
        self.assertIn("temprature", str(ctx.exception))
        self.assertIn("unsupported", str(ctx.exception))

    def test_non_mapping_fails(self):
        with self.assertRaises(ValueError):
            run_prompt.normalize_generation_overrides([("top_p", 0.9)])

    def test_wrong_type_fails_clearly(self):
        with self.assertRaises(ValueError) as ctx:
            run_prompt.normalize_generation_overrides({"top_k": 20.5})
        self.assertIn("expected int", str(ctx.exception))
        with self.assertRaises(ValueError):
            run_prompt.normalize_generation_overrides({"top_p": "hot"})
        with self.assertRaises(ValueError):
            run_prompt.normalize_generation_overrides({"reasoning_effort": 3})

    def test_boolean_values_are_rejected_even_for_numeric_fields(self):
        # bool is an int subclass; a profile flag is not a sampling number.
        with self.assertRaises(ValueError) as ctx:
            run_prompt.normalize_generation_overrides({"top_p": True})
        self.assertIn("boolean", str(ctx.exception))

    def test_empty_reasoning_effort_is_rejected(self):
        with self.assertRaises(ValueError):
            run_prompt.normalize_generation_overrides({"reasoning_effort": "   "})


class RunPromptCliTests(unittest.TestCase):
    """CLI flag propagation: configured overrides reach the HTTP payload of a
    real run_prompt.py invocation; absent flags leave the legacy body."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp()).resolve()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.spec = self.tmp / "spec.json"
        self.spec.write_text(json.dumps({"user_prompt": "hello"}))

    def _run(self, *extra):
        with RecordingSSEServer() as server:
            cmd = [sys.executable, str(Path(run_prompt.__file__)),
                   "--base-url", server.url, "--model", "m",
                   "--spec", str(self.spec), "--max-turns", "1",
                   *extra]
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            body = server.httpd.last_request_body
        self.assertEqual(proc.returncode, 0, proc.stderr)
        return body, json.loads(proc.stdout)

    def test_no_flags_keeps_the_legacy_body_on_the_wire(self):
        body, result = self._run()
        self.assertEqual(body, LEGACY_BODY)
        self.assertIsNone(result["error"])

    def test_configured_flags_reach_the_http_payload(self):
        body, result = self._run(
            "--temperature", "1.0", "--top-p", "0.95", "--top-k", "20",
            "--min-p", "0", "--repetition-penalty", "1.0",
            "--presence-penalty", "1.5", "--frequency-penalty", "0",
            "--reasoning-effort", "xhigh",
        )
        self.assertEqual(body["temperature"], 1.0)
        self.assertEqual(body["top_p"], 0.95)
        self.assertEqual(body["top_k"], 20)
        self.assertEqual(body["min_p"], 0)
        self.assertEqual(body["repetition_penalty"], 1.0)
        self.assertEqual(body["presence_penalty"], 1.5)
        self.assertEqual(body["frequency_penalty"], 0)
        self.assertEqual(body["reasoning_effort"], "xhigh")
        self.assertIsNone(result["error"])

    def test_malformed_cli_value_fails_fast(self):
        proc = subprocess.run(
            [sys.executable, str(Path(run_prompt.__file__)),
             "--base-url", "http://127.0.0.1:1/v1", "--model", "m",
             "--spec", str(self.spec), "--top-k", "fast"],
            capture_output=True, text=True, timeout=60,
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("invalid int value", proc.stderr)


_FAKE_PROFILES = {
    "generation_profiles": {
        "capability": {
            "temperature": 1.0, "top_p": 0.95, "top_k": 20, "min_p": 0,
            "presence_penalty": 1.5, "repetition_penalty": 1.0,
            "reasoning_effort": "xhigh",
        },
        "practical": {
            "temperature": 0.8, "top_p": 0.9,
            "reasoning_effort": "medium",
        },
        "no_effort": {
            "temperature": 1.0, "top_p": 0.95,
        },
        "bare": {
            # NO temperature: a selected profile must never silently force
            # temperature=0 — the backend's configured/default value applies.
            "top_p": 0.8,
        },
    },
}


class SuiteProfileIntegrationTests(unittest.TestCase):
    """Config-driven profile selection end to end: drive
    run_prompt_suite.main(_allow_archived_suites=True) against a recording backend and inspect the
    request body each task actually sent. REPO is redirected to a throwaway
    tree, so the real results/log.jsonl is never opened."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp()).resolve()
        (self.tmp / "runner").mkdir()
        (self.tmp / "tasks").mkdir()
        (self.tmp / "results").mkdir()
        real_runner = Path(run_prompt.__file__).parent
        for name in ("run_prompt.py", "grade_prompt.py"):
            shutil.copy2(real_runner / name, self.tmp / "runner" / name)
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def _write_suite(self, name="hermes_ops"):
        import yaml
        spec = {
            "suite": name,
            "runner": "prompt",
            "timeout_seconds": 20,
            "max_turns": 3,
            "tasks": [{
                "id": f"{name}-one",
                "type": "prompt-response",
                "prompt_spec": {"user_prompt": "hello"},
                "check": {"type": "contains", "text": "hello there"},
            }],
        }
        (self.tmp / "tasks" / f"{name}.yaml").write_text(yaml.safe_dump(spec))

    def _run_suite(self, config, suite="hermes_ops", generation_profile=None):
        import bench_common
        import yaml
        config_path = self.tmp / "fake_config.yaml"
        config_path.write_text(yaml.safe_dump(config))
        argv = [
            "run_prompt_suite.py", "--suite", suite,
            "--base-url", "http://127.0.0.1:1/v1", "--model", "fake-model",
            "--inference-engine", "fake",
            "--config", str(config_path),
            "--summary-out", str(self.tmp / "summary.json"),
        ]
        if generation_profile:
            argv += ["--generation-profile", generation_profile]
        with unittest.mock.patch.object(run_prompt_suite, "REPO", self.tmp), \
                unittest.mock.patch.object(bench_common, "REPO", self.tmp), \
                unittest.mock.patch.object(sys, "argv", argv):
            run_prompt_suite.main(_allow_archived_suites=True)
        return json.loads((self.tmp / "summary.json").read_text())

    def _run_suite_expecting_failure(self, config, suite="hermes_ops",
                                     generation_profile=None):
        """Assert the suite REFUSES to start (SystemExit, no rows) and return
        the message."""
        with self.assertRaises(SystemExit) as ctx:
            self._run_suite(config, suite=suite,
                            generation_profile=generation_profile)
        rows_path = self.tmp / "summary.json"
        self.assertFalse(rows_path.exists())
        return str(ctx.exception.code)

    def test_config_selecting_a_profile_applies_it_to_hermes_ops(self):
        config = dict(_FAKE_PROFILES, hermes_ops_generation_profile="capability")
        self._write_suite()
        with RecordingSSEServer() as server:
            self._run_suite_with_url(config, server.url)
            body = server.httpd.last_request_body
        self.assertEqual(body["temperature"], 1.0)
        self.assertEqual(body["top_p"], 0.95)
        self.assertEqual(body["top_k"], 20)
        self.assertEqual(body["min_p"], 0)
        self.assertEqual(body["presence_penalty"], 1.5)
        self.assertEqual(body["repetition_penalty"], 1.0)
        self.assertEqual(body["reasoning_effort"], "xhigh")

    def test_config_selector_never_leaks_into_other_suites(self):
        # sanity/fixture suites are determinism gates: the hermes_ops-only
        # selector must leave their bodies at the historic defaults.
        config = dict(_FAKE_PROFILES, hermes_ops_generation_profile="capability")
        self._write_suite(name="sanity")
        with RecordingSSEServer() as server:
            self._run_suite_with_url(config, server.url, suite="sanity")
            body = server.httpd.last_request_body
        self.assertEqual(body, LEGACY_SUITE_BODY)
        self.assertNotIn("top_p", body)

    def test_profiles_without_a_selector_change_nothing(self):
        # opt-in: declaring profiles but never selecting one must not alter
        # the historic deterministic hermes_ops body.
        config = dict(_FAKE_PROFILES)
        self._write_suite()
        with RecordingSSEServer() as server:
            self._run_suite_with_url(config, server.url)
            body = server.httpd.last_request_body
        self.assertEqual(body, LEGACY_SUITE_BODY)

    def test_cli_generation_profile_overrides_the_config_selector(self):
        # lane selection without editing the config: config defaults to the
        # capability lane, this run forces the practical/medium lane.
        config = dict(_FAKE_PROFILES, hermes_ops_generation_profile="capability")
        self._write_suite()
        with RecordingSSEServer() as server:
            self._run_suite_with_url(config, server.url,
                                     generation_profile="practical")
            body = server.httpd.last_request_body
        self.assertEqual(body["temperature"], 0.8)
        self.assertEqual(body["top_p"], 0.9)
        self.assertEqual(body["reasoning_effort"], "medium")
        self.assertNotIn("top_k", body)

    def test_profile_without_effort_never_invents_one(self):
        # "do not silently assume medium": a selected profile that declares
        # no reasoning_effort sends no reasoning_effort field, even though
        # the config's human-facing metadata names an effort.
        config = dict(_FAKE_PROFILES, hermes_ops_generation_profile="no_effort",
                      reasoning_effort="medium")
        self._write_suite()
        with RecordingSSEServer() as server:
            self._run_suite_with_url(config, server.url)
            body = server.httpd.last_request_body
        self.assertEqual(body["temperature"], 1.0)
        self.assertNotIn("reasoning_effort", body)

    def test_selected_profile_without_temperature_never_forces_zero(self):
        # User policy, 2026-09-22: a profile that does not declare
        # temperature must NOT silently fall back to the historic
        # temperature=0 — the request omits temperature so the backend
        # serves its configured/default value.
        config = dict(_FAKE_PROFILES, hermes_ops_generation_profile="bare")
        self._write_suite()
        with RecordingSSEServer() as server:
            self._run_suite_with_url(config, server.url)
            body = server.httpd.last_request_body
        self.assertEqual(body["top_p"], 0.8)
        self.assertNotIn("temperature", body)
        self.assertNotIn("reasoning_effort", body)

    def test_unknown_selector_name_fails_before_any_task(self):
        config = dict(_FAKE_PROFILES, hermes_ops_generation_profile="nope")
        self._write_suite()
        msg = self._run_suite_expecting_failure(config)
        self.assertIn("nope", msg)
        self.assertIn("capability", msg)  # message lists declared profiles

    def test_unknown_cli_profile_name_fails(self):
        config = dict(_FAKE_PROFILES)
        self._write_suite()
        msg = self._run_suite_expecting_failure(
            config, generation_profile="nope")
        self.assertIn("nope", msg)

    def test_unknown_field_inside_a_profile_fails_clearly(self):
        config = {"generation_profiles": {"bad": {"temprature": 1.0}}}
        self._write_suite()
        msg = self._run_suite_expecting_failure(config)
        self.assertIn("temprature", msg)

    def test_wrong_type_inside_a_profile_fails_clearly(self):
        config = {"generation_profiles": {"bad": {"top_k": "fast"}}}
        self._write_suite()
        msg = self._run_suite_expecting_failure(config)
        self.assertIn("top_k", msg)

    def test_max_tokens_inside_a_profile_is_rejected(self):
        # hermes_ops_max_tokens is the single max-token source; letting
        # profiles carry max_tokens would create duplicate/conflicting
        # sources. The field must fail loudly, not be silently dropped.
        config = {"generation_profiles": {"bad": {"max_tokens": 16384}}}
        self._write_suite()
        msg = self._run_suite_expecting_failure(config)
        self.assertIn("max_tokens", msg)

    def test_legacy_hermes_ops_max_tokens_still_applies_with_a_profile(self):
        # backward compatibility: an old config field and a new profile
        # compose — max_tokens comes from the legacy key, sampling from the
        # profile.
        config = dict(_FAKE_PROFILES, hermes_ops_generation_profile="capability",
                      hermes_ops_max_tokens=16384)
        self._write_suite()
        with RecordingSSEServer() as server:
            self._run_suite_with_url(config, server.url)
            body = server.httpd.last_request_body
        self.assertEqual(body["max_tokens"], 16384)
        self.assertEqual(body["reasoning_effort"], "xhigh")

    # -- helpers ---------------------------------------------------------

    def _argv_for(self, base_url, suite="hermes_ops", generation_profile=None):
        argv = [
            "run_prompt_suite.py", "--suite", suite,
            "--base-url", base_url, "--model", "fake-model",
            "--inference-engine", "fake",
            "--config", str(self.tmp / "fake_config.yaml"),
            "--summary-out", str(self.tmp / "summary.json"),
        ]
        if generation_profile:
            argv += ["--generation-profile", generation_profile]
        return argv

    def _run_suite_with_url(self, config, base_url, suite="hermes_ops",
                            generation_profile=None):
        import bench_common
        import yaml
        config_path = self.tmp / "fake_config.yaml"
        config_path.write_text(yaml.safe_dump(config))
        with unittest.mock.patch.object(run_prompt_suite, "REPO", self.tmp), \
                unittest.mock.patch.object(bench_common, "REPO", self.tmp), \
                unittest.mock.patch.object(
                    sys, "argv",
                    self._argv_for(base_url, suite=suite,
                                   generation_profile=generation_profile)):
            run_prompt_suite.main(_allow_archived_suites=True)
        return json.loads((self.tmp / "summary.json").read_text())


class RunBenchProfileArgTests(unittest.TestCase):
    """run_bench.py carries the run-level lane selectors and forwards them to
    the right stages: generation profile to the one-shot Hermes Ops suite
    (never sanity), coding reasoning effort to every coding suite."""

    def test_parser_accepts_a_generation_profile(self):
        import legacy_run_bench as rb
        args = rb.build_arg_parser().parse_args(
            ["--config", "configs/x/y.yaml", "--generation-profile", "capability"]
        )
        self.assertEqual(args.generation_profile, "capability")

    def test_parser_accepts_a_coding_reasoning_level(self):
        import legacy_run_bench as rb
        args = rb.build_arg_parser().parse_args(
            ["--config", "configs/x/y.yaml", "--reasoning", "xhigh"]
        )
        self.assertEqual(args.reasoning, "xhigh")

    def test_parser_rejects_an_unknown_reasoning_level(self):
        import legacy_run_bench as rb
        with self.assertRaises(SystemExit):
            rb.build_arg_parser().parse_args(
                ["--config", "configs/x/y.yaml", "--reasoning", "turbo"]
            )

    def test_parser_defaults_to_no_profile(self):
        import legacy_run_bench as rb
        args = rb.build_arg_parser().parse_args(["--config", "configs/x/y.yaml"])
        self.assertIsNone(args.generation_profile)
        self.assertIsNone(args.reasoning)

    def test_run_one_forwards_the_profile_to_the_impl(self):
        import legacy_run_bench as rb
        with tempfile.TemporaryDirectory() as td, \
                unittest.mock.patch.object(rb, "_run_one_impl", return_value=True) as impl:
            config_path = Path(td) / "config.yaml"
            config_path.write_text("inference_engine: fake\n")
            rb.run_one(config_path, generation_profile="practical",
                       reasoning="medium")
        _, kwargs = impl.call_args
        self.assertEqual(kwargs["generation_profile"], "practical")
        self.assertEqual(kwargs["reasoning"], "medium")


class RunFixtureSuiteReasoningTests(unittest.TestCase):
    """The coding profile: `hermes chat --reasoning` is passed ONLY when
    selected, forwarded exactly, and a config value outside the vocabulary
    fails loudly."""

    def _fake_proc(self):
        proc = unittest.mock.MagicMock()
        proc.communicate.return_value = ("", "")
        proc.returncode = 0
        proc.pid = 1
        # subprocess.run() (used by the sandbox probe inside run_hermes)
        # enters the process as a context manager and must get the SAME
        # object back, not a fresh MagicMock child.
        proc.__enter__.return_value = proc
        return proc

    def test_run_hermes_forwards_the_reasoning_flag_exactly(self):
        import run_fixture_suite as rfs
        fake = self._fake_proc()
        with unittest.mock.patch.object(rfs.subprocess, "Popen", return_value=fake) as popen:
            rfs.run_hermes("do it", "/tmp", "prov", "model", 40, 30,
                           reasoning="xhigh")
        cmd = popen.call_args.args[0]
        self.assertIn("--reasoning", cmd)
        self.assertEqual(cmd[cmd.index("--reasoning") + 1], "xhigh")

    def test_run_hermes_omits_reasoning_by_default(self):
        import run_fixture_suite as rfs
        fake = self._fake_proc()
        with unittest.mock.patch.object(rfs.subprocess, "Popen", return_value=fake) as popen:
            rfs.run_hermes("do it", "/tmp", "prov", "model", 40, 30)
        cmd = popen.call_args.args[0]
        self.assertNotIn("--reasoning", cmd)

    def test_config_value_outside_the_vocabulary_fails_before_any_task(self):
        import bench_common
        import run_fixture_suite as rfs
        import tempfile
        import yaml
        tmp = Path(tempfile.mkdtemp()).resolve()
        self.addCleanup(shutil.rmtree, tmp, True)
        (tmp / "tasks").mkdir()
        (tmp / "results").mkdir()
        (tmp / "tasks" / "kiem_mini.yaml").write_text(yaml.safe_dump({
            "suite": "kiem_mini", "runner": "fixture",
            "timeout_seconds": 900,
            "tasks": [{"id": "kiem_mini-feature", "type": "feature"}],
        }))
        config_path = tmp / "cfg.yaml"
        config_path.write_text(yaml.safe_dump({"coding_reasoning_effort": "turbo"}))
        argv = [
            "run_fixture_suite.py", "--suite", "kiem_mini",
            "--hermes-provider", "p", "--hermes-model", "m",
            "--inference-engine", "fake", "--config", str(config_path),
            "--only-task", "kiem_mini-feature",
        ]
        with unittest.mock.patch.object(rfs, "REPO", tmp), \
                unittest.mock.patch.object(bench_common, "REPO", tmp), \
                unittest.mock.patch.object(sys, "argv", argv):
            with self.assertRaises(SystemExit) as ctx:
                rfs.main()
        self.assertIn("turbo", str(ctx.exception.code))
        self.assertIn("hermes chat --reasoning", str(ctx.exception.code))


if __name__ == "__main__":
    unittest.main()