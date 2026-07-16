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


INVOICE_REQUIREMENTS_QUERY = (
    "CSUB invoice requirements itemized match Purchase Order PO Direct Pay DP "
    "supplier upload Accounts Payable"
)
SUPPLIER_INVITATION_QUERY = (
    "Supplier Did Not Receive Invitation CSUBUY invited email Re-Invite Request"
)
AMAZON_ACCESS_QUERY = (
    "Amazon Accounts and Access CSUBUY Amazon Business account email punchout"
)
VOUCHER_PAY_STATUS_QUERY = (
    "Voucher Pay Status CSUBUY Orders Search Vouchers Payment Information"
)
SUPPLIER_RETURNED_QUERY = (
    "Supplier Registration Returned correction reason SM Team noreply jaggaer resources"
)
PO_CHANGE_REQUEST_QUERY = (
    "Purchase Order Change Request current PO status vouchers payments receipts History Summary sent to CFS completed"
)


def _contains_any(text: str, terms: tuple[str, ...]) -> bool:
    return any(term in text for term in terms)


def _recent_user_history(history: list[dict[str, str]]) -> str:
    return " ".join(
        str(item.get("text", "")).casefold()
        for item in history[-4:]
        if item.get("role") == "user"
    )


def deterministic_retrieval_decision(
    message: str,
    history: list[dict[str, str]],
) -> RetrievalDecision | None:
    """Resolve narrow, high-confidence workflows before asking the model router.

    These matches only choose a public retrieval query. Policy gates still run
    first, and answer text remains source-verified after retrieval.
    """
    lowered = " ".join(message.casefold().split())

    if "invoice" in lowered and _contains_any(
        lowered,
        (
            "what information",
            "what should i include",
            "what should be on",
            "what is required",
            "requirements",
            "required on",
            "include with",
            "include on",
        ),
    ):
        return RetrievalDecision(
            route="retrieve",
            reply="",
            search_query=INVOICE_REQUIREMENTS_QUERY,
            reason="deterministic_invoice_requirements",
        )

    invitation_problem = _contains_any(
        lowered,
        (
            "did not receive",
            "didn't receive",
            "does not receive",
            "doesn't receive",
            "never received",
            "not received",
            "did not get",
            "didn't get",
            "never got",
            "missing invitation",
            "resend invitation",
            "re-invite",
            "reinvite",
        ),
    )
    if (
        _contains_any(lowered, ("supplier", "vendor"))
        and _contains_any(lowered, ("invitation", "invite"))
        and invitation_problem
    ):
        return RetrievalDecision(
            route="retrieve",
            reply="",
            search_query=SUPPLIER_INVITATION_QUERY,
            reason="deterministic_supplier_invitation",
        )

    if "amazon" in lowered and _contains_any(
        lowered,
        ("access", "account", "punchout", "sign in", "login", "start shopping"),
    ):
        return RetrievalDecision(
            route="retrieve",
            reply="",
            search_query=AMAZON_ACCESS_QUERY,
            reason="deterministic_amazon_access",
        )

    if (
        _contains_any(lowered, ("supplier", "vendor"))
        and "registration" in lowered
        and _contains_any(lowered, ("returned", "return", "correction"))
    ):
        return RetrievalDecision(
            route="retrieve",
            reply="",
            search_query=SUPPLIER_RETURNED_QUERY,
            reason="deterministic_supplier_registration_returned",
        )

    if "change request" in lowered and _contains_any(
        lowered, ("purchase order", " po ", "cfs", "history", "status")
    ):
        return RetrievalDecision(
            route="retrieve",
            reply="",
            search_query=PO_CHANGE_REQUEST_QUERY,
            reason="deterministic_po_change_request",
        )

    voucher_status_in_message = "voucher" in lowered and _contains_any(
        lowered, ("pay status", "payment status", "status")
    )
    follow_up_reference = _contains_any(
        lowered,
        (
            "check that",
            "find that",
            "see that",
            "review that",
            "check it",
            "find it",
            "see it",
            "where is that",
            "where do i",
            "how do i check",
        ),
    )
    prior_user_text = _recent_user_history(history)
    voucher_status_in_history = "voucher" in prior_user_text and _contains_any(
        prior_user_text, ("pay status", "payment status", "status")
    )
    if voucher_status_in_message or (
        follow_up_reference and voucher_status_in_history
    ):
        return RetrievalDecision(
            route="retrieve",
            reply="",
            search_query=VOUCHER_PAY_STATUS_QUERY,
            reason=(
                "deterministic_voucher_status"
                if voucher_status_in_message
                else "deterministic_voucher_followup"
            ),
        )

    return None


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
    if any(
        re.search(pattern, normalized, re.IGNORECASE) for pattern in unsafe_patterns
    ):
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
