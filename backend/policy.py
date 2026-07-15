"""Deterministic public-access and capability policy gates."""

from __future__ import annotations

import re


ROLE_LABELS = {
    "requester": "faculty or staff requester",
    "vendor": "vendor or supplier",
    "internal_staff": "internal support staff (self-reported public context only)",
}

SENSITIVE_ACCESS_TERMS = (
    "sensitive data",
    "sensitive-pii",
    "pii access",
    "personally identifiable",
    "social security",
    "ssn",
    "taxpayer identification",
    "bank account",
    "routing number",
)

SENSITIVE_ACCESS_PATTERNS = (
    r"\bpii\b",
    r"\bbank[- ]account\b",
    r"\brouting[- ]number\b",
    r"\bsocial[- ]security\b",
)

OUT_OF_SCOPE_PATTERNS = (
    r"\btuition\b",
    r"\badmissions?\b",
    r"\bfinancial aid\b",
    r"\bclass registration\b",
    r"\bcourse schedule\b",
    r"\bgrades?\b",
    r"\bcanvas\b",
    r"\bcampus housing\b",
    r"\bparking permit\b",
)

PROCUREMENT_TERMS = (
    "procurement",
    "purchase",
    "buy",
    "supplier",
    "vendor",
    "requisition",
    "invoice",
    "voucher",
    "payment",
    "csubuy",
    "p2p",
    "contract",
    "purchase order",
)

PROMPT_ATTACK_PATTERNS = (
    r"\bignore (?:all |any )?(?:previous|prior|system) instructions?\b",
    r"\b(?:reveal|show|print|repeat|leak) (?:the )?(?:system prompt|hidden prompt|internal documents?|restricted documents?)\b",
    r"\b(?:bypass|disable|override) (?:the )?(?:guardrails?|filters?|access controls?)\b",
    r"\bpretend (?:that )?(?:you|i) (?:am|are) (?:authorized|an? admin)",
)

INTERNAL_PROCEDURE_PATTERNS = (
    r"\bapprove (?:a |the )?(?:requisition|purchase order|po|invoice|voucher|cart)\b",
    r"\bapproval queue\b",
    r"\bcampus admin(?:istrator)?s?\b",
    r"\badmin(?:istrator)? (?:settings?|console|workflow|instructions?|training)\b",
    r"\b(?:configure|assign|grant|change) (?:a )?(?:security|admin|approval|pii) (?:role|access|permission)\b",
    r"\bdraft cart (?:for|on behalf of)\b",
    r"\binternal[- ]only\b",
)

ACTION_PATTERN = re.compile(
    r"\b(?:approve|submit|create|edit|modify|change|cancel|delete|withdraw|reject|finalize|place|send|process)\b"
    r".{0,70}\b(?:requisition|purchase order|po|invoice|voucher|supplier|vendor|cart|order|transaction)\b",
    re.IGNORECASE,
)

GENERAL_HOWTO_PATTERN = re.compile(
    r"^(?:please\s+)?(?:how|where|when|why|what)\b|\b(?:steps|instructions?|walk me through|guidance)\b",
    re.IGNORECASE,
)

LEADING_PLEASANTRY_PATTERN = re.compile(
    r"^\s*(?:(?:hi|hello|hey|thanks|thank you|good (?:morning|afternoon|evening))\b[\s,!?.:;-]*)+",
    re.IGNORECASE,
)

LIVE_OBJECT_PATTERN = re.compile(
    r"\b(?:requisition|purchase order|po|invoice|voucher|supplier|vendor|payment|transaction)\b",
    re.IGNORECASE,
)

LIVE_LOOKUP_PATTERN = re.compile(
    r"\b(?:status|look up|lookup|check|track|has .* been paid|when .* paid)\b",
    re.IGNORECASE,
)

FIXED_RESPONSES = {
    "sensitive_access": (
        "This public/no-auth assistant cannot provide instructions for accessing or handling sensitive supplier data or PII. "
        "Choosing an internal-staff role does not grant authorization. Use the approved internal CSUBUY support channel or contact Supplier Management for role-appropriate assistance."
    ),
    "prompt_attack": (
        "I can only provide public, source-grounded CSUB procurement guidance. I cannot reveal hidden instructions, internal documents, or bypass access controls."
    ),
    "out_of_scope": (
        "I can only help with public CSUB purchasing and procurement guidance. I do not have an approved procurement source for that topic, so I will not guess. "
        "Please use the appropriate CSUB office or campus service for current information."
    ),
    "internal_procedure": (
        "This public/no-auth assistant cannot provide internal administrator or approver procedures. Self-reported role selection is not authorization. "
        "Use the approved internal CSUBUY support channel or contact the responsible Procurement support team."
    ),
    "transaction_action": (
        "I can explain the documented procurement process, but I cannot submit, approve, edit, withdraw, reject, or otherwise change a requisition, purchase order, invoice, supplier record, cart, or other transaction. "
        "Do not send account credentials or sensitive transaction data here. Ask me for general, source-backed steps instead."
    ),
    "live_lookup": (
        "I do not have live access to CSUBUY, ServiceNow, CFS, supplier, invoice, voucher, purchase-order, or payment records, so I cannot verify the current status of that item. "
        "I can provide public, source-backed instructions for where you can check it yourself, or you can contact the responsible CSUB support office."
    ),
}


