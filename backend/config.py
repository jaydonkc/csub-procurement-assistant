"""Environment-backed configuration for the CSUB procurement runtime."""

from __future__ import annotations

import os


KNOWLEDGE_BASE_ID = os.environ.get("KNOWLEDGE_BASE_ID", "")
MODEL_ID = os.environ.get("MODEL_ID", "us.anthropic.claude-sonnet-4-6")
VALIDATOR_MODEL_ID = os.environ.get(
    "VALIDATOR_MODEL_ID",
    "us.anthropic.claude-haiku-4-5-20251001-v1:0",
)
ROUTER_MODEL_ID = os.environ.get("ROUTER_MODEL_ID", VALIDATOR_MODEL_ID)

MAX_BODY_BYTES = 64_000
MAX_MESSAGE_LENGTH = 4_000
MAX_HISTORY_ITEMS = 6
MAX_HISTORY_ITEM_LENGTH = 2_000
MAX_CONTEXT_EXCERPTS = 8
MAX_CHUNKS_PER_SOURCE = 2

ALLOWED_ORIGIN = os.environ.get("ALLOWED_ORIGIN", "*")
SOURCE_BUCKET = os.environ.get(
    "SOURCE_BUCKET",
    "csub-pa-mvp-source-335010339891-us-west-2",
)
MEDIA_URL_TTL_SECONDS = min(
    max(int(os.environ.get("MEDIA_URL_TTL_SECONDS", "900")), 60),
    3_600,
)
