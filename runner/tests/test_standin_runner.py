"""Current stand-in dispatch, failure closure, provenance and reporting."""

import copy
import json
import subprocess
import sys
import tempfile
import threading
import unittest
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import run_bench as bench
from build_standin_report import build_report, render
from run_standin_suite import (
    admission,
    committed_config,
    generation,
    run_suite,
    run_task,
)
from standin_domain import SCOPE
from standin_tasks import SMOKE_IDS, cases
from test_standin_domain import ScriptedClient, response

CFG = {
    "model": "fixture-model",
    "inference_engine": "mei",
    "benchmark_scope": SCOPE,
    "standin_generation_profile": "native",
    "standin_cache_policy": "test-only fake backend",
    "generation_profiles": {"native": {"temperature": 1.0, "top_p": 0.95, "top_k": 20}},
}


class FailClient:
    def __init__(self, failure):
        self.failure = failure

    def __call__(self, *args, **kwargs):
        raise self.failure


@contextmanager
def backend(replies, *, truncate_final=False, final_error=False):
    observed = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            observed.append(
                json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            )
            payload = replies.pop(0)
            message = payload["choices"][0]["message"]
            delta = {"content": message.get("content")}
            if message.get("tool_calls"):
                delta["tool_calls"] = [
                    dict(t, index=i) for i, t in enumerate(message["tool_calls"])
                ]
            event = {
                "choices": [
                    {
                        "delta": delta,
                        "finish_reason": payload["choices"][0]["finish_reason"],
                    }
                ],
                "usage": payload["usage"],
            }
            is_final = not message.get("tool_calls")
            if is_final and truncate_final:
                event["choices"][0]["finish_reason"] = None
            events = f"data: {json.dumps(event)}\n\n"
            if is_final and final_error:
                events += 'data: {"error":{"message":"injected backend failure"}}\n\n'
            if not (is_final and truncate_final):
                events += "data: [DONE]\n\n"
            body = events.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *_args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/v1", observed
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


