"""No-network unit tests for runner/canary.py (deterministic quantisation canary).

Run: uv run --locked python -m unittest runner.tests.test_canary -v
   (or the repo-wide: uv run --locked python -m unittest discover -s runner/tests -v)

These tests never open a socket: request building, hashing, canonicalisation,
logprob/margin extraction, repeated-trial comparison, and the atomic artifact
writer are all exercised with in-memory data and temp files only. The suite
loader reads committed repo files (tasks/*.yaml, fixtures/hermes_ops/*) — no
network.
"""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import canary  # noqa: E402


def _task(**overrides):
    task = {
        "id": "test-task",
        "system_prompt": "You are a helpful assistant.",
        "user_prompt": "What is 15 + 27?",
        "tools": None,
        "check": {"type": "regex", "pattern": "^42$"},
        **overrides,
    }
    return task


class PromptDeterminismTests(unittest.TestCase):
    def test_identical_request_yields_identical_hash(self):
        t1 = _task()
        t2 = _task()
        r1 = canary.build_request(t1, model="m", max_tokens=512)
        r2 = canary.build_request(t2, model="m", max_tokens=512)
        self.assertEqual(canary.prompt_sha256(r1), canary.prompt_sha256(r2))

    def test_key_order_in_task_dict_does_not_change_hash(self):
        base = _task()
        shuffled = {
            "check": base["check"],
            "user_prompt": base["user_prompt"],
            "id": base["id"],
            "tools": None,
            "system_prompt": base["system_prompt"],
        }
        self.assertEqual(
            canary.prompt_sha256(canary.build_request(base, "m", 512)),
            canary.prompt_sha256(canary.build_request(shuffled, "m", 512)),
        )

    def test_any_semantic_change_changes_hash(self):
        r = canary.build_request(_task(), "m", 512)
        base = canary.prompt_sha256(r)
        self.assertNotEqual(base, canary.prompt_sha256(canary.build_request(_task(), "m", 513)))
        self.assertNotEqual(base, canary.prompt_sha256(canary.build_request(_task(), "other", 512)))
        u = _task()
        u["user_prompt"] = "What is 15 + 28?"
        self.assertNotEqual(base, canary.prompt_sha256(canary.build_request(u, "m", 512)))
        with_lp = canary.build_request(_task(), "m", 512, logprobs=True, top_logprobs=5)
        self.assertNotEqual(base, canary.prompt_sha256(with_lp))


class RequestPayloadTests(unittest.TestCase):
    def test_temperature_always_zero_and_max_tokens_explicit(self):
        body = canary.build_request(_task(), "model-x", 1024)
        self.assertEqual(body["temperature"], 0)
        self.assertEqual(body["max_tokens"], 1024)
        self.assertIn("temperature", body)
        self.assertIn("max_tokens", body)
        self.assertIs(body["stream"], False)

    def test_messages_shape_and_role_order(self):
        body = canary.build_request(_task(), "m", 512)
        self.assertEqual(
            [m["role"] for m in body["messages"]], ["system", "user"]
        )
        self.assertEqual(body["messages"][0]["content"], "You are a helpful assistant.")
        self.assertEqual(body["messages"][1]["content"], "What is 15 + 27?")

    def test_tools_included_only_when_declared(self):
        tools = [{"type": "function", "function": {"name": "add_numbers"}}]
        with_tools = canary.build_request(_task(tools=tools), "m", 512)
        self.assertEqual(with_tools["tools"], tools)
        without = canary.build_request(_task(), "m", 512)
        self.assertNotIn("tools", without)

    def test_logprobs_keys_only_when_requested(self):
        plain = canary.build_request(_task(), "m", 512)
        self.assertNotIn("logprobs", plain)
        self.assertNotIn("top_logprobs", plain)
        with_lp = canary.build_request(_task(), "m", 512, logprobs=True, top_logprobs=5)
        self.assertIs(with_lp["logprobs"], True)
        self.assertEqual(with_lp["top_logprobs"], 5)
        no_top = canary.build_request(_task(), "m", 512, logprobs=True, top_logprobs=None)
        self.assertIs(no_top["logprobs"], True)
        self.assertNotIn("top_logprobs", no_top)

    def test_multi_turn_history_is_stable_and_scripted_marker_stripped(self):
        task = dict(canary.MULTI_TURN_TASK)
        body = canary.build_request(task, "m", 512)
        roles = [m["role"] for m in body["messages"]]
        self.assertEqual(roles, ["system", "user", "assistant", "user"])
        for message in body["messages"]:
            self.assertNotIn("scripted", message)
        self.assertEqual(body["messages"][2], {"role": "assistant", "content": "Acknowledged."})
        # Stable across repeated builds.
        again = canary.build_request(task, "m", 512)
        self.assertEqual(canary.prompt_sha256(body), canary.prompt_sha256(again))


