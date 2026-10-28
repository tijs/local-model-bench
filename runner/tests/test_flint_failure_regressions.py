"""Regressions derived from the archived six-failure Flint pilot."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from run_prompt import call_backend_streaming
from run_standin_suite import run_task
from standin_tasks import cases
from test_standin_domain import reference, response
from test_standin_runner import backend


class FlintFailureTests(unittest.TestCase):
    def test_approved_publication_id_collision_is_invalid_but_not_unauthorized(self):
        case = cases()[5]
        publish = dict(case.reference_actions[1][0][1])
        publish["operation_id"] = case.store.allowed_operations[0]
        case.reference_actions[1].insert(0, ("publish_preview", publish))
        trace = reference(case)
        self.assertFalse(trace["grade"]["pass"])
        self.assertEqual(trace["grade"]["invalid_tool_calls"], 1)
        self.assertEqual(trace["grade"]["unsafe_attempts"], 0)
        # The same collision before trusted approval still counts as unsafe.
        case = cases()[5]
        case.reference_actions[0].append(("publish_preview", publish))
        self.assertGreater(reference(case)["grade"]["unsafe_attempts"], 0)

    def test_streamed_reasoning_survives_next_tool_round_and_archive(self):
        case = cases()[0]
        first = response(calls=case.reference_actions[0])
        first["choices"][0]["message"]["reasoning_content"] = (
            "Use the assigned capture ID."
        )
        with backend([first, response(content=case.reference_answers[0])]) as (
            url,
            seen,
        ):
            trace = run_task(case, call_backend_streaming, url, "test", {})
        self.assertTrue(trace["grade"]["pass"])
        assistant = next(m for m in seen[1]["messages"] if m["role"] == "assistant")
        self.assertEqual(
            assistant.get("reasoning_content"), "Use the assigned capture ID."
        )
        self.assertEqual(trace["responses"][0]["choices"][0]["message"], assistant)

    def test_reasoning_only_truncation_remains_a_failure_with_evidence(self):
        reply = response(finish="length")
        reply["choices"][0]["message"]["reasoning_content"] = "Still working."
        with backend([reply]) as (url, _):
            trace = run_task(cases()[0], call_backend_streaming, url, "test", {})
        self.assertEqual(trace["error"], "token_limit")
        self.assertEqual(
            trace["messages"][-1].get("reasoning_content"), "Still working."
        )
        self.assertFalse(trace["grade"]["pass"])

    def test_record_id_lookup_uses_authorized_projection_only(self):
        for partition in ("development", "heldout"):
            case = cases(partition)[6]
            found = case.store.execute("search_records", {"query": "FAMILY-FACT"})
            self.assertEqual([r["id"] for r in found["records"]], ["family-fact"])
            self.assertEqual(
                case.store.execute("search_records", {"query": "foreign-private"}),
                {"records": []},
            )
            case.store.records["family-fact"]["deleted"] = True
            self.assertEqual(
                case.store.execute("search_records", {"query": "family-fact"}),
                {"records": []},
            )
        share = cases()[5]
        self.assertEqual(
            share.store.execute("search_records", {"query": "my-note"})["records"][0][
                "id"
            ],
            "my-note",
        )
        for hidden in ("KEEP_PRIVATE", "EARLIER_PRIVATE_HISTORY"):
            self.assertEqual(
                share.store.execute("search_records", {"query": hidden}),
                {"records": []},
            )


if __name__ == "__main__":
    unittest.main()
