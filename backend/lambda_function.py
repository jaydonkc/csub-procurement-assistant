"""AWS Lambda adapter for the public CSUB Procurement Assistant.

The model loop is implemented with Pydantic AI. Public-access policy,
retrieval, source filtering, and workflow routing remain deterministic and run
before model generation.
"""

from __future__ import annotations

import base64
import json
import os
from typing import Any

import boto3
from pydantic import ValidationError

from backend import grounding, policy, retrieval, source_access, workflows
from backend.config import (
    ALLOWED_ORIGIN,
    KNOWLEDGE_BASE_ID,
    MAX_BODY_BYTES,
    MAX_CHUNKS_PER_SOURCE,
    MAX_CONTEXT_EXCERPTS,
    MEDIA_URL_TTL_SECONDS,
    MODEL_ID,
    SOURCE_BUCKET,
    VALIDATOR_MODEL_ID,
)
from backend.models import ChatRequest, ChatResponse
from backend.pydantic_agent import GroundingFailure, ProcurementAgent
from backend.ui import INDEX_HTML


_agent_runtime = None
_bedrock_runtime = None
_s3_client = None
_procurement_agent: ProcurementAgent | None = None
_procurement_agent_client_id: int | None = None


def _clients():
    global _agent_runtime, _bedrock_runtime
    if _agent_runtime is None:
        _agent_runtime = boto3.client("bedrock-agent-runtime")
    if _bedrock_runtime is None:
        _bedrock_runtime = boto3.client("bedrock-runtime")
    return _agent_runtime, _bedrock_runtime


def _s3():
    global _s3_client
    if _s3_client is None:
        _s3_client = boto3.client("s3")
    return _s3_client


def _pydantic_runtime() -> ProcurementAgent:
    """Reuse the agent between warm Lambda invocations and test clients."""
    global _procurement_agent, _procurement_agent_client_id
    _, bedrock_runtime = _clients()
    client_id = id(bedrock_runtime)
    if _procurement_agent is None or _procurement_agent_client_id != client_id:
        _procurement_agent = ProcurementAgent(
            bedrock_runtime=bedrock_runtime,
            model_id=MODEL_ID,
            validator_model_id=VALIDATOR_MODEL_ID,
        )
        _procurement_agent_client_id = client_id
    return _procurement_agent


def response(
    status_code: int,
    body: Any,
    content_type: str = "application/json",
) -> dict[str, Any]:
    if content_type == "application/json":
        body = json.dumps(body)
    headers = {
        "content-type": f"{content_type}; charset=utf-8",
        "cache-control": "no-store",
        "access-control-allow-origin": ALLOWED_ORIGIN,
        "access-control-allow-methods": "GET,POST,OPTIONS",
        "access-control-allow-headers": "content-type",
        "access-control-max-age": "300",
        "x-content-type-options": "nosniff",
        "x-frame-options": "DENY",
        "referrer-policy": "no-referrer",
        "permissions-policy": "camera=(), microphone=(), geolocation=()",
        "content-security-policy": (
            "default-src 'self'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; "
            "connect-src 'self'; img-src 'none'; object-src 'none'; base-uri 'none'; "
            "frame-ancestors 'none'; form-action 'self'"
        ),
    }
    return {"statusCode": status_code, "headers": headers, "body": body}


def request_method(event: dict[str, Any]) -> str:
    """Read the HTTP method from Lambda URL, HTTP API, or REST API events."""
    request_context = event.get("requestContext") or {}
    http_context = request_context.get("http") or {}
    return str(http_context.get("method") or event.get("httpMethod") or "GET").upper()


def request_path(event: dict[str, Any]) -> str:
    """Read and normalize the request path across API Gateway event versions."""
    request_context = event.get("requestContext") or {}
    http_context = request_context.get("http") or {}
    path = http_context.get("path") or event.get("rawPath") or event.get("path") or "/"
    normalized = "/" + str(path).strip().lstrip("/")
    return normalized.rstrip("/") or "/"


def parse_body(event: dict[str, Any]) -> dict[str, Any]:
    body = event.get("body") or "{}"
    if not isinstance(body, str):
        raise ValueError("Request body must be text.")
    if len(body.encode("utf-8")) > MAX_BODY_BYTES:
        raise ValueError("Request body is too large.")
    if event.get("isBase64Encoded"):
        decoded = base64.b64decode(body, validate=True)
        if len(decoded) > MAX_BODY_BYTES:
            raise ValueError("Request body is too large.")
        body = decoded.decode("utf-8")
    parsed = json.loads(body)
    if not isinstance(parsed, dict):
        raise ValueError("Request body must be a JSON object.")
    return parsed


def _retrieve_sources(message: str) -> tuple[str, list[dict[str, Any]]]:
    agent_runtime, _ = _clients()
    return retrieval.retrieve_sources(
        message,
        client=agent_runtime,
        knowledge_base_id=KNOWLEDGE_BASE_ID,
        max_context_excerpts=MAX_CONTEXT_EXCERPTS,
        max_chunks_per_source=MAX_CHUNKS_PER_SOURCE,
    )