def _contains_pattern(text: str, patterns: tuple[str, ...]) -> bool:
    return any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns)


def _without_leading_pleasantry(message: str) -> str:
    return LEADING_PLEASANTRY_PATTERN.sub("", message).strip()


def _is_action_request(message: str) -> bool:
    if not ACTION_PATTERN.search(message):
        return False
    return not GENERAL_HOWTO_PATTERN.search(_without_leading_pleasantry(message))


def _is_live_lookup(message: str) -> bool:
    if not (
        LIVE_OBJECT_PATTERN.search(message) and LIVE_LOOKUP_PATTERN.search(message)
    ):
        return False
    if GENERAL_HOWTO_PATTERN.search(_without_leading_pleasantry(message)) and not re.search(
        r"\b\d{4,}\b|\bmy\b", message, re.IGNORECASE
    ):
        return False
    return True


def _clarification_for(message: str) -> str | None:
    lowered = message.casefold()
    if "unfinalized" in lowered and any(
        term in lowered for term in ("cart", "punchout")
    ):
        return (
            "To avoid applying the wrong workflow, is this still a punchout shopping cart/session, "
            "or is it a completed purchase order in CSUBUY that is labeled as having unfinalized revisions?"
        )
    has_amount = bool(
        re.search(
            r"(?:\$\s*\d|\b\d[\d,]*(?:\.\d{1,2})?\s*(?:dollars?|usd|k)\b)", lowered
        )
    )
    has_specific_software_context = any(
        term in lowered
        for term in (
            "renewal",
            "new subscription",
            "cloud",
            "data",
            "contract",
            "supplier",
            "vendor",
            "license",
            "approved software",
        )
    )
    broad_software = any(
        term in lowered for term in ("software", "subscription")
    ) and any(term in lowered for term in ("need", "buy", "purchase", "get", "acquire"))
    if broad_software and not (has_amount and has_specific_software_context):
        return (
            "To recommend the right path, is this new software or a renewal, what is the estimated amount, "
            "does it store or access university data, and do you know whether the supplier and contract already exist?"
        )
    broad_purchase = bool(
        re.search(
            r"\b(?:i need to|want to|trying to)\s+(?:buy|purchase|get|order)\b", lowered
        )
    )
    if broad_purchase and not has_amount:
        return "What are you buying, what is the estimated total amount, and do you know whether the supplier is already registered or a contract already exists?"
    return None


def classify_request(message: str, role: str) -> dict[str, str] | None:
    lowered = message.casefold()
    if any(term in lowered for term in SENSITIVE_ACCESS_TERMS) or _contains_pattern(
        message, SENSITIVE_ACCESS_PATTERNS
    ):
        return {
            "route": "sensitive_access",
            "answer": FIXED_RESPONSES["sensitive_access"],
        }
    if _contains_pattern(message, PROMPT_ATTACK_PATTERNS):
        return {"route": "prompt_attack", "answer": FIXED_RESPONSES["prompt_attack"]}
    if _is_action_request(message):
        return {
            "route": "transaction_action",
            "answer": FIXED_RESPONSES["transaction_action"],
        }
    vendor_status_request = (
        role == "vendor"
        and LIVE_OBJECT_PATTERN.search(message)
        and LIVE_LOOKUP_PATTERN.search(message)
    )
    if _is_live_lookup(message) or vendor_status_request:
        return {"route": "live_lookup", "answer": FIXED_RESPONSES["live_lookup"]}
    if _contains_pattern(message, INTERNAL_PROCEDURE_PATTERNS):
        return {
            "route": "internal_procedure",
            "answer": FIXED_RESPONSES["internal_procedure"],
        }
    if _contains_pattern(message, OUT_OF_SCOPE_PATTERNS) and not any(
        term in lowered for term in PROCUREMENT_TERMS
    ):
        return {"route": "out_of_scope", "answer": FIXED_RESPONSES["out_of_scope"]}
    clarification = _clarification_for(message)
    if clarification:
        return {"route": "clarification", "answer": clarification}
    return None
