"""Public-source filtering and short-lived source-link generation."""

from __future__ import annotations

from typing import Any

from botocore.exceptions import BotoCoreError, ClientError


DOCUMENT_CONTENT_TYPES = {
    ".doc": "application/msword",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".pdf": "application/pdf",
    ".ppt": "application/vnd.ms-powerpoint",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".xls": "application/vnd.ms-excel",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}

INTERNAL_PATH_FRAGMENTS = (
    "admin (campus, security, & optimize)/",
    "admin (campus, security, and optimize)/",
    "approvals/",
    "supplier management faq (internal)",
    "viewing supplier data with sensitive data pii access",
    "csub buy.docx",
    "csub buy.pdf",
)


def is_public_source(metadata: dict[str, Any], path: str) -> bool:
    lowered_path = path.casefold()
    if any(fragment in lowered_path for fragment in INTERNAL_PATH_FRAGMENTS):
        return False
    access_scope = str(metadata.get("access_scope", "")).casefold().strip()
    sensitivity = (
        str(metadata.get("sensitivity", metadata.get("data_classification", "")))
        .casefold()
        .strip()
    )
    if access_scope in {
        "internal",
        "restricted",
        "private",
        "sensitive-pii",
        "sensitive-pii access",
    }:
        return False
    if sensitivity in {
        "internal",
        "restricted",
        "pii",
        "sensitive-pii",
        "sensitive-pii access",
    }:
        return False
    return True


def _public_source_path(source: dict[str, Any]) -> str | None:
    path = str(source.get("path", "")).strip().replace("\\", "/")
    parts = path.split("/")
    if any(part in {"", ".", ".."} for part in parts) or not is_public_source({}, path):
        return None
    return path


def public_video_object_key(source: dict[str, Any]) -> str | None:
    """Map a cited public transcript source to its private S3 video object."""
    path = _public_source_path(source)
    kind = str(source.get("kind", "")).casefold()
    if (
        not path
        or not path.casefold().endswith(".mp4")
        or kind not in {"", "video_transcript"}
    ):
        return None
    return f"media/videos/{path}"


def public_caption_object_key(source: dict[str, Any]) -> str | None:
    """Map a cited public video to its approved canonical WebVTT object."""
    video_key = public_video_object_key(source)
    if not video_key:
        return None
    path = _public_source_path(source)
    if not path:
        return None
    return f"approved/transcripts/{path[:-4]}.vtt"


def public_document_object_key(source: dict[str, Any]) -> tuple[str, str] | None:
    """Map a cited public document to its private S3 object and content type."""
    path = _public_source_path(source)
    if not path:
        return None
    lowered_path = path.casefold()
    extension = next(
        (item for item in DOCUMENT_CONTENT_TYPES if lowered_path.endswith(item)),
        None,
    )
    if not extension:
        return None
    return f"approved/documents/{path}", DOCUMENT_CONTENT_TYPES[extension]


def _presigned_source_url(
    *,
    s3_client: Any,
    source_bucket: str,
    object_key: str,
    content_type: str,
    ttl_seconds: int,
) -> str | None:
    try:
        return s3_client.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": source_bucket,
                "Key": object_key,
                "ResponseContentType": content_type,
            },
            ExpiresIn=ttl_seconds,
        )
    except (BotoCoreError, ClientError, ValueError):
        return None


def sources_with_urls(
    sources: list[dict[str, Any]],
    *,
    s3_client: Any,
    source_bucket: str,
    ttl_seconds: int,
) -> list[dict[str, Any]]:
    """Attach short-lived source URLs without making the source bucket public."""
    enriched_sources = []
    for source in sources:
        enriched = dict(source)
        video_key = public_video_object_key(enriched)
        if video_key:
            source_url = _presigned_source_url(
                s3_client=s3_client,
                source_bucket=source_bucket,
                object_key=video_key,
                content_type="video/mp4",
                ttl_seconds=ttl_seconds,
            )
            caption_key = public_caption_object_key(enriched)
            caption_url = (
                _presigned_source_url(
                    s3_client=s3_client,
                    source_bucket=source_bucket,
                    object_key=caption_key,
                    content_type="text/vtt",
                    ttl_seconds=ttl_seconds,
                )
                if caption_key
                else None
            )
            if source_url:
                enriched["source_url"] = source_url
                enriched["media_url"] = source_url
            if caption_url:
                enriched["caption_url"] = caption_url
            if source_url or caption_url:
                enriched["media_expires_in"] = ttl_seconds
        else:
            document_object = public_document_object_key(enriched)
            if document_object:
                object_key, content_type = document_object
                source_url = _presigned_source_url(
                    s3_client=s3_client,
                    source_bucket=source_bucket,
                    object_key=object_key,
                    content_type=content_type,
                    ttl_seconds=ttl_seconds,
                )
                if source_url:
                    enriched["source_url"] = source_url
                    enriched["media_expires_in"] = ttl_seconds
        enriched_sources.append(enriched)
    return enriched_sources
