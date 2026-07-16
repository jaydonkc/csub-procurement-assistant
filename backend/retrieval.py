"""Deterministic Bedrock Knowledge Base retrieval."""

from __future__ import annotations

import re
from typing import Any

from backend.source_access import is_public_source


QUERY_EXPANSIONS = (
    (
        ("invoice",),
        ("information", "include", "requirement", "required"),
        "CSUB invoice itemized match PO Direct Pay supplier invoice date number Accounts Payable",
    ),
    (
        ("supplier", "vendor"),
        ("invitation", "invite", "re-invite", "reinvite"),
        "Supplier Did Not Receive Invitation invited email Re-Invite Request jaggaer.com",
    ),
    (
        ("supplier", "vendor"),
        ("search", "find", "registered", "active"),
        "Supplier Search Tips CSUBUY supplier search registered active invitation",
    ),
    (
        ("amazon",),
        tuple(),
        "Amazon Accounts and Access CSUBUY Amazon Business email punchout",
    ),
    (
        ("voucher",),
        ("pay status", "payment status", "status"),
        "Voucher Pay Status Orders Search Vouchers Payment Information",
    ),
    (
        ("supplier", "vendor"),
        ("registration returned", "returned for correction"),
        "Supplier Registration Returned correction reason SM Team noreply jaggaer resources",
    ),
    (
        ("change request",),
        ("purchase order", "po", "cfs", "history", "status"),
        "Purchase Order Change Request current PO status vouchers payments receipts History Summary sent to CFS completed",
    ),
    (
        ("marketplace",),
        ("end user", "shop", "shopping", "cart"),
        "Marketplace End User Training CSUBUY marketplace end user shopping cart",
    ),
    (
        ("form", "forms"),
        tuple(),
        "CSUB procurement forms purchasing forms request form",
    ),
    (
        ("software", "subscription", "cloud"),
        tuple(),
        "technology software cloud subscription purchase review CSUBUY",
    ),
)


def build_retrieval_query(message: str) -> str:
    lowered = message.casefold()
    expansions = []
    for primary_terms, secondary_terms, expansion in QUERY_EXPANSIONS:
        if not any(term in lowered for term in primary_terms):
            continue
        if secondary_terms and not any(term in lowered for term in secondary_terms):
            continue
        expansions.append(expansion)
    if not expansions:
        return message
    return f"{message}\nSearch concepts: {'; '.join(expansions)}"


def generation_hint(message: str) -> str:
    lowered = message.casefold()
    if "invoice" in lowered and any(
        term in lowered for term in ("information", "include", "requirement", "required")
    ):
        return (
            "Provide every supported invoice requirement or submission detail first. Clearly distinguish vendor-facing guidance "
            "from internal voucher-entry fields, label the result non-exhaustive when the source does not claim completeness, "
            "and escalate only the undocumented fields rather than refusing the whole question."
        )
    if (
        any(term in lowered for term in ("supplier", "vendor"))
        and any(term in lowered for term in ("invitation", "invite"))
    ):
        return (
            "Use the documented invited-email decision tree: verify the invited address, distinguish the correct-address "
            "and incorrect-address branches, then include the documented spam-filter escalation."
        )
    if "amazon" in lowered and any(
        term in lowered for term in ("access", "account", "punchout")
    ):
        return (
            "Explain how the CSUBUY profile email affects Amazon Business access. Include only account branches whose exact "
            "conditions and actions appear in the excerpts; do not generalize one branch to every Amazon account state."
        )
    if any(
        term in lowered
        for term in ("new supplier", "request a supplier", "cannot find a supplier")
    ):
        return (
            "Focus only on searching first, deciding whether a new request is appropriate, the core request steps, "
            "status follow-up, and escalation. Use at most six checklist items and 350 words. Omit detailed status branches or "
            "extension-request advice unless each is explicit in the cited excerpt."
        )
    if "voucher" in lowered and "status" in lowered:
        return (
            "State only the documented navigation path and the fields or values explicitly shown. Do not infer who has access, "
            "define statuses beyond the excerpt, or claim that the excerpt lists every possible status."
        )
    if "receipt" in lowered:
        return "Preserve the complete documented receipt sequence. Cite each numbered step; a cited parent step may introduce its own indented field list."
    return "Use the shortest complete answer supported by the excerpts."


def _source_path(metadata: dict[str, Any], index: int) -> str:
    path = str(metadata.get("relative_path") or "").strip()
    if path:
        return path
    uri = str(metadata.get("source_uri") or "").strip()
    if uri:
        marker = "/approved/"
        if marker in uri:
            return f"approved/{uri.split(marker, 1)[1]}"
    return f"Public source {index}"


def _timestamp(metadata: dict[str, Any], text: str) -> str | None:
    start = metadata.get("start_timestamp")
    end = metadata.get("end_timestamp")
    if start and end:
        return f"{start} --> {end}"
    match = re.search(
        r"\d{2}:\d{2}:\d{2}\.\d{3}\s+-->\s+\d{2}:\d{2}:\d{2}\.\d{3}",
        text,
    )
    return match.group(0) if match else None


def retrieve_sources(
    message: str,
    *,
    client: Any,
    knowledge_base_id: str,
    max_context_excerpts: int,
    max_chunks_per_source: int,
) -> tuple[str, list[dict[str, Any]]]:
    """Retrieve approved context before the model runs.

    Retrieval is intentionally application-controlled rather than an optional
    model tool, so a procedural answer can never skip the public-source filter.
    """
    result = client.retrieve(
        knowledgeBaseId=knowledge_base_id,
        retrievalQuery={"text": build_retrieval_query(message)},
        retrievalConfiguration={
            "managedSearchConfiguration": {
                "numberOfResults": 12,
                "rerankingModelType": "NONE",
                "filter": {"notEquals": {"key": "access_scope", "value": "internal"}},
            }
        },
    )
    sources: list[dict[str, Any]] = []
    context: list[str] = []
    path_ids: dict[str, str] = {}
    path_chunk_counts: dict[str, int] = {}
    for index, item in enumerate(result.get("retrievalResults", []), start=1):
        metadata = item.get("metadata") or {}
        text = str((item.get("content") or {}).get("text", "")).strip()
        path = _source_path(metadata, index)
        if not text or not is_public_source(metadata, path):
            continue
        if path_chunk_counts.get(path, 0) >= max_chunks_per_source:
            continue
        path_chunk_counts[path] = path_chunk_counts.get(path, 0) + 1
        source_id = path_ids.get(path)
        timestamp = _timestamp(metadata, text)
        if source_id is None:
            source_id = f"S{len(sources) + 1}"
            path_ids[path] = source_id
            sources.append(
                {
                    "id": source_id,
                    "path": path,
                    "kind": metadata.get("source_kind"),
                    "timestamp": timestamp,
                }
            )
        elif timestamp:
            for source in sources:
                if source["id"] == source_id and not source.get("timestamp"):
                    source["timestamp"] = timestamp
                    break
        context.append(f"[{source_id}] {path}\n{text[:3000]}")
        if len(context) >= max_context_excerpts:
            break
    return "\n\n".join(context), sources