class ToolCallCanonicalisationTests(unittest.TestCase):
    def _calls(self, name, args, index=0, id_="call_1"):
        return [{
            "index": index, "id": id_, "type": "function",
            "function": {"name": name, "arguments": args},
        }]

    def test_key_order_and_whitespace_insensitive(self):
        a = self._calls("web_search", '{"query":"amsterdam","category":"weather"}')
        b = self._calls("web_search", '\n{"category":  "weather", "query": "amsterdam"} ')
        self.assertEqual(
            canary.tool_calls_sha256(a), canary.tool_calls_sha256(b)
        )

    def test_tool_call_order_is_canonicalised(self):
        # Same two calls in different array orders must hash identically.
        first = (
            self._calls("web_search", '{"query":"a"}', index=0, id_="c1")
            + self._calls("write_file", '{"path":"f.txt","content":"x"}', index=1, id_="c2")
        )
        second = (
            self._calls("write_file", '{"content":"x","path":"f.txt"}', index=1, id_="c2")
            + self._calls("web_search", '{"query":"a"}', index=0, id_="c1")
        )
        self.assertEqual(
            canary.tool_calls_sha256(first), canary.tool_calls_sha256(second)
        )

    def test_malformed_arguments_flagged_not_repaired(self):
        calls = self._calls("write_file", '{"path": "x", "content": "truncat')
        canonical = canary.canonical_tool_calls(calls)
        self.assertTrue(canonical[0]["malformed_arguments"])
        self.assertEqual(canonical[0]["arguments_canon"], '{"path": "x", "content": "truncat')

    def test_numeric_literals_are_difference_detectors(self):
        a = self._calls("add_numbers", '{"a": 15, "b": 27}')
        b = self._calls("add_numbers", '{"a": 15.0, "b": 27}')
        self.assertNotEqual(
            canary.tool_calls_sha256(a), canary.tool_calls_sha256(b)
        )

    def test_parsed_dict_arguments_equivalent_to_raw_string(self):
        raw = self._calls("web_search", '{"query": "amsterdam"}')
        parsed = self._calls("web_search", '{"query": "amsterdam"}')
        parsed[0]["function"]["arguments"] = {"query": "amsterdam"}
        self.assertEqual(
            canary.tool_calls_sha256(raw), canary.tool_calls_sha256(parsed)
        )

    def test_no_calls_hashes_to_defined_empty(self):
        self.assertEqual(canary.tool_calls_sha256([]), canary.SHA256_EMPTY)


