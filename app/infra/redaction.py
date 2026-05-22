"""Redaction helper for MLflow, LangSmith, model cards, and manifests.

Ensures no raw secrets or oversized issue payloads are persisted in
telemetry, artifact metadata, or run records.
"""

from __future__ import annotations

import re
from typing import Any

_SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9]{20,}", re.IGNORECASE),
    re.compile(r"(?:api[_\-]?key|token|secret|password|credential)\s*[:=]\s*\S+", re.IGNORECASE),
]

_MEMORY_KEY_VALUE_PATTERN = re.compile(
    r"((?:api[_\-]?key|token|secret|password|credential)\s*[:=]\s*)(\S+)",
    re.IGNORECASE,
)

_RAW_TOKEN_PATTERN = re.compile(r"sk-[A-Za-z0-9]{20,}", re.IGNORECASE)

_MAX_TEXT_FIELD_LENGTH = 500

_REDACTED = "[REDACTED]"


def redact_string(value: str) -> str:
    """Replace potential secrets in a string with a redaction marker."""
    result = value
    for pattern in _SECRET_PATTERNS:
        result = pattern.sub(_REDACTED, result)
    return result


def redact_dict(data: dict[str, Any], text_fields: set[str] | None = None) -> dict[str, Any]:
    """Redact secrets and truncate oversized text fields in a dictionary.

    Recursively processes nested dicts. Keys matching secret patterns are
    replaced. Values in text_fields longer than the max length are truncated.
    """
    text_fields = text_fields or set()
    redacted: dict[str, Any] = {}
    for key, value in data.items():
        key_lower = key.lower()
        if any(
            pat in key_lower
            for pat in ("secret", "password", "token", "api_key", "apikey", "credential")
        ):
            redacted[key] = _REDACTED
            continue
        redacted[key] = _redact_value(value, key, text_fields)
    return redacted


def _redact_value(value: Any, key: str, text_fields: set[str]) -> Any:
    """Redact a single value, recursing into dicts and lists."""
    if isinstance(value, dict):
        return redact_dict(value, text_fields)
    if isinstance(value, list):
        return [_redact_value(item, key, text_fields) for item in value]
    if isinstance(value, str):
        value = redact_string(value)
        if key in text_fields and len(value) > _MAX_TEXT_FIELD_LENGTH:
            value = value[:_MAX_TEXT_FIELD_LENGTH] + "...[TRUNCATED]"
    return value


def redact_model_card(card: dict[str, Any]) -> dict[str, Any]:
    """Redact a model card dict before persistence.

    Ensures no secrets, and marks redaction_applied=True.
    """
    text_fields = {"intended_use", "limitations"}
    result = redact_dict(card, text_fields)
    result["redaction_applied"] = True
    return result


def redact_run_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    """Redact MLflow run metadata before persistence."""
    text_fields = {"tracking_uri", "artifact_uri"}
    return redact_dict(metadata, text_fields)


_SAFE_ISSUE_ANALYSIS_KEYS = {
    "request_id",
    "tool_name",
    "combined_characters",
    "normalized_comment_count",
    "entity_count",
    "entity_types",
    "status",
    "code",
    "trace_id",
    "provider_backend",
    "tracing_backend",
    "timeout_seconds",
    "limitations",
    "error_code",
}


def redact_issue_analysis_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    """Keep only safe, bounded keys for issue-analysis logging and tracing."""
    safe: dict[str, Any] = {}
    for key, value in metadata.items():
        if key in _SAFE_ISSUE_ANALYSIS_KEYS:
            if isinstance(value, str):
                safe[key] = redact_string(value)
            elif isinstance(value, (int, float, bool)):
                safe[key] = value
            elif isinstance(value, list):
                safe[key] = [
                    redact_string(item) if isinstance(item, str) else item for item in value
                ]
            else:
                safe[key] = str(value)
    return safe


def redact_log_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Strip full title/body/comments before logging — retain only length metadata."""
    safe: dict[str, Any] = {}
    for key, value in payload.items():
        if key in {"title", "body", "comments"}:
            if isinstance(value, str):
                safe[f"{key}_len"] = len(value)
            elif isinstance(value, list):
                safe[f"{key}_len"] = len(value)
                safe[f"{key}_count"] = sum(len(c) for c in value if isinstance(c, str))
            continue
        if isinstance(value, str):
            safe[key] = redact_string(value)
        else:
            safe[key] = value
    return safe


def redact_short_term_memory_value(value: str) -> str:
    """Redact secret-like values before short-term memory persistence."""
    result = _MEMORY_KEY_VALUE_PATTERN.sub(r"\1[REDACTED]", value)
    result = _RAW_TOKEN_PATTERN.sub(_REDACTED, result)
    return result


def redact_long_term_memory_content(value: str) -> str:
    """Redact secret-like values before embedding and long-term persistence."""
    result = _MEMORY_KEY_VALUE_PATTERN.sub(r"\1[REDACTED]", value)
    result = _RAW_TOKEN_PATTERN.sub(_REDACTED, result)
    return result


def redact_audit_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    """Redact and bound audit metadata before audit persistence."""
    return redact_dict(metadata)


def redact_chat_message(message: str) -> str:
    """Redact chat message content for logs, traces, and bounded state."""
    return redact_string(message)[:_MAX_TEXT_FIELD_LENGTH]


def redact_chat_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Redact a sequence of chat messages for telemetry."""
    safe_messages: list[dict[str, Any]] = []
    for message in messages:
        safe_messages.append(
            {
                "role": message.get("role"),
                "name": message.get("name"),
                "content": redact_chat_message(str(message.get("content", ""))),
            }
        )
    return safe_messages


