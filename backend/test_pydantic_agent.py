import unittest

from pydantic import ValidationError
from pydantic_ai import models
from pydantic_ai.models.test import TestModel

from backend.models import ChatRequest, GroundingVerdict
from backend.pydantic_agent import GroundingFailure, ProcurementAgent


models.ALLOW_MODEL_REQUESTS = False


class ChatRequestModelTests(unittest.TestCase):
    def test_request_is_trimmed_and_history_is_bounded(self):
        request = ChatRequest.model_validate(
            {
                "message": "  How do I create a receipt?  ",
                "role": "requester",
                "history": [
                    {"role": "system", "text": "discard me"},
                    {"role": "user", "text": "  keep me  "},
                ],
            }
        )

        self.assertEqual(request.message, "How do I create a receipt?")
        self.assertEqual(
            [item.model_dump() for item in request.history],
            [{"role": "user", "text": "keep me"}],
        )

    def test_grounding_verdict_rejects_inconsistent_state(self):
        with self.assertRaises(ValidationError):
            GroundingVerdict(valid=True, reason="numeric_mismatch")


class PydanticAgentTests(unittest.TestCase):
    def setUp(self):
        self.context = "[S1] guide.pdf\nFollow the documented step."
        self.sources = [
            {"id": "S1", "path": "guide.pdf", "kind": "document", "timestamp": None}
        ]

    def test_grounded_text_passes_structured_audit(self):
        agent = ProcurementAgent(
            answer_model=TestModel(
                custom_output_text="Follow the documented step. [S1]"
            ),
            audit_model=TestModel(
                custom_output_args={"valid": True, "reason": "supported"}
            ),
        )

        result = agent.run_grounded(
            message="What should I do?",
            role="requester",
            history=[],
            context=self.context,
            sources=self.sources,
        )

        self.assertEqual(result.answer, "Follow the documented step. [S1]")
        self.assertEqual(result.grounding, "supported")
        self.assertFalse(result.repaired)

    def test_uncited_text_exhausts_one_retry_and_fails_closed(self):
        agent = ProcurementAgent(
            answer_model=TestModel(custom_output_text="Follow an unsupported step."),
            audit_model=TestModel(
                custom_output_args={"valid": True, "reason": "supported"}
            ),
        )

        with self.assertRaises(GroundingFailure) as raised:
            agent.run_grounded(
                message="What should I do?",
                role="requester",
                history=[],
                context=self.context,
                sources=self.sources,
            )

        self.assertEqual(raised.exception.reason, "missing_citation")

    def test_structured_audit_rejection_fails_closed(self):
        agent = ProcurementAgent(
            answer_model=TestModel(
                custom_output_text="Follow the documented step. [S1]"
            ),
            audit_model=TestModel(
                custom_output_args={"valid": False, "reason": "unsupported_claim"}
            ),
        )

        with self.assertRaises(GroundingFailure) as raised:
            agent.run_grounded(
                message="What should I do?",
                role="requester",
                history=[],
                context=self.context,
                sources=self.sources,
            )

        self.assertEqual(raised.exception.reason, "unsupported_claim")


if __name__ == "__main__":
    unittest.main()
