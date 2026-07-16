"""Citation normalization and deterministic grounding checks."""

from __future__ import annotations

import re
from typing import Any

from backend.config import ESCALATION_CONTACT, ESCALATION_EMAIL

AUDIT_INSTRUCTIONS = f"""You are a strict citation and policy-grounding auditor. Evaluate the proposed answer only against the supplied source excerpts.

Mark valid=false if any procedural, policy, threshold, form, system, timeline, contact, eligibility, or next-step claim is not explicitly supported by its cited excerpt. Also mark false for a wrong citation, an uncited factual claim, a changed numeric boundary or comparison operator, invented steps, or advice generalized beyond the named vendor/system/source scope. Allow only direct literal comparison logic from a cited threshold: for example, a value exactly equal to X does not satisfy a rule written as greater than X. Capability disclaimers and the configured escalation sentence "{ESCALATION_CONTACT}" do not need citations. Do not accept any other uncited contact as a substitute for {ESCALATION_EMAIL}."""


def cited_source_ids(answer: str) -> set[str]:
    return set(re.findall(r"\[(S\d+)\]", answer))


def normalize_citation_syntax(answer: str) -> str:
    """Keep citation IDs machine-readable while preserving model-added locators."""
    return re.sub(r"\[(S\d+),\s*([^\]]+)\]", r"[\1] (\2)", answer)


def citation_coverage_reason(answer: str) -> str | None:
    """Return a failure reason when a substantive answer line lacks a citation."""
    generic_prefixes = (
        "i cannot ",
        "i can't ",
        "i do not have ",
        "i don't have ",
        "i could not find ",
        "i couldn't find ",
        "the available public sources are insufficient ",
        "the available public sources do not specify ",
        "the available sources do not ",
        "the supplied public sources are insufficient ",
        "the supplied public sources do not specify ",
        "the excerpts do not specify ",
        "the provided excerpts do not specify ",
        "the sources do not specify ",
        "it is recommended to contact ",
        "please contact ",
        "contact csub ",
        "if you need further assistance, contact ",
        "if you still need help, contact ",
        "for additional help, contact ",
    )
    lines = answer.splitlines()
    cited_table_lines: set[int] = set()
    index = 0
    while index < len(lines):
        if not lines[index].strip().startswith("|"):
            index += 1
            continue
        table_start = index
        while index < len(lines) and lines[index].strip().startswith("|"):
            index += 1
        citation_index = index
        while citation_index < len(lines) and not lines[citation_index].strip():
            citation_index += 1
        if citation_index < len(lines) and re.fullmatch(
            r"(?:\[S\d+\]\s*)+", lines[citation_index].strip()
        ):
            cited_table_lines.update(range(table_start, index))

    parent_line_cited = False
    for line_index, raw_line in enumerate(lines):
        if line_index in cited_table_lines:
            continue
        is_nested_bullet = len(raw_line) - len(
            raw_line.lstrip()
        ) >= 2 and raw_line.lstrip().startswith(("- ", "* "))
        if is_nested_bullet and parent_line_cited:
            continue
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("#"):
            parent_line_cited = False
            continue
        heading = re.sub(r"[*_`]", "", line).strip()
        if heading.endswith(":") and len(re.findall(r"\b\w+\b", heading)) <= 8:
            parent_line_cited = False
            continue
        line = re.sub(r"^#{1,6}\s+", "", line)
        if line.endswith(":") and not re.search(r"\[(?:S\d+)\]", line):
            continue
        claim = re.sub(r"^>\s*", "", line).strip()
        claim = re.sub(r"^(?:[-*]\s+|\d+[.)]\s*)", "", claim).strip()
        claim = re.sub(r"^\*\*[^*]+:?\*\*:?\s*", "", claim).strip()
        if len(re.findall(r"\b\w+\b", claim)) < 3:
            continue
        if claim.casefold().startswith(generic_prefixes):
            parent_line_cited = False
            continue
        parent_line_cited = bool(re.search(r"\[(?:S\d+)\]", claim))
        if not parent_line_cited:
            return "uncited_claim"
    return None


def context_for_citations(context: str, citations: set[str]) -> str:
    chunks = re.split(r"\n\n(?=\[S\d+\]\s)", context)
    selected = []
    for chunk in chunks:
        match = re.match(r"\[(S\d+)\]\s", chunk)
        if match and match.group(1) in citations:
            selected.append(chunk)
    return "\n\n".join(selected)


def grounding_precheck(
    answer: str,
    sources: list[dict[str, Any]],
) -> tuple[str, set[str]]:
    available_ids = {str(source["id"]) for source in sources}
    citations = cited_source_ids(answer)
    if not answer or not citations:
        return "missing_citation", citations
    if not citations.issubset(available_ids):
        return "unknown_citation", citations
    coverage_failure = citation_coverage_reason(answer)
    if coverage_failure:
        return coverage_failure, citations
    return "supported", citations


def build_audit_prompt(answer: str, context: str, citations: set[str]) -> str:
    cited_context = context_for_citations(context, citations)
    return f"""CITED SOURCE EXCERPTS
{cited_context}

PROPOSED ANSWER
{answer}"""


def sources_for_answer(
    answer: str, sources: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    cited = cited_source_ids(answer)
    return [source for source in sources if source["id"] in cited]