class RepeatedOutputComparisonTests(unittest.TestCase):
    def _record(self, trial, text_hash="h1", tool_hash="t1", outcome="passed"):
        return {
            "trial": trial,
            "outcome": outcome,
            "final_text": "x" if text_hash else None,
            "final_text_sha256": text_hash,
            "tool_calls_sha256": tool_hash if outcome != "error" else None,
        }

    def test_identical_repeats_are_consistent(self):
        records = [self._record(1), self._record(2), self._record(3)]
        result = canary.trial_consistency(records)
        self.assertTrue(result["identical"])
        self.assertEqual(result["trials_compared"], 3)
        self.assertEqual(result["differing_trials"], [])

    def test_single_text_difference_is_detected(self):
        records = [
            self._record(1, text_hash="a"),
            self._record(2, text_hash="b"),
            self._record(3, text_hash="a"),
        ]
        result = canary.trial_consistency(records)
        self.assertFalse(result["identical"])
        self.assertEqual(result["differing_trials"], [2])

    def test_tool_call_difference_is_detected_even_with_same_text(self):
        records = [
            self._record(1, text_hash="same", tool_hash="t1"),
            self._record(2, text_hash="same", tool_hash="t2"),
        ]
        result = canary.trial_consistency(records)
        self.assertFalse(result["identical"])
        self.assertEqual(result["differing_trials"], [2])

    def test_error_trials_excluded_but_signalled(self):
        records = [self._record(1), self._record(2, outcome="error", text_hash=None)]
        result = canary.trial_consistency(records)
        self.assertTrue(result["identical"])
        self.assertEqual(result["trials_compared"], 1)

    def test_all_error_trials_yield_no_verdict(self):
        records = [self._record(1, outcome="error"), self._record(2, outcome="error")]
        result = canary.trial_consistency(records)
        self.assertIsNone(result["identical"])
        self.assertIn("no comparable", result["reason"])


class LogprobExtractionTests(unittest.TestCase):
    def test_flat_top_logprobs_margins(self):
        choice = {"logprobs": {"content": [
            {
                "token": "42",
                "logprob": -0.1,
                "top_logprobs": {"42": -0.1, "43": -1.4, "": -2.0},
            },
            {
                "token": "\\n",
                "logprob": -0.05,
                "top_logprobs": {"\\n": -0.05, "42": -1.1},
            },
        ]}}
        record = canary.extract_logprobs(choice)
        self.assertEqual(record["status"], "present")
        self.assertEqual(record["positions"], 2)
        self.assertEqual(record["margins"]["count"], 2)
        self.assertAlmostEqual(record["margins"]["min"], 1.05, places=6)
        self.assertAlmostEqual(record["margins"]["max"], 1.3, places=6)
        self.assertAlmostEqual(record["margins"]["mean"], 1.175, places=6)

    def test_dict_of_dict_top_logprobs_format(self):
        # llama.cpp-style: {"token": {"logprob": f, "bytes": [...]}}
        choice = {"logprobs": {"content": [
            {
                "token": "ok",
                "logprob": -0.2,
                "top_logprobs": {
                    "ok": {"logprob": -0.2, "bytes": [1]},
                    "no": {"logprob": -0.9, "bytes": [2]},
                },
            }
        ]}}
        record = canary.extract_logprobs(choice)
        self.assertEqual(record["status"], "present")
        self.assertAlmostEqual(record["margins"]["mean"], 0.7, places=6)

    def test_non_numeric_values_counted_not_coerced(self):
        choice = {"logprobs": {"content": [
            {
                "token": "x",
                "logprob": None,
                "top_logprobs": {"x": None, "y": {"logprob": "NaN"}, "z": -3.0},
            }
        ]}}
        record = canary.extract_logprobs(choice)
        # One genuinely numeric candidate exists, so the data is present —
        # the two non-numeric values are counted, never coerced, and with a
        # single candidate there is no top-1/top-2 margin to compute.
        self.assertEqual(record["status"], "present")
        self.assertEqual(record["non_numeric_top_values"], 2)
        self.assertEqual(record["positions"], 1)
        self.assertIsNone(record["margins"])

    def test_all_non_numeric_top_values_is_unavailable(self):
        choice = {"logprobs": {"content": [
            {"token": "x", "logprob": None, "top_logprobs": {"x": None, "y": "NaN"}}
        ]}}
        record = canary.extract_logprobs(choice)
        self.assertEqual(record["status"], "unavailable")
        self.assertEqual(record["non_numeric_top_values"], 2)
        self.assertIsNone(record["margins"])

    def test_single_candidate_has_no_margin_but_is_present(self):
        choice = {"logprobs": {"content": [
            {"token": "only", "logprob": -1.0, "top_logprobs": {"only": -1.0}}
        ]}}
        record = canary.extract_logprobs(choice)
        self.assertEqual(record["status"], "present")
        self.assertIsNone(record["margins"])
        self.assertEqual(record["positions"], 1)


