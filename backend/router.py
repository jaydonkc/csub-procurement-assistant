"""Deterministic safety checks around the model-based retrieval router."""

from __future__ import annotations

import re

from backend.models import RetrievalDecision


ROUTER_FALLBACK_RESPONSES = {
    "conversation": (
        "Hi! I can help you navigate CSUB purchasing, suppliers, requisitions, invoices, and related procurement guidance. "
        "What are you trying to accomplish?"
    ),
    "clarification": (
        "What procurement task are you trying to complete? For example, are you buying something, working with a supplier, "
        "handling an invoice, or looking for requisition guidance?"
    ),
    "out_of_scope": (
        "I’m focused on CSUB purchasing and procurement guidance. What procurement-related task can I help you with?"
    ),
}


def retrieval_fallback(message: str) -> RetrievalDecision:
    return RetrievalDecision(
        route="retrieve",
        reply="",
        search_query=message,
        reason="safe_fallback",
    )


def safe_router_reply(route: str, reply: str) -> str:
    fallback = ROUTER_FALLBACK_RESPONSES[route]
    normalized = " ".join(reply.split()).strip()
    if not normalized or len(normalized) > 800 or len(normalized.split()) > 100:
        return fallback
    unsafe_patterns = (
        r"\[S\d+\]",
        r"https?://",
        r"\$\s*\d",
        r"\b\d+(?:\.\d+)?%?\b",
        r"\b(?:click|navigate|select|submit|approve|required|must|deadline|within \d+)\b",
        r"\b(?:track|look up|access|change)\s+(?:your\s+)?(?:purchase|requisition|invoice|voucher|payment|supplier|record)s?\b",
    )
    if any(re.search(pattern, normalized, re.IGNORECASE) for pattern in unsafe_patterns):
        return fallback
    return normalized


def normalize_router_decision(
    decision: RetrievalDecision,
    message: str,
) -> RetrievalDecision:
    reason = decision.reason or "model_decision"
    if decision.route == "retrieve":
        return RetrievalDecision(
            route="retrieve",
            reply="",
            search_query=decision.search_query or message,
            reason=reason,
        )
    return RetrievalDecision(
        route=decision.route,
        reply=safe_router_reply(decision.route, decision.reply),
        search_query="",
        reason=reason,
    )
