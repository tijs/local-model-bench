"""Automation quality checks exercise real CLI execution and independent variants."""

import json
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import run_standin_suite as household
from automation_references import REFERENCES
from automation_tasks import tasks
from run_automation_suite import (
    BUDGETS,
    Workspace,
    execute_source,
    grader_module,
    run_task,
    strict_json,
)
from run_prompt import StreamStall
from run_standin_suite import EpisodeFailure, conversation, empty_trace, write_json
from standin_tasks import cases


def response(name=None, args=None):
    message = {
        "role": "assistant",
        "content": "Script tested." if name is None else None,
    }
    if name:
        message["tool_calls"] = [
            {
                "id": "call-" + name,
                "type": "function",
                "function": {"name": name, "arguments": json.dumps(args)},
            }
        ]
    return {
        "choices": [
            {
                "message": message,
                "finish_reason": "stop" if name is None else "tool_calls",
            }
        ],
        "usage": {"prompt_tokens": 10, "completion_tokens": 10},
    }


class ScriptClient:
    def __init__(self, source, repair=False):
        self.source = source
        self.repair = repair
        self.count = 0
        self.observed_error = False

    def __call__(self, _url, _model, messages, _tools, **kwargs):
        assert kwargs["max_tokens"] == BUDGETS["max_tokens"]
        self.count += 1
        actions = [
            (
                "write_script",
                {
                    "source": 'raise ValueError("repair me")\n'
                    if self.repair
                    else self.source
                },
            ),
            ("run_script", {}),
        ]
        if self.repair:
            actions += [("write_script", {"source": self.source}), ("run_script", {})]
            if self.count == 3:
                last = json.loads(messages[-1]["content"])
                self.observed_error = (
                    last["returncode"] != 0 and "repair me" in last["stderr"]
                )
        action = actions[self.count - 1] if self.count <= len(actions) else (None, None)
        return response(*action), 0.01, 0.02


