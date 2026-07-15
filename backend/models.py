"""Typed HTTP and model contracts for the procurement assistant."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from backend.config import (
    MAX_HISTORY_ITEM_LENGTH,
    MAX_HISTORY_ITEMS,
    MAX_MESSAGE_LENGTH,
)


Role = Literal["requester", "vendor", "internal_staff"]
HistoryRole = Literal["user", "assistant"]
RetrievalRoute = Literal["conversation", "clarification", "out_of_scope", "retrieve"]


class HistoryItem(BaseModel):
    model_config = ConfigDict(extra="ignore")

    role: HistoryRole
    text: str = Field(min_length=1, max_length=MAX_HISTORY_ITEM_LENGTH)

    @field_validator("text", mode="before")
    @classmethod
    def normalize_text(cls, value: Any) -> str:
        return str(value or "")[:MAX_HISTORY_ITEM_LENGTH].strip()


class ChatRequest(BaseModel):
    """Validated public chat payload.

    Invalid history entries are discarded to preserve the previous tolerant API
    behavior, while the current message and role remain strict.
    """

    model_config = ConfigDict(extra="ignore")

    message: str = Field(min_length=1, max_length=MAX_MESSAGE_LENGTH)
    role: Role
    history: list[HistoryItem] = Field(
        default_factory=list, max_length=MAX_HISTORY_ITEMS
    )

    @field_validator("message", mode="before")
    @classmethod
    def normalize_message(cls, value: Any) -> str:
        if not isinstance(value, str):
            raise ValueError("Message must be text.")
        return value.strip()

    @field_validator("history", mode="before")
    @classmethod
    def normalize_history(cls, value: Any) -> list[dict[str, str]]:
        if not isinstance(value, list):
            return []
        cleaned: list[dict[str, str]] = []
        for item in value[-MAX_HISTORY_ITEMS:]:
            if not isinstance(item, dict) or item.get("role") not in {
                "user",
                "assistant",
            }:
                continue
            text = str(item.get("text", ""))[:MAX_HISTORY_ITEM_LENGTH].strip()
            if text:
                cleaned.append({"role": item["role"], "text": text})
        return cleaned


class SourceCard(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    path: str
    kind: str | None = None
    timestamp: str | None = None
    source_url: str | None = None
    media_url: str | None = None
    media_expires_in: int | None = None


class ChatResponse(BaseModel):
    answer: str
    sources: list[SourceCard] = Field(default_factory=list)
    request_id: str


class RetrievalDecision(BaseModel):
    """Typed output from the pre-retrieval router."""

    model_config = ConfigDict(extra="forbid")

    route: RetrievalRoute
    reply: str = Field(default="", max_length=MAX_MESSAGE_LENGTH)
    search_query: str = Field(default="", max_length=MAX_MESSAGE_LENGTH)
    reason: str = Field(default="model_decision", max_length=80)

    @field_validator("reply", "search_query", "reason", mode="before")
    @classmethod
    def normalize_router_text(cls, value: Any) -> str:
        return " ".join(str(value or "").split()).strip()


GroundingReason = Literal[
    "supported",
    "missing_citation",
    "unsupported_claim",
    "citation_mismatch",
    "numeric_mismatch",
    "scope_mismatch",
]


class GroundingVerdict(BaseModel):
    model_config = ConfigDict(extra="forbid")

    valid: bool
    reason: GroundingReason

    @model_validator(mode="after")
    def require_consistent_reason(self) -> "GroundingVerdict":
        if self.valid != (self.reason == "supported"):
            raise ValueError(
                "A valid verdict must use 'supported', and a rejection must not."
            )
        return self
