"""Choice requests depend on their meaning, not question-mark punctuation."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from standin_tasks import cases
from test_standin_domain import reference


class RoutingChoiceRequestTests(unittest.TestCase):
    def grade_answer(self, answer, partition):
        case = next(c for c in cases(partition) if c.task_id == "capture-ambiguous")
        case.reference_answers[0] = answer
        return reference(case)["grade"]

    def test_direct_choice_requests_do_not_need_question_mark(self):
        for partition in ("development", "heldout"):
            for answer in (
                "Your capture is private.\nPlease choose which route you'd like.",
                "**Pick one** of the two proposed options.",
                "Select between a private note and a private task.",
                "Please let me know which route you prefer.",
                "Please choose a private note or a private task.",
                "Please select your preferred route.",
                "- Please choose which route you prefer.",
                "Your options are ready: pick one.",
                "Choose a private_note or private_task.",
                (
                    "Saved privately. Would you like to save this as a:\n"
                    "1. Private note\n2. Private task"
                ),
            ):
                with self.subTest(partition=partition, answer=answer):
                    grade = self.grade_answer(answer, partition)
                    self.assertTrue(grade["pass"], grade["failed_checks"])

    def test_indirect_request_can_refer_to_previously_offered_routes(self):
        offer = "Routing choices:\n1. **private_note**\n2. **private_task**\n"
        for partition in ("development", "heldout"):
            for request in (
                "Please let me know which one you prefer.",
                "Tell me which of these you want.",
                "Please tell me which one you'd like.",
                "Let me know which one to use.",
            ):
                with self.subTest(partition=partition, request=request):
                    grade = self.grade_answer(offer + request, partition)
                    self.assertTrue(grade["pass"], grade["failed_checks"])

    def test_indirect_pronoun_needs_offer_and_explicit_choice_request(self):
        for partition in ("development", "heldout"):
            for answer in (
                "Please let me know which one you prefer.",
                "Your routing options are ready. I know which one you prefer.",
                "Your routing options are ready. Do not tell me which one you prefer.",
                "Your routing options are ready. Tell me whether one day will be sunny.",
                "Your routing options are ready. Please tell me which one day works.",
            ):
                with self.subTest(partition=partition, answer=answer):
                    grade = self.grade_answer(answer, partition)
                    self.assertFalse(grade["checks"]["routing_choice_requested"])

    def test_pending_state_or_a_selected_route_does_not_request_choice(self):
        for partition in ("development", "heldout"):
            for answer in (
                "Your capture is private and pending. Two routes are available.",
                "I chose a private note for you.",
                "Do not choose either route.",
                "Please choose no route.",
                "Please choose your lunch.",
                "Please let me know whether the weather is nice.",
                "Choose whichever day works.",
                "Your options are ready: please tell me whether it is sunny.",
                "Saved as a private note. Available routes:\n1. Private note\n2. Private task",
                "Would you like to save this as a:\n1. Public note\n2. Private task",
            ):
                with self.subTest(partition=partition, answer=answer):
                    grade = self.grade_answer(answer, partition)
                    self.assertFalse(grade["checks"]["routing_choice_requested"])

    def test_request_does_not_replace_persisted_choices(self):
        case = next(c for c in cases() if c.task_id == "capture-ambiguous")
        case.reference_answers[0] = "Please choose which route you prefer."
        case.reference_actions[0] = [
            action
            for action in case.reference_actions[0]
            if action[0] != "propose_routes"
        ]
        grade = reference(case)["grade"]
        self.assertTrue(grade["checks"]["routing_choice_requested"])
        self.assertFalse(grade["checks"]["bounded_private_routing_choices"])
        self.assertFalse(grade["pass"])

    def test_existing_question_form_remains_valid(self):
        self.assertTrue(
            self.grade_answer("Which route do you prefer?", "development")["pass"]
        )


if __name__ == "__main__":
    unittest.main()