class StandinRunnerTests(unittest.TestCase):
    def test_real_http_stream_reaches_domain_and_native_sampler_without_policy_overrides(
        self,
    ):
        from run_prompt import call_backend_streaming

        case = cases()[0]
        replies = [
            response(calls=case.reference_actions[0]),
            response(content="Saved once to family Shopping."),
        ]
        with backend(replies) as (base, observed):
            got = run_task(
                case, call_backend_streaming, base, "served-exact", generation(CFG)[1]
            )
        self.assertTrue(got["grade"]["pass"], got["grade"])
        self.assertEqual(len(observed), 2)
        self.assertEqual(observed[0]["model"], "served-exact")
        self.assertEqual(observed[0]["temperature"], 1.0)
        self.assertEqual(observed[0]["top_k"], 20)
        self.assertNotIn("reasoning_effort", observed[0])
        self.assertNotIn("enable_thinking", observed[0])
        self.assertGreater(got["completion_tokens"], 0)

    def test_test_only_admission_bypass_cannot_write_canonical_results(self):
        with self.assertRaisesRegex(ValueError, "cannot write canonical"):
            run_suite(
                CFG,
                b"fixture",
                "unused",
                "served",
                1,
                "development",
                True,
                _test_skip_admission=True,
            )

    def test_completed_suite_uses_fresh_state_and_separate_append_only_log(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            legacy = root / "results/log.jsonl"
            legacy.parent.mkdir()
            sentinel = b'{"old":"immutable"}\n'
            legacy.write_bytes(sentinel)
            selected = [c for c in cases() if c.task_id in SMOKE_IDS]
            rows, run_dir = run_suite(
                CFG,
                b"pinned fixture",
                "unused",
                "served",
                1,
                "development",
                True,
                root,
                ScriptedClient(selected),
                _test_skip_admission=True,
            )
            self.assertEqual(len(rows), 4)
            self.assertTrue(all(r["pass"] for r in rows))
            self.assertTrue(
                all(
                    r["benchmark_scope"] == SCOPE and not r["rank_eligible"]
                    for r in rows
                )
            )
            self.assertEqual(legacy.read_bytes(), sentinel)
            self.assertEqual(
                json.loads((run_dir / "manifest.json").read_text())["status"],
                "completed",
            )
            build_report(root)
            report = (root / "results/STANDIN.md").read_text()
            self.assertIn("4/4", report)
            self.assertIn("Not Peixinho app acceptance", report)
            raw = (root / "results/standin/log.jsonl").read_bytes()
            run_suite(
                CFG,
                b"pinned fixture",
                "unused",
                "served",
                1,
                "development",
                True,
                root,
                ScriptedClient(selected),
                _test_skip_admission=True,
            )
            self.assertTrue(
                (root / "results/standin/log.jsonl").read_bytes().startswith(raw)
            )

    def test_transport_or_interruption_persists_partial_artifact_and_missing_coverage(
        self,
    ):
        for failure, status in [
            (OSError("connection refused"), "infrastructure_stopped"),
            (KeyboardInterrupt(), "interrupted"),
        ]:
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as td:
                root = Path(td)
                rows, run_dir = run_suite(
                    CFG,
                    b"config",
                    "unused",
                    "served",
                    1,
                    "development",
                    True,
                    root,
                    FailClient(failure),
                    _test_skip_admission=True,
                )
                self.assertEqual(len(rows), 1)
                self.assertFalse(rows[0]["pass"])
                self.assertTrue(rows[0]["harness_error"])
                self.assertTrue((root / rows[0]["result_path"]).exists())
                manifest = json.loads((run_dir / "manifest.json").read_text())
                self.assertEqual(manifest["status"], status)
                build_report(root)
                self.assertIn("1/4 | 3", (root / "results/STANDIN.md").read_text())

    def test_malformed_empty_token_and_turn_limits_are_model_failures(self):
        samples = [
            (response(content=""), "empty_final"),
            (response(content="partial", finish="length"), "token_limit"),
            ({"choices": []}, "malformed_response"),
            ({"usage": {"completion_tokens": "bad"}}, "malformed_usage"),
        ]
        for reply, error in samples:
            with self.subTest(error=error):
                client = lambda *a, value=reply, **kw: (
                    copy.deepcopy(value),
                    None,
                    None,
                )
                result = run_task(cases()[0], client, "unused", "served", {})
                self.assertEqual(result["error"], error)
                expected_class = (
                    "truncation"
                    if error == "token_limit"
                    else "protocol_error"
                    if error.startswith("malformed")
                    else "task_failure"
                )
                self.assertEqual(result["failure_class"], expected_class)
                self.assertFalse(result["grade"]["pass"])
        looping = lambda *a, **kw: (
            response(calls=[("search_records", {"query": ""})]),
            None,
            None,
        )
        result = run_task(cases()[0], looping, "unused", "served", {})
        self.assertEqual(result["error"], "turn_limit")
        self.assertEqual(result["turns"], 12)
        self.assertEqual(len(result["responses"]), 12)

    def test_partial_completed_messages_survive_later_transport_failure(self):
        case = cases()[0]

        class Partial:
            count = 0

            def __call__(self, *a, **kw):
                self.count += 1
                if self.count == 1:
                    return response(calls=case.reference_actions[0]), 0.1, 0.2
                raise OSError("socket lost mid stream")

        result = run_task(case, Partial(), "unused", "served", {})
        self.assertEqual(result["failure_class"], "harness_error")
        self.assertTrue(result["final"]["receipts"])
        self.assertTrue(any(m["role"] == "tool" for m in result["messages"]))

    def test_unknown_tools_and_nonobject_arguments_are_denied_without_harness_crash(
        self,
    ):
        for calls in [[("terminal", {"command": "not real"})], [("capture", [])]]:
            case = cases()[0]
            script = iter(
                [response(calls=calls), response(content="No changes were made.")]
            )
            result = run_task(
                case,
                lambda *a, script=script, **kw: (next(script), None, None),
                "unused",
                "served",
                {},
            )
            self.assertFalse(result["grade"]["pass"])
            self.assertEqual(result["failure_class"], "task_failure")
            self.assertEqual(result["grade"]["denied_operations"], 1)
            self.assertEqual(result["grade"]["invalid_tool_calls"], 1)
            self.assertGreaterEqual(result["grade"]["unsafe_attempts"], 1)

    def test_admission_requires_dependent_tool_result_and_grounded_final(self):
        class Probe:
            def __call__(self, *args, **kwargs):
                messages = args[2]
                tool_results = [
                    json.loads(m["content"]) for m in messages if m["role"] == "tool"
                ]
                if not tool_results:
                    reply = response(calls=[("admission_probe", {"stage": "begin"})])
                elif len(tool_results) == 1:
                    reply = response(
                        calls=[
                            (
                                "admission_probe",
                                {"stage": "verify", "code": tool_results[0]["code"]},
                            )
                        ]
                    )
                else:
                    reply = response(content=tool_results[-1]["verified"])
                return reply, 0.01, 0.02

        self.assertEqual(admission(Probe(), "unused", "served", {})["status"], "passed")
        simple = lambda *a, **kw: (response(content="Looks good"), None, None)
        self.assertEqual(admission(simple, "unused", "served", {})["status"], "failed")

    def test_admission_timeout_and_unexpected_client_fault_preserve_evidence(self):
        from run_prompt import StreamStall

        timed = admission(
            FailClient(StreamStall("first_progress", 1, 1)), "unused", "served", {}
        )
        self.assertEqual(timed["status"], "failed")
        self.assertEqual(timed["timeout_phase"], "first_progress")
        interrupted = admission(FailClient(KeyboardInterrupt()), "unused", "served", {})
        self.assertEqual(interrupted["status"], "interrupted")
        task = run_task(
            cases()[0],
            FailClient(RuntimeError("decoder failure")),
            "unused",
            "served",
            {},
        )
        self.assertEqual(task["failure_class"], "harness_error")
        self.assertFalse(task["grade"]["pass"])

    def test_report_rejects_duplicate_trial_provenance_mismatch_and_false_completion(
        self,
    ):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            selected = [c for c in cases() if c.task_id in SMOKE_IDS]
            rows, run_dir = run_suite(
                CFG,
                b"fixture",
                "unused",
                "served",
                1,
                "development",
                True,
                root,
                ScriptedClient(selected),
                _test_skip_admission=True,
            )
            manifest = json.loads((run_dir / "manifest.json").read_text())
            for bad in [
                rows + [rows[0]],
                rows[:-1],
                [dict(rows[0], config_hash="different"), *rows[1:]],
            ]:
                with self.assertRaises(ValueError):
                    render(bad, [manifest])

    def test_admitted_config_retains_exact_bytes_after_authored_file_changes(self):
        from types import SimpleNamespace

        import run_standin_suite as suite

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            path = root / "config.yaml"
            original = yaml.safe_dump(CFG).encode()
            path.write_bytes(original)
            with (
                patch.object(suite, "REPO", root),
                patch.object(
                    suite.subprocess,
                    "run",
                    return_value=SimpleNamespace(returncode=0, stdout=original),
                ),
            ):
                cfg, content = committed_config(path)
            path.write_text("changed: true")
            self.assertEqual(content, original)
            self.assertEqual(cfg["model"], CFG["model"])

    def test_config_must_be_committed_and_sampler_explicit(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "uncommitted.yaml"
            path.write_text(yaml.safe_dump(CFG))
            with self.assertRaises(ValueError):
                committed_config(path)
        for bad in [{}, dict(CFG, standin_generation_profile="missing")]:
            with self.assertRaises(ValueError):
                generation(bad)

    def test_orchestrator_routes_workflow_scope_and_preserves_owned_cleanup(self):
        with tempfile.TemporaryDirectory() as td:
            config = Path(td) / "config.yaml"
            cfg = dict(
                CFG,
                orchestration={
                    "raw_port": None,
                    "api_base_url": "http://local.invalid/v1",
                    "api_key_env": "FAKE_KEY",
                    "served_model_id": "served",
                    "viable": "model_only",
                },
                standin_smoke=True,
            )
            config.write_text(yaml.safe_dump(cfg))
            calls = []

            def run(command, **kwargs):
                from types import SimpleNamespace

                calls.append(command)
                if "run_standin_suite.py" in str(command):
                    Path(command[command.index("--summary-out") + 1]).write_text(
                        json.dumps(
                            [
                                {"task_id": task_id, "trial": 1, "pass": True}
                                for task_id in SMOKE_IDS
                            ]
                        )
                    )
                return SimpleNamespace(returncode=0)

            with (
                patch.dict("os.environ", FAKE_KEY="test"),
                patch.object(bench, "run", side_effect=run),
                patch.object(bench, "admitted_config_snapshot", return_value=config),
                patch(
                    "run_standin_suite.committed_config",
                    return_value=(cfg, config.read_bytes()),
                ),
            ):
                self.assertTrue(bench.run_one(config))
            self.assertFalse(any("run_prompt_suite.py" in str(c) for c in calls))
            self.assertTrue(any("stop_mei_server.sh" in str(c) for c in calls))
            self.assertFalse(any("hermes" in str(c).lower() for c in calls))

    def test_public_cli_does_not_offer_admission_or_legacy_bypass(self):
        root = Path(__file__).resolve().parents[1]
        result = subprocess.run(
            [sys.executable, str(root / "run_standin_suite.py"), "--help"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0)
        self.assertNotIn("skip-admission", result.stdout)
        self.assertNotIn("hermes", result.stdout.lower())


if __name__ == "__main__":
    unittest.main()