class UnsupportedReportingTests(unittest.TestCase):
    def test_missing_logprobs_field_is_unsupported(self):
        record = canary.extract_logprobs({})
        self.assertEqual(record["status"], "unsupported")
        self.assertIn("absent", record["reason"])
        self.assertNotIn("margins", record)

    def test_null_logprobs_content_is_unsupported(self):
        record = canary.extract_logprobs({"logprobs": {"content": None}})
        self.assertEqual(record["status"], "unsupported")
        self.assertNotIn("margins", record)

    def test_content_without_top_logprobs_is_unavailable(self):
        choice = {"logprobs": {"content": [{"token": "a", "logprob": -0.1}]}}
        record = canary.extract_logprobs(choice)
        self.assertEqual(record["status"], "unavailable")
        self.assertIn("no usable top_logprobs", record["reason"])
        self.assertIsNone(record.get("margins"))

    def test_end_to_end_unsupported_record_via_fake_transport(self):
        """A backend that ignores --logprobs must produce an explicit
        unsupported row with NO margins — never a fabricated number."""
        def fake_post(url, payload, timeout):
            return {
                "choices": [{
                    "message": {"role": "assistant", "content": "42"},
                    "finish_reason": "stop",
                }],
                "usage": {"prompt_tokens": 20, "completion_tokens": 2, "total_tokens": 22},
            }, 0.05

        task = canary.LoadedTask(
            id="sanity-basic", title="t", task=_task(), grading="full"
        )
        record = canary.run_task_once(
            task, "http://127.0.0.1:1/v1", "m", 512,
            logprobs_requested=True, top_logprobs=5, timeout=10,
            http_post=fake_post,
        )
        self.assertEqual(record["outcome"], "passed")
        self.assertEqual(record["logprobs"]["status"], "unsupported")
        self.assertNotIn("margins", record["logprobs"])
        self.assertIn("absent", record["logprobs"]["reason"])

    def test_error_trials_are_explicit(self):
        from canary import RequestError

        def failing_post(url, payload, timeout):
            raise RequestError("server_disconnect", "RemoteDisconnected: end closed")

        task = canary.LoadedTask(id="x", title="t", task=_task(), grading="full")
        record = canary.run_task_once(
            task, "http://127.0.0.1:1/v1", "m", 512,
            logprobs_requested=False, top_logprobs=None, timeout=10,
            http_post=failing_post,
        )
        self.assertEqual(record["outcome"], "error")
        self.assertFalse(record["passed"])
        self.assertEqual(record["error_kind"], "server_disconnect")
        self.assertIn("RemoteDisconnected", record["error"])


class SuiteLoadingTests(unittest.TestCase):
    def test_suite_has_required_six_tasks_in_order(self):
        suite = canary.load_suite()
        ids = [t.id for t in suite]
        self.assertEqual(ids, [
            "sanity-basic",
            "hermes_ops-chaining",
            "hermes_ops-noisy-result",
            "kiem_mini-feature",
            "kiem_mini-testwrite",
            "canary-multi-turn",
        ])

    def test_failure_task_prompts_are_verbatim_repo_text(self):
        import yaml
        kiem = yaml.safe_load(
            (canary.REPO / "tasks" / "kiem_mini.yaml").read_text()
        )
        by_id = {t["id"]: t for t in kiem["tasks"]}
        suite = {t.id: t for t in canary.load_suite()}
        for task_id in canary.QWEN36_FAILURE_TASK_IDS:
            self.assertEqual(
                suite[task_id].task["user_prompt"], by_id[task_id]["prompt"]
            )
            self.assertEqual(
                suite[task_id].task["expected_tools"],
                by_id[task_id].get("expected_tools", []),
            )
            self.assertEqual(suite[task_id].grading, "canary_response_only")

    def test_hermes_ops_tasks_use_real_manifest_and_system_prompt(self):
        suite = {t.id: t for t in canary.load_suite()}
        chaining = suite["hermes_ops-chaining"].task
        self.assertGreater(len(chaining["system_prompt"]), 20000)  # real 26K prompt
        names = {t["function"]["name"] for t in chaining["tools"]}
        self.assertIn("web_search", names)
        self.assertGreater(len(names), 40)  # real 41-tool manifest
        self.assertEqual(chaining["check"]["expected_sequence"], ["web_search", "write_file"])