class AutomationTaskTests(unittest.TestCase):
    def test_request_consuming_final_task_budget_is_not_runtime_timeout_in_either_track(
        self,
    ):
        observed = []

        def client(*args, **kwargs):
            observed.append(kwargs)
            time.sleep(0.03)
            raise StreamStall("turn_total", 0.03, 0.01)

        with patch.dict(BUDGETS, task_seconds=0.01):
            result = run_task(tasks()[0], "development", client, "unused", "test", {})
        self.assertEqual(result["failure_class"], "task_budget")
        with patch.dict(household.BUDGETS, task_seconds=0.01):
            result = household.run_task(
                cases("development")[0], client, "unused", "test", {}
            )
        self.assertEqual(result["failure_class"], "task_budget")
        self.assertTrue(
            all(
                item["max_tokens"] == 4096 and item["timeout"] <= 0.01
                for item in observed
            )
        )
        self.assertEqual(BUDGETS["turn_seconds"], 180)
        self.assertEqual(household.BUDGETS["turn_seconds"], 180)

    def test_overall_task_deadline_is_distinct_from_turn_or_liveness_stall(self):
        for phase, clock, budget in [
            ("turn_total", 101.0, True),
            ("turn_total", 100.1, False),
            ("stream_idle", 101.0, False),
        ]:

            def client(*args, selected=phase, **kwargs):
                raise StreamStall(selected, 1, 1)

            expected = EpisodeFailure if budget else StreamStall
            with (
                self.subTest(phase=phase, clock=clock),
                patch("run_standin_suite.time.monotonic", side_effect=[100.0, clock]),
                self.assertRaises(expected) as caught,
            ):
                conversation(
                    [],
                    [],
                    lambda *a: {},
                    client,
                    "unused",
                    "test",
                    {},
                    100.5,
                    empty_trace(),
                )
            if budget:
                self.assertEqual(str(caught.exception), "task_timeout")

    def test_oracles_have_independently_asserted_edge_outputs(self):
        g = grader_module()
        self.assertEqual(
            g.expected("shopping-csv", g.variants("shopping-csv", "development")[2]),
            [
                {"item": "café beans", "quantity": 3},
                {"item": "salt, fine", "quantity": 0},
            ],
        )
        self.assertEqual(
            g.expected(
                "expense-summary", g.variants("expense-summary", "development")[2]
            ),
            {
                "categories": [
                    {"category": "café, outing", "total": "2.68"},
                    {"category": "food", "total": "0.00"},
                    {"category": "uncategorized", "total": "1.01"},
                ],
                "total": "3.69",
            },
        )
        self.assertEqual(
            [
                x["id"]
                for x in g.expected(
                    "reminder-repair", g.variants("reminder-repair", "development")[2]
                )
            ],
            ["a", "z"],
        )
        for tid in REFERENCES:
            self.assertNotEqual(
                g.variants(tid, "development")[0], g.variants(tid, "heldout")[0]
            )

    def test_reference_scripts_pass_all_variants_and_both_partitions(self):
        for task in tasks():
            for partition in ("development", "heldout"):
                with self.subTest(task=task.task_id, partition=partition):
                    result = run_task(
                        task,
                        partition,
                        ScriptClient(REFERENCES[task.task_id]),
                        "unused",
                        "test",
                        {},
                    )
                    self.assertTrue(result["grade"]["pass"], result)
                    self.assertEqual(len(result["validation"]), 4)

    def test_real_execution_error_can_be_repaired_without_failing_task(self):
        client = ScriptClient(REFERENCES["shopping-csv"], repair=True)
        result = run_task(tasks()[0], "development", client, "unused", "test", {})
        self.assertTrue(client.observed_error)
        self.assertTrue(result["grade"]["pass"], result)

    def test_wrong_scripts_fail_each_contract_in_both_partitions(self):
        wrong = {
            "shopping-csv": REFERENCES["shopping-csv"].replace(
                "items.get(name,0)+int", "0+int"
            ),
            "expense-summary": REFERENCES["expense-summary"].replace(
                "ROUND_HALF_UP)", '"ROUND_HALF_EVEN")'
            ),
            "reminder-repair": tasks()[2].starter,
        }
        for task in tasks():
            for partition in ("development", "heldout"):
                with self.subTest(task=task.task_id, partition=partition):
                    result = run_task(
                        task,
                        partition,
                        ScriptClient(wrong[task.task_id]),
                        "unused",
                        "test",
                        {},
                    )
                    self.assertFalse(result["grade"]["pass"])

    def test_hardcoded_visible_answer_fails_unseen_variants(self):
        g = grader_module()
        data = g.variants("shopping-csv", "development")[0]
        source = "print(" + repr(json.dumps(g.expected("shopping-csv", data))) + ")\n"
        result = run_task(
            tasks()[0], "development", ScriptClient(source), "unused", "test", {}
        )
        self.assertTrue(result["grade"]["checks"]["visible_output_correct"])
        self.assertFalse(result["grade"]["checks"]["unseen_outputs_correct"])
        self.assertFalse(result["grade"]["pass"])

    def test_no_action_and_unexecuted_final_submission_fail(self):
        result = run_task(
            tasks()[0],
            "development",
            lambda *a, **k: (response(), None, None),
            "unused",
            "test",
            {},
        )
        self.assertFalse(result["grade"]["pass"])
        self.assertFalse(result["grade"]["checks"]["submitted_script"])

        class NoRun(ScriptClient):
            def __call__(self, *args, **kwargs):
                if self.count:
                    return response(), None, None
                return super().__call__(*args, **kwargs)

        result = run_task(
            tasks()[0],
            "development",
            NoRun(REFERENCES["shopping-csv"]),
            "unused",
            "test",
            {},
        )
        self.assertTrue(result["grade"]["checks"]["visible_output_correct"])
        self.assertFalse(
            result["grade"]["checks"]["final_script_executed_successfully"]
        )

    def test_only_named_synthetic_files_and_source_write_are_exposed(self):
        w = Workspace(tasks()[0], "item,quantity\n")
        for name in ("../checks/python_automation.py", "/etc/passwd", "input.json"):
            self.assertIn("error", w.execute("read_file", {"name": name}))
        self.assertIn("error", w.execute("write_script", {"source": "x" * 32769}))
        self.assertEqual(w.data, "item,quantity\n")
        self.assertIsNone(w.source)

    def test_malformed_unicode_is_an_invalid_call_and_evidence_survives(self):
        w = Workspace(tasks()[0], "item,quantity\n")
        result = w.execute("write_script", {"source": "\ud800"})
        self.assertIn("UTF-8", result["error"])
        self.assertEqual(w.invalid_calls, 1)
        self.assertIsNone(w.source)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "evidence.json"
            write_json(path, {"journal": w.journal})
            self.assertEqual(
                json.loads(path.read_text())["journal"][0]["arguments"]["source"],
                "\ud800",
            )

    def test_strict_json_rejects_nonfinite_duplicate_and_surrounding_text(self):
        for text in (
            "NaN",
            "1e309",
            "-1e309",
            '{"x":1,"x":2}',
            "Here: []",
            "[] trailing",
        ):
            with self.subTest(text=text), self.assertRaises(ValueError):
                strict_json(text)

    def test_deep_model_json_is_incorrect_output_not_harness_error(self):
        source = 'print("["*10000+"0"+"]"*10000)\n'
        result = run_task(
            tasks()[0], "development", ScriptClient(source), "unused", "test", {}
        )
        self.assertEqual(result["failure_class"], "task_failure")
        self.assertEqual(len(result["validation"]), 4)
        self.assertTrue(all(v["parse_error"] for v in result["validation"]))

    def test_deep_tool_arguments_are_a_protocol_failure(self):
        def client(*args, **kwargs):
            r = response("write_script", {})
            r["choices"][0]["message"]["tool_calls"][0]["function"]["arguments"] = (
                "[" * 1100 + "0" + "]" * 1100
            )
            return r, None, None

        result = run_task(tasks()[0], "development", client, "unused", "test", {})
        self.assertEqual(result["failure_class"], "protocol_error")
        self.assertEqual(result["error"], "malformed_tool_arguments")

    def test_grading_interrupt_preserves_source_messages_and_completed_variants(self):
        for interrupt_call in (2, 4):
            with self.subTest(interrupt_call=interrupt_call):
                calls = 0

                def execute(*args, stop=interrupt_call, **kwargs):
                    nonlocal calls
                    calls += 1
                    if calls == stop:
                        raise KeyboardInterrupt
                    return execute_source(*args, **kwargs)

                with patch("run_automation_suite.execute_source", side_effect=execute):
                    result = run_task(
                        tasks()[0],
                        "development",
                        ScriptClient(REFERENCES["shopping-csv"]),
                        "unused",
                        "test",
                        {},
                    )
                self.assertEqual(result["failure_class"], "interrupted")
                self.assertEqual(result["script"], REFERENCES["shopping-csv"])
                self.assertEqual(len(result["responses"]), 3)
                self.assertEqual(len(result["validation"]), interrupt_call - 2)

    def test_token_limit_is_not_a_quality_pass(self):
        def client(*a, **k):
            r = response()
            r["choices"][0]["finish_reason"] = "length"
            return r, None, None

        result = run_task(tasks()[0], "development", client, "unused", "test", {})
        self.assertEqual(result["failure_class"], "truncation")
        self.assertFalse(result["grade"]["pass"])


if __name__ == "__main__":
    unittest.main()
