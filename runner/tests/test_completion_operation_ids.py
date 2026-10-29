"""Valid optional actions must not consume IDs forced by future fixture phases."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from run_standin_suite import run_task
from standin_tasks import cases, event_before
from test_standin_domain import ScriptedClient, reference


def completion(partition):
    return next(c for c in cases(partition) if c.task_id == "completion-intent")


class CompletionOperationIDTests(unittest.TestCase):
    def test_optional_later_write_does_not_poison_future_done(self):
        for partition in ("development", "heldout"):
            with self.subTest(partition=partition):
                case = completion(partition)
                case.reference_actions[0] = [
                    (
                        "set_progress",
                        {
                            "record_id": "bag",
                            "action": "later",
                            "operation_id": case.store.allowed_operations[0],
                        },
                    )
                ]
                result = reference(case)
                self.assertTrue(
                    result["grade"]["pass"], result["grade"]["failed_checks"]
                )

    def test_optional_later_and_help_remain_valid_across_restart(self):
        for partition in ("development", "heldout"):
            with self.subTest(partition=partition):
                case = completion(partition)
                case.reference_actions[0] = [
                    (
                        "set_progress",
                        {
                            "record_id": "bag",
                            "action": action,
                            "operation_id": operation,
                        },
                    )
                    for action, operation in zip(
                        ("later", "help"),
                        case.store.allowed_operations[:2],
                        strict=True,
                    )
                ]
                result = reference(case)
                self.assertTrue(
                    result["grade"]["pass"], result["grade"]["failed_checks"]
                )
                self.assertEqual(
                    result["phases"][0]["records"]["bag"],
                    result["initial"]["records"]["bag"],
                )

    def test_future_completion_id_is_granted_only_with_its_user_phase(self):
        case = completion("development")
        done_id = case.reference_actions[1][0][1]["operation_id"]
        self.assertNotIn(done_id, case.store.allowed_operations)
        self.assertNotIn(done_id, case.context())
        self.assertIn(
            "error",
            case.store.execute(
                "set_progress",
                {"record_id": "bag", "action": "done", "operation_id": done_id},
            ),
        )
        event_before(case, 1)
        self.assertIn(done_id, case.store.allowed_operations)
        result = case.store.execute(
            "set_progress",
            {"record_id": "bag", "action": "done", "operation_id": done_id},
        )
        self.assertNotIn("error", result)
        reopen_id = case.reference_actions[2][0][1]["operation_id"]
        self.assertNotIn(reopen_id, case.store.allowed_operations)
        self.assertIn(
            "error",
            case.store.execute(
                "set_progress",
                {"record_id": "bag", "action": "reopen", "operation_id": reopen_id},
            ),
        )
        event_before(case, 2)
        self.assertNotIn(
            "error",
            case.store.execute(
                "set_progress",
                {"record_id": "bag", "action": "reopen", "operation_id": reopen_id},
            ),
        )
        self.assertTrue(
            all(step["done"] for step in case.store.records["bag"]["steps"])
        )

    def test_late_truncation_does_not_relabel_completed_earlier_phases(self):
        case = completion("development")
        client = ScriptedClient([case])
        client.responses[-1]["choices"][0]["finish_reason"] = "length"
        result = run_task(case, client, "unused", "test", {})
        self.assertEqual(result["error"], "token_limit")
        self.assertFalse(result["grade"]["pass"])
        self.assertTrue(result["grade"]["checks"]["later_did_not_complete"])
        self.assertTrue(result["grade"]["checks"]["explicit_done_completes_parent"])


if __name__ == "__main__":
    unittest.main()