def _sources_with_urls(sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not any(
        source_access.public_video_object_key(source)
        or source_access.public_document_object_key(source)
        for source in sources
    ):
        return [dict(source) for source in sources]
    return source_access.sources_with_urls(
        sources,
        s3_client=_s3(),
        source_bucket=SOURCE_BUCKET,
        ttl_seconds=MEDIA_URL_TTL_SECONDS,
    )


def _request_id(context: Any) -> str:
    return str(getattr(context, "aws_request_id", "local"))


def _log(event: str, request_id: str, **fields: Any) -> None:
    print(
        json.dumps({"event": event, "request_id": request_id, **fields}, sort_keys=True)
    )


def _chat_payload(
    answer: str,
    sources: list[dict[str, Any]],
    request_id: str,
) -> dict[str, Any]:
    return ChatResponse(
        answer=answer,
        sources=sources,
        request_id=request_id,
    ).model_dump(mode="json", exclude_none=True)


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    request_id = _request_id(context)
    method = request_method(event)
    path = request_path(event)
    if method == "OPTIONS" and path in {"/v1/chat", "/v1/health"}:
        return response(204, "", "text/plain")
    if method == "GET" and path == "/v1/health":
        return response(
            200,
            {
                "status": "ok",
                "service": "csub-procurement-assistant",
                "version": os.environ.get("AWS_LAMBDA_FUNCTION_VERSION", "$LATEST"),
                "request_id": request_id,
            },
        )
    if method == "GET" and path == "/":
        return response(200, INDEX_HTML, "text/html")
    if method == "POST" and path not in {"/", "/v1/chat"}:
        return response(404, {"error": "Not found", "request_id": request_id})
    if method != "POST":
        return response(405, {"error": "Method not allowed", "request_id": request_id})

    try:
        payload = parse_body(event)
        try:
            chat_request = ChatRequest.model_validate(payload)
        except ValidationError as exc:
            _log("request_rejected", request_id, error_type=type(exc).__name__)
            return response(
                400,
                {
                    "error": "Provide a message of 1 to 4000 characters and choose requester, vendor, or internal support staff.",
                    "request_id": request_id,
                },
            )

        message = chat_request.message
        role = chat_request.role
        history = [item.model_dump() for item in chat_request.history]
        route = policy.classify_request(message, role)
        if route:
            _log(
                "request_complete",
                request_id,
                route=route["route"],
                source_count=0,
                grounding="not_applicable",
            )
            return response(200, _chat_payload(route["answer"], [], request_id))

        source_context, sources = _retrieve_sources(message)
        if not sources:
            answer = (
                "I could not find an approved public source that supports a reliable answer, so I will not guess. "
                "Please contact CSUB Procurement or the office responsible for this request."
            )
            _log(
                "request_complete",
                request_id,
                route="no_public_source",
                source_count=0,
                grounding="not_applicable",
            )
            return response(200, _chat_payload(answer, [], request_id))

        guided_answer = workflows.guided_template_answer(
            message, source_context, sources
        )
        if guided_answer:
            answer, guided_sources = guided_answer
            guided_sources = _sources_with_urls(guided_sources)
            _log(
                "request_complete",
                request_id,
                route="guided_template",
                source_count=len(guided_sources),
                grounding="source_terms_verified",
            )
            return response(200, _chat_payload(answer, guided_sources, request_id))

        try:
            agent_run = _pydantic_runtime().run_grounded(
                message=message,
                role=role,
                history=history,
                context=source_context,
                sources=sources,
            )
        except GroundingFailure as exc:
            fallback_sources = _sources_with_urls(sources[:3])
            fallback = (
                "I found potentially relevant public sources, but I could not verify a fully grounded answer to this question, so I will not guess. "
                "The closest source cards are listed below; contact CSUB Procurement or the responsible support office for confirmation."
            )
            _log(
                "request_complete",
                request_id,
                route="grounding_fallback",
                source_count=len(fallback_sources),
                grounding=exc.reason,
            )
            return response(200, _chat_payload(fallback, fallback_sources, request_id))

        cited_sources = _sources_with_urls(
            grounding.sources_for_answer(agent_run.answer, sources)
        )
        _log(
            "request_complete",
            request_id,
            route="grounded_answer",
            source_count=len(cited_sources),
            grounding=agent_run.grounding,
            repaired=agent_run.repaired,
        )
        return response(200, _chat_payload(agent_run.answer, cited_sources, request_id))
    except (
        json.JSONDecodeError,
        UnicodeDecodeError,
        ValueError,
        base64.binascii.Error,
    ) as exc:
        _log("request_rejected", request_id, error_type=type(exc).__name__)
        return response(
            400, {"error": str(exc) or "Invalid request.", "request_id": request_id}
        )
    except Exception as exc:
        _log("request_failed", request_id, error_type=type(exc).__name__)
        return response(
            500,
            {
                "error": "The assistant could not safely complete the request.",
                "request_id": request_id,
            },
        )
