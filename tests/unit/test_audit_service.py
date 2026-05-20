"""Unit tests for audit service helpers."""


class TestAuditService:
    def test_memory_write_metadata_is_safe_and_bounded(self):
        from app.services.audit_service import AuditService

        metadata = AuditService.build_memory_write_metadata(
            memory_type="semantic",
            content_hash="abc123",
            redacted_content="password=[REDACTED]",
            redaction_applied=True,
            source="write_memory",
        )

        assert metadata["memory_type"] == "semantic"
        assert metadata["content_hash"] == "abc123"
        assert metadata["redaction_applied"] is True
        assert metadata["source"] == "write_memory"
        assert metadata["content_length"] == len("password=[REDACTED]")
        assert "password=[REDACTED]" not in str(metadata)

    def test_memory_write_action_constant(self):
        from app.services.audit_service import MEMORY_WRITE_ACTION

        assert MEMORY_WRITE_ACTION == "memory.write"
