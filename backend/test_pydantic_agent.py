import unittest

from pydantic import ValidationError
from pydantic_ai import models
from pydantic_ai.models.function import FunctionModel
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

    def agent(
        self,
        *,
        answer_model=None,
        audit_model=None,
        router_model=None,
    ) -> ProcurementAgent:
        return ProcurementAgent(
            answer_model=answer_model
            or TestModel(custom_output_text="Follow the documented step. [S1]"),
            audit_model=audit_model
            or TestModel(custom_output_args={"valid": True, "reason": "supported"}),
            router_model=router_model
            or TestModel(
                custom_output_args={
                    "route": "retrieve",
                    "reply": "",
                    "search_query": "procurement guidance",
                    "reason": "test",
                }
            ),
        )

    def test_grounded_text_passes_structured_audit(self):
        agent = self.agent(
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
        agent = self.agent(
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
        agent = self.agent(
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

    def test_structured_router_returns_conversation_without_search(self):
        agent = self.agent(
            router_model=TestModel(
                custom_output_args={
                    "route": "conversation",
                    "reply": "Hi! What procurement task can I help with?",
                    "search_query": "should be removed",
                    "reason": "greeting",
                }
            )
        )

        decision = agent.decide_retrieval(
            message="hi",
            role="requester",
            history=[],
        )

        self.assertEqual(decision.route, "conversation")
        self.assertEqual(decision.search_query, "")
        self.assertIn("Hi!", decision.reply)

    def test_structured_router_preserves_rewritten_retrieval_query(self):
        agent = self.agent(
            router_model=TestModel(
                custom_output_args={
                    "route": "retrieve",
                    "reply": "should be removed",
                    "search_query": "create a CSUBUY requisition",
                    "reason": "procedural_question",
                }
            )
        )

        decision = agent.decide_retrieval(
            message="Hi, how do I create a requisition?",
            role="requester",
            history=[],
        )

        self.assertEqual(decision.route, "retrieve")
        self.assertEqual(decision.reply, "")
        self.assertEqual(decision.search_query, "create a CSUBUY requisition")

    def test_unsafe_non_retrieval_reply_is_replaced(self):
        agent = self.agent(
            router_model=TestModel(
                custom_output_args={
                    "route": "conversation",
                    "reply": "Click the form and submit it within 30 days [S1].",
                    "search_query": "",
                    "reason": "bad_reply",
                }
            )
        )

        decision = agent.decide_retrieval(
            message="hello",
            role="requester",
            history=[],
        )

        self.assertNotIn("[S1]", decision.reply)
        self.assertIn("What are you trying to accomplish?", decision.reply)

    def test_invalid_router_output_fails_safely_to_retrieval(self):
        agent = self.agent(
            router_model=TestModel(
                custom_output_args={
                    "route": "not_a_route",
                    "reply": "",
                    "search_query": "",
                    "reason": "invalid",
                }
            )
        )

        decision = agent.decide_retrieval(
            message="Where is the invoice guide?",
            role="requester",
            history=[],
        )

        self.assertEqual(decision.route, "retrieve")
        self.assertEqual(decision.search_query, "Where is the invoice guide?")
        self.assertEqual(decision.reason, "safe_fallback")

    def test_router_exception_fails_safely_to_retrieval(self):
        def fail_router(*_args, **_kwargs):
            raise RuntimeError("router unavailable")

        agent = self.agent(router_model=FunctionModel(fail_router))

        decision = agent.decide_retrieval(
            message="How do I create a receipt?",
            role="requester",
            history=[],
        )

        self.assertEqual(decision.route, "retrieve")
        self.assertEqual(decision.search_query, "How do I create a receipt?")


if __name__ == "__main__":
    unittest.main()
