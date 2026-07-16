"""Read-only status lookup boundary for the synthetic demonstration records.

The public demo uses an in-memory provider so no transaction data is stored or
queried outside the Lambda package. A production implementation can replace
this provider with an authenticated CSUB system integration while preserving
the same structured response contract. Authorization must remain server-side;
the model must never receive credentials or grant record access.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any


DEMO_ID_PATTERN = re.compile(r"\bDEMO-[A-Z]{2,5}-\d{4}\b", re.IGNORECASE)
DEMO_MUTATION_PATTERN = re.compile(
    r"\b(?:approve|submit|edit|modify|change|cancel|delete|withdraw|reject|finalize|pay|process)\b",
    re.IGNORECASE,
)

DEMO_RECORDS: dict[str, dict[str, Any]] = {
    "DEMO-REQ-1001": {
        "record_type": "Requisition",
        "title": "Faculty workstation equipment",
        "status": "Pending department approval",
        "current_stage": 2,
        "stages": [
            "Submitted",
            "Department approval",
            "Procurement review",
            "Purchase order issued",
        ],
        "fields": [
            {"label": "Amount", "value": "$2,480.00"},
            {"label": "Supplier", "value": "Technology Supply Co."},
            {"label": "Department", "value": "Academic Affairs"},
            {"label": "Submitted", "value": "July 14, 2026"},
        ],
        "next_step": "The department approver reviews the requisition before it can continue to Procurement.",
        "last_updated": "July 16, 2026 at 9:20 AM",
    },
    "DEMO-PO-2001": {
        "record_type": "Purchase order",
        "title": "Instructional laboratory supplies",
        "status": "Purchase order issued",
        "current_stage": 2,
        "stages": [
            "Requisition approved",
            "PO issued",
            "Supplier fulfillment",
            "Receipt recorded",
        ],
        "fields": [
            {"label": "Amount", "value": "$1,275.40"},
            {"label": "Supplier", "value": "Lab Supply Co."},
            {"label": "Delivery", "value": "July 22, 2026"},
            {"label": "Related requisition", "value": "REQ-1002"},
        ],
        "next_step": "The supplier fulfills the order; the requester records receipt after delivery when required.",
        "last_updated": "July 16, 2026 at 10:05 AM",
    },
    "DEMO-INV-3001": {
        "record_type": "Invoice",
        "title": "Equipment delivery invoice",
        "status": "In Accounts Payable review",
        "current_stage": 2,
        "stages": [
            "Invoice received",
            "AP review",
            "Payment scheduled",
            "Paid",
        ],
        "fields": [
            {"label": "Invoice total", "value": "$2,480.00"},
            {"label": "Supplier", "value": "Technology Supply Co."},
            {"label": "Purchase order", "value": "PO-2003"},
            {"label": "Invoice date", "value": "July 11, 2026"},
        ],
        "next_step": "Accounts Payable completes its review before the payment can be scheduled.",
        "last_updated": "July 16, 2026 at 11:40 AM",
    },
    "DEMO-VCH-4002": {
        "record_type": "Voucher",
        "title": "Completed payment",
        "status": "Paid",
        "current_stage": 4,
        "stages": [
            "Voucher created",
            "Review complete",
            "Payment scheduled",
            "Paid",
        ],
        "fields": [
            {"label": "Payment amount", "value": "$845.75"},
            {"label": "Supplier", "value": "Office Products Co."},
            {"label": "Payment method", "value": "ACH"},
            {"label": "Paid date", "value": "July 15, 2026"},
        ],
        "next_step": "No action is required for this completed demonstration record.",
        "last_updated": "July 15, 2026 at 3:15 PM",
    },
}


@dataclass(frozen=True)
class StatusToolResult:
    """A controlled status-tool result for the chat adapter."""

    answer: str
    status_card: dict[str, Any] | None
    outcome: str


def demo_ids_in_message(message: str) -> list[str]:
    """Return unique normalized demo identifiers in message order."""
    return list(
        dict.fromkeys(
            match.group(0).upper() for match in DEMO_ID_PATTERN.finditer(message)
        )
    )


def contains_demo_id(message: str) -> bool:
    return bool(DEMO_ID_PATTERN.search(message))


def requests_demo_mutation(message: str) -> bool:
    return contains_demo_id(message) and bool(DEMO_MUTATION_PATTERN.search(message))


def lookup_status(message: str, role: str) -> StatusToolResult | None:
    """Resolve one synthetic identifier without retrieval or model execution.

    ``role`` is accepted to keep the adapter compatible with a future
    authorization-aware provider. It does not grant access in this public demo.
    """
    del role
    demo_ids = demo_ids_in_message(message)
    if not demo_ids:
        return None
    if len(demo_ids) > 1:
        return StatusToolResult(
            answer=(
                "I found more than one identifier. Enter one `DEMO-*` "
                "identifier at a time so I can show one status record."
            ),
            status_card=None,
            outcome="multiple_ids",
        )

    record_id = demo_ids[0]
    record = DEMO_RECORDS.get(record_id)
    if record is None:
        examples = ", ".join(f"`{value}`" for value in DEMO_RECORDS)
        return StatusToolResult(
            answer=(
                f"I could not find `{record_id}`. "
                f"Try {examples}. No live procurement system was queried."
            ),
            status_card=None,
            outcome="not_found",
        )

    status_card = {
        "record_id": record_id,
        "record_type": record["record_type"],
        "title": record["title"],
        "status": record["status"],
        "current_stage": record["current_stage"],
        "stages": record["stages"],
        "fields": record["fields"],
        "next_step": record["next_step"],
        "last_updated": record["last_updated"],
    }
    return StatusToolResult(
        answer=(
            f"I found the {record['record_type'].lower()} `{record_id}`. "
            f"Its current status is **{record['status']}**. I opened the status details on the right."
        ),
        status_card=status_card,
        outcome="found",
    )