def redact_chat_prompt_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Keep prompt telemetry bounded and secret-safe."""
    safe: dict[str, Any] = {}
    for key, value in payload.items():
        if key.endswith("prompt") and isinstance(value, str):
            safe[f"{key}_len"] = len(value)
            continue
        if isinstance(value, str):
            safe[key] = redact_chat_message(value)
        elif isinstance(value, list):
            safe[key] = [redact_chat_message(str(item)) for item in value]
        elif isinstance(value, dict):
            safe[key] = redact_dict(value)
        else:
            safe[key] = value
    return safe


def redact_tool_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Redact tool input/output payloads before logs or traces."""
    return redact_dict(payload)


def redact_llm_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Redact LLM prompt/response metadata before logs or traces."""
    return redact_chat_prompt_payload(payload)


def redact_sse_event(payload: dict[str, Any]) -> dict[str, Any]:
    """Redact SSE event payloads before logs or traces."""
    safe = redact_dict(payload)
    content = safe.get("content")
    if isinstance(content, str):
        safe["content_len"] = len(content)
        del safe["content"]
    error = safe.get("error")
    if isinstance(error, dict):
        safe["error"] = redact_dict(error)
    return safe


def redact_trace_metadata(payload: dict[str, Any]) -> dict[str, Any]:
    """Redact span/root metadata for chat tracing."""
    return redact_dict(payload)


# -- Phase 5 RAG redaction -----------------------------------------------------

_RAG_REDACTED_FIELDS = {"content", "content_preview", "maintainer_answer", "question_context"}

_SAFE_RAG_KEYS = {
    "request_id",
    "trace_id",
    "chunk_id",
    "parent_id",
    "source_type",
    "source_path",
    "retrieval_mode",
    "embedding_model",
    "top_k",
    "rank",
    "final_score",
    "insufficient_evidence",
    "chunk_ids",
    "supporting_chunk_ids",
    "generation_latency_ms",
    "retrieval_latency_ms",
    "query",
    "query_transformation_applied",
    "reranking_applied",
    "conversation_id",
    "message_id",
    "scores",
    "run_id",
    "mode",
    "judge_id",
    "report_id",
}


def redact_chunk_preview(chunk: dict[str, Any]) -> dict[str, Any]:
    """Strip full chunk content; keep id, parent_id, score metadata."""
    safe: dict[str, Any] = {}
    for key in _SAFE_RAG_KEYS:
        if key in chunk:
            safe[key] = chunk[key]
    return safe


def redact_rag_prompt(payload: dict[str, Any]) -> dict[str, Any]:
    """Replace full prompt text with length-only metadata."""
    safe: dict[str, Any] = {}
    for key, value in payload.items():
        if key in _RAG_REDACTED_FIELDS:
            if isinstance(value, str):
                safe[f"{key}_len"] = len(value)
            continue
        if key in _SAFE_RAG_KEYS or isinstance(value, (int, float, bool)):
            if isinstance(value, str):
                safe[key] = redact_string(value)
            else:
                safe[key] = value
        elif isinstance(value, str):
            safe[key] = redact_string(value)
    return safe


def redact_snapshot_row(row: dict[str, Any]) -> dict[str, Any]:
    """Redact a snapshot row for safe storage — keep chunk IDs and scores only."""
    safe: dict[str, Any] = {}
    for key in {
        "snapshot_id",
        "conversation_id",
        "message_id",
        "trace_id",
        "chunk_ids",
        "scores",
        "created_at",
        "query",
    }:
        if key in row:
            if key == "query":
                safe[key] = redact_string(row[key])
            else:
                safe[key] = row[key]
    return safe


def redact_eval_report(report: dict[str, Any]) -> dict[str, Any]:
    """Redact eval report — suppress raw chunks, prompts, and full previews."""
    safe: dict[str, Any] = {}
    for key, value in report.items():
        if key in _RAG_REDACTED_FIELDS:
            continue
        if isinstance(value, dict):
            safe[key] = redact_dict(value, _RAG_REDACTED_FIELDS)
        elif isinstance(value, list):
            safe[key] = [
                redact_chunk_preview(item) if isinstance(item, dict) else item for item in value
            ]
        elif isinstance(value, str):
            safe[key] = redact_string(value)
        else:
            safe[key] = value
    return safe