class AtomicWriterTests(unittest.TestCase):
    def test_commit_atomically_moves_rows_into_place(self):
        with tempfile.TemporaryDirectory() as tmp:
            final = Path(tmp) / "out.jsonl"
            writer = canary.AtomicJsonlWriter(final)
            writer.write_row({"kind": "run", "n": 1})
            writer.write_row({"kind": "trial", "n": 2})
            self.assertFalse(final.exists())
            writer.commit()
            rows = [json.loads(line) for line in final.read_text().splitlines()]
            self.assertEqual([r["n"] for r in rows], [1, 2])
            self.assertFalse(list(Path(tmp).glob("*.tmp.*")))

    def test_partial_artifact_survives_without_commit(self):
        with tempfile.TemporaryDirectory() as tmp:
            final = Path(tmp) / "out.jsonl"
            writer = canary.AtomicJsonlWriter(final)
            writer.write_row({"kind": "trial", "n": 1})
            writer.close()  # crash-equivalent: no commit
            self.assertFalse(final.exists())
            partials = list(Path(tmp).glob("*.tmp.*"))
            self.assertEqual(len(partials), 1)
            rows = [json.loads(line) for line in partials[0].read_text().splitlines()]
            self.assertEqual(rows[0]["n"], 1)


class ToolLoopTests(unittest.TestCase):
    def _scripted_transport(self, script):
        """Transport that pops canned responses per request; script is a list
        of (response_dict, elapsed) tuples."""
        calls = []

        def http_post(url, payload, timeout):
            calls.append(payload)
            response, elapsed = script[len(calls) - 1]
            return response, elapsed

        return http_post, calls

    def test_chained_tool_calls_loop_passes_with_real_grader(self):
        # Mirrors hermes_ops-chaining: web_search (mocked Amsterdam result),
        # then write_file with the exact required content+path, then a final
        # text turn. The REAL chained_tool_calls grader from tasks yaml must
        # pass — this is the semantic the single-exchange design broke.
        import yaml
        hermes = yaml.safe_load(
            (canary.REPO / "tasks" / "hermes_ops.yaml").read_text()
        )
        raw = next(t for t in hermes["tasks"] if t["id"] == "hermes_ops-chaining")
        spec = canary.resolve_prompt_spec(raw)
        task = canary.LoadedTask(
            id="hermes_ops-chaining", title="t",
            task={"id": "hermes_ops-chaining", **spec, "check": raw["check"]},
            grading="full",
        )
        transport, calls = self._scripted_transport([
            ({"choices": [{
                "message": {"role": "assistant", "content": None, "tool_calls": [
                    {"id": "c1", "type": "function", "function": {
                        "name": "web_search",
                        "arguments": '{"query": "Amsterdam population"}'}},
                ]},
                "finish_reason": "tool_calls"}],
              "usage": {"prompt_tokens": 100, "completion_tokens": 5, "total_tokens": 105}}, 0.1),
            ({"choices": [{
                "message": {"role": "assistant", "content": None, "tool_calls": [
                    {"id": "c2", "type": "function", "function": {
                        "name": "write_file",
                        "arguments": '{"path": "population.txt", "content": "912046"}'}},
                ]},
                "finish_reason": "tool_calls"}],
              "usage": {"prompt_tokens": 120, "completion_tokens": 6, "total_tokens": 126}}, 0.1),
            ({"choices": [{
                "message": {"role": "assistant", "content": "Done."},
                "finish_reason": "stop"}],
              "usage": {"prompt_tokens": 140, "completion_tokens": 2, "total_tokens": 142}}, 0.1),
        ])
        record = canary.run_task_once(
            task, "http://127.0.0.1:1/v1", "m", 512,
            logprobs_requested=False, top_logprobs=None, timeout=10,
            http_post=transport, max_turns=6,
        )
        self.assertEqual(record["outcome"], "passed")
        self.assertEqual(record["turns"], 3)
        self.assertEqual(record["usage"]["prompt_tokens"], 360)  # summed across turns
        # The mocked tool results were actually fed back into the loop.
        tool_results = [
            m["content"] for m in calls[1]["messages"] if m["role"] == "tool"
        ]
        self.assertIn("912046", tool_results[0])
        self.assertIn("Amsterdam has a population", "".join(tool_results))
        self.assertEqual(record["tool_calls_sha256"], canary.tool_calls_sha256([
            {"function": {"name": "web_search", "arguments": {"query": "Amsterdam population"}}},
            {"function": {"name": "write_file",
                          "arguments": {"path": "population.txt", "content": "912046"}}},
        ]))

    def test_loop_stops_when_model_stops_calling_tools(self):
        read_file_tool = {
            "type": "function",
            "function": {
                "name": "read_file",
                "parameters": {
                    "type": "object",
                    "properties": {"path": {"type": "string"}},
                },
            },
        }
        task = canary.LoadedTask(
            id="t", title="t",
            task={
                "id": "t",
                "system_prompt": "",
                "user_prompt": "Read notes.txt",
                "tools": [read_file_tool],
                "mock_tool_responses": {"read_file": '{"content": "hello"}'},
                "check": {"type": "contains", "text": "hello"},
            },
            grading="full",
        )
        transport, _ = self._scripted_transport([
            ({"choices": [{
                "message": {"role": "assistant", "content": None, "tool_calls": [
                    {"id": "c1", "type": "function", "function": {
                        "name": "read_file", "arguments": '{"path": "notes.txt"}'}}]},
                "finish_reason": "tool_calls"}],
              "usage": {"prompt_tokens": 10, "completion_tokens": 2, "total_tokens": 12}}, 0.05),
            ({"choices": [{
                "message": {"role": "assistant", "content": "hello there"},
                "finish_reason": "stop"}],
              "usage": {"prompt_tokens": 20, "completion_tokens": 3, "total_tokens": 23}}, 0.05),
        ])
        record = canary.run_task_once(
            task, "http://127.0.0.1:1/v1", "m", 512,
            logprobs_requested=False, top_logprobs=None, timeout=10,
            http_post=transport, max_turns=6,
        )
        self.assertEqual(record["outcome"], "passed")
        self.assertEqual(record["turns"], 2)

    def test_exceeding_max_turns_is_an_explicit_error(self):
        task = canary.LoadedTask(
            id="t", title="t",
            task={"id": "t", "system_prompt": "", "user_prompt": "Loop",
                  "tools": None,
                  "mock_tool_responses": {"read_file": '{"content": "x"}'},
                  "check": {"type": "contains", "text": "never"}},
            grading="full",
        )

        def looping_post(url, payload, timeout):
            return {"choices": [{
                "message": {"role": "assistant", "content": None, "tool_calls": [
                    {"id": "c1", "type": "function", "function": {
                        "name": "read_file", "arguments": '{"path": "x"}'}}]},
                "finish_reason": "tool_calls"}],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2}}, 0.01

        record = canary.run_task_once(
            task, "http://127.0.0.1:1/v1", "m", 512,
            logprobs_requested=False, top_logprobs=None, timeout=10,
            http_post=looping_post, max_turns=3,
        )
        self.assertEqual(record["outcome"], "error")
        self.assertEqual(record["error_kind"], "max_turns")
        self.assertIn("max_turns", record["error"])


if __name__ == "__main__":
    unittest.main()