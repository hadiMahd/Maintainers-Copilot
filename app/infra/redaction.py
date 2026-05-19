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
        if any(pat in key_lower for pat in ("secret", "password", "token", "api_key", "apikey", "credential")):
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