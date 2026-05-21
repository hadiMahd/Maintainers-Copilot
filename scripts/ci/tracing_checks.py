"""Tracing config validation helpers."""

import os
from typing import Any, Optional


def validate_tracing_config(settings: Optional[dict[str, Any]] = None) -> tuple[bool, list[str]]:
    """Validate tracing configuration. Returns (passed, error_messages)."""
    errors: list[str] = []
    langsmith_key = os.environ.get("LANGSMITH_API_KEY", "")
    langsmith_project = os.environ.get("LANGSMITH_PROJECT", "")
    langsmith_endpoint = os.environ.get("LANGSMITH_ENDPOINT", "")

    if not langsmith_key:
        errors.append("LANGSMITH_API_KEY not set")

    if langsmith_endpoint and not langsmith_project:
        errors.append("LANGSMITH_ENDPOINT set but LANGSMITH_PROJECT not set")

    if langsmith_key and "ls__" not in langsmith_key and len(langsmith_key) < 10:
        errors.append("LANGSMITH_API_KEY appears invalid (too short)")

    return len(errors) == 0, errors


def check_tracing_enabled_warning() -> tuple[bool, str]:
    """Check if tracing is enabled and warn if misconfigured."""
    passed, errors = validate_tracing_config()
    if passed:
        return True, "Tracing config: valid"
    return False, f"Tracing config: {', '.join(errors)}"
