"""Unit tests for memory-specific redaction helpers."""


class TestMemoryRedaction:
    def test_short_term_memory_redacts_secret_like_values(self):
        from app.infra.redaction import redact_short_term_memory_value

        result = redact_short_term_memory_value(
            "api_key=sk-abcdefghijklmnopqrstuvwxyz password=supersecret",
        )

        assert "supersecret" not in result
        assert "sk-abcdefghijklmnopqrstuvwxyz" not in result
        assert result.count("[REDACTED]") >= 1

    def test_short_term_memory_leaves_safe_text_unchanged(self):
        from app.infra.redaction import redact_short_term_memory_value

        value = "short-term note about triage"
        assert redact_short_term_memory_value(value) == value
