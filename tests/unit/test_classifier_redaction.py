"""Tests for redaction before telemetry/artifact persistence."""

import pytest

from app.infra.redaction import (
    redact_dict,
    redact_model_card,
    redact_run_metadata,
    redact_string,
)


def test_redact_string_leaves_normal_text():
    """Normal text passes through redaction unchanged."""
    assert redact_string("hello world") == "hello world"


def test_redact_string_removes_sk_keys():
    """OpenAI-style sk- keys are replaced."""
    result = redact_string("key=sk-AbCdEfGhIjKlMnOpQrStUvWxYz0123456789")
    assert "sk-" not in result
    assert "[REDACTED]" in result


def test_redact_string_removes_explicit_secrets():
    """Explicit secret/key/password patterns are replaced."""
    result = redact_string("api_key=my-secret-value")
    assert "my-secret-value" not in result


def test_redact_dict_replaces_secret_keys():
    """Dict keys matching secret patterns have their values replaced."""
    data = {"api_key": "sk-abc123longkey", "name": "model-v1"}
    result = redact_dict(data)
    assert result["api_key"] == "[REDACTED]"
    assert result["name"] == "model-v1"


def test_redact_dict_truncates_long_text_fields():
    """Oversized text fields are truncated when listed in text_fields."""
    long_text = "x" * 1000
    data = {"description": long_text}
    result = redact_dict(data, text_fields={"description"})
    assert result["description"].endswith("...[TRUNCATED]")
    assert len(result["description"]) < 600


def test_redact_dict_recurses_nested_dicts():
    """Nested dicts containing secrets are recursively redacted."""
    data = {"outer": {"password": "hunter2", "safe": "value"}}
    result = redact_dict(data)
    assert result["outer"]["password"] == "[REDACTED]"
    assert result["outer"]["safe"] == "value"


def test_redact_model_card_marks_applied():
    """Model card redaction sets redaction_applied=True."""
    card = {
        "model_version": "0.1.0",
        "architecture_name": "distilbert-base-uncased",
        "api_key": "sk-should-be-redacted",
    }
    result = redact_model_card(card)
    assert result["redaction_applied"] is True
    assert result["api_key"] == "[REDACTED]"


def test_redact_run_metadata_redacts_uris():
    """Run metadata with URIs containing secrets is redacted."""
    metadata = {
        "run_id": "abc123",
        "tracking_uri": "http://mlflow:5000",
        "token": "secret-value",
    }
    result = redact_run_metadata(metadata)
    assert result["run_id"] == "abc123"
    assert result["token"] == "[REDACTED]"


def test_redact_dict_handles_lists():
    """Lists inside dicts are recursively processed."""
    data = {"items": [{"password": "secret"}, {"name": "safe"}]}
    result = redact_dict(data)
    assert result["items"][0]["password"] == "[REDACTED]"
    assert result["items"][1]["name"] == "safe"