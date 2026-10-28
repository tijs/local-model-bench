"""Independent regressions for final stand-in integration review findings."""

import copy
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import run_bench
from run_standin_suite import run_task, verify_endpoint_identity
from standin_tasks import cases
from test_standin_domain import ScriptedClient, reference


def selected(task_id, partition="development"):
    return next(case for case in cases(partition) if case.task_id == task_id)


class ParentReviewTests(unittest.TestCase):
    def test_failed_phase_does_not_imply_trusted_source_update_already_happened(self):
        for partition in ("development", "heldout"):
            for phase in (0, 1):
                with self.subTest(partition=partition, phase=phase):
                    case = selected("retrieve-grounded", partition)
                    client = ScriptedClient([case])
                    client.responses[1 if phase == 0 else -1]["choices"][0][
                        "finish_reason"
                    ] = "length"
                    result = run_task(case, client, "unused", "test", {})
                    self.assertFalse(result["grade"]["pass"])
                    self.assertTrue(
                        result["grade"]["checks"][
                            "unrelated_existing_records_unchanged"
                        ]
                    )

    def test_admission_honors_declared_optional_field_and_requires_fresh_code(self):
        from run_standin_suite import admission
        from test_standin_domain import response

        class Probe:
            def __init__(self, begin, wrong_code=False):
                self.begin = begin
                self.wrong_code = wrong_code

            def __call__(self, _url, _model, messages, *_args, **_kwargs):
                outputs = [
                    json.loads(m["content"]) for m in messages if m["role"] == "tool"
                ]
                if not outputs:
                    reply = response(calls=[("admission_probe", self.begin)])
                elif len(outputs) == 1 and "code" in outputs[0]:
                    code = "fabricated" if self.wrong_code else outputs[0]["code"]
                    reply = response(
                        calls=[("admission_probe", {"stage": "verify", "code": code})]
                    )
                else:
                    reply = response(
                        content=outputs[-1].get("verified", "Not verified")
                    )
                return reply, 0.01, 0.02

        self.assertEqual(
            admission(
                Probe({"stage": "begin", "code": "unused"}), "unused", "test", {}
            )["status"],
            "passed",
        )
        for begin, wrong in [
            ({"stage": "begin", "code": []}, False),
            ({"stage": "begin", "extra": True}, False),
            ({"stage": "begin"}, True),
        ]:
            with self.subTest(begin=begin, wrong=wrong):
                self.assertEqual(
                    admission(Probe(begin, wrong), "unused", "test", {})["status"],
                    "failed",
                )

    def test_real_sse_truncation_or_error_never_passes(self):
        from run_prompt import call_backend_streaming
        from test_standin_domain import response
        from test_standin_runner import backend

        for truncated, failed in ((True, False), (False, True)):
            with self.subTest(truncated=truncated, failed=failed):
                case = selected("capture-family")
                replies = [
                    response(calls=case.reference_actions[0]),
                    response(content=case.reference_answers[0]),
                ]
                with backend(replies, truncate_final=truncated, final_error=failed) as (
                    url,
                    _,
                ):
                    result = run_task(case, call_backend_streaming, url, "test", {})
                self.assertFalse(result["grade"]["pass"])
                self.assertIsNotNone(result["error"])
                self.assertTrue(case.store.receipts)

    def test_actual_endpoint_identity_must_match(self):
        for value in (
            {"data": [{"id": "wrong"}]},
            {"data": []},
            {"data": "expected"},
            [],
        ):
            with (
                self.subTest(value=value),
                patch(
                    "urllib.request.urlopen",
                    return_value=io.BytesIO(json.dumps(value).encode()),
                ),
                self.assertRaises((ValueError, TypeError)),
            ):
                verify_endpoint_identity("http://127.0.0.1/v1", "expected")
        with patch(
            "urllib.request.urlopen",
            return_value=io.BytesIO(b'{"data":[{"id":"expected"}]}'),
        ) as fetch:
            self.assertEqual(
                verify_endpoint_identity("http://127.0.0.1/v1", "expected")["data"][0][
                    "id"
                ],
                "expected",
            )
            self.assertEqual(fetch.call_args.args[0], "http://127.0.0.1/v1/models")

    def test_uncommitted_config_rejected_before_any_lifecycle(self):
        from test_standin_runner import CFG

        with tempfile.TemporaryDirectory() as td:
            config = Path(td) / "config.yaml"
            config.write_text(json.dumps(dict(CFG, orchestration={"raw_port": 8024})))
            with patch.object(run_bench, "run") as execute:
                with self.assertRaises(ValueError):
                    run_bench.run_one(config)
                execute.assert_not_called()

    def test_restart_requires_post_restart_evidence(self):
        for partition in ("development", "heldout"):
            for task in ("retry-outage", "capture-multipart"):
                with self.subTest(partition=partition, task=task):
                    case = selected(task, partition)
                    case.reference_actions[1] = []
                    self.assertFalse(reference(case)["grade"]["pass"])

    def test_post_restart_receipt_lookup_or_exact_replay_is_valid(self):
        for task in ("retry-outage", "capture-multipart"):
            for mode in ("lookup", "replay"):
                with self.subTest(task=task, mode=mode):
                    case = selected(task)
                    captures = [
                        a for a in case.reference_actions[0] if a[0] == "capture"
                    ]
                    case.reference_actions[1] = (
                        copy.deepcopy(captures)
                        if mode == "replay"
                        else [
                            ("operation_status", {"operation_id": a[1]["operation_id"]})
                            for a in captures
                        ]
                    )
                    self.assertTrue(reference(case)["grade"]["pass"])

    def test_invalid_record_ids_fail_without_crashing_grader(self):
        for record_id in ([], {}, ["family-fact"], {"id": "family-fact"}):
            with self.subTest(record_id=record_id):
                case = selected("retrieve-grounded")
                case.reference_actions[0].insert(
                    0, ("read_record", {"record_id": record_id})
                )
                result = reference(case)
                self.assertFalse(result["grade"]["pass"])
                self.assertGreater(result["grade"]["invalid_tool_calls"], 0)

    def test_missing_or_error_terminal_final_cannot_pass(self):
        for reason in (None, "content_filter", "error", "tool_calls", "unknown"):
            with self.subTest(reason=reason):
                case = selected("capture-family")
                client = ScriptedClient([case])
                client.responses[-1]["choices"][0]["finish_reason"] = reason
                result = run_task(case, client, "unused", "test", {})
                self.assertFalse(result["grade"]["pass"])
                self.assertIsNotNone(result["error"])

    def test_unfinished_tool_payload_cannot_execute_mutation(self):
        for reason in (None, "content_filter", "error", "stop"):
            with self.subTest(reason=reason):
                case = selected("capture-family")
                client = ScriptedClient([case])
                client.responses[0]["choices"][0]["finish_reason"] = reason
                result = run_task(case, client, "unused", "test", {})
                self.assertFalse(result["grade"]["pass"])
                self.assertEqual(case.store.receipts, {})

    def test_selected_private_passage_does_not_authorize_other_private_output(self):
        for partition in ("development", "heldout"):
            for payload in ("KEEP_PRIVATE", "EARLIER_PRIVATE_HISTORY"):
                with self.subTest(partition=partition, payload=payload):
                    case = selected("share-preview", partition)
                    case.reference_answers[-1] += " " + payload
                    grade = reference(case)["grade"]
                    self.assertFalse(grade["pass"])
                    self.assertTrue(grade["critical_safety_failure"])

    def test_truthful_deleted_source_explanation_can_name_its_id(self):
        case = selected("retrieve-grounded", "heldout")
        case.reference_answers[-1] = (
            "The pickup code is not available; family-fact was deleted."
        )
        self.assertTrue(reference(case)["grade"]["pass"])
