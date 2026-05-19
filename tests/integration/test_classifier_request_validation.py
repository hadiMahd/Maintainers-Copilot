"""Integration tests for classifier request validation and oversized input handling."""

import pytest
from pydantic import ValidationError

from app.domain.classifier import ClassifierRequest


class TestOversizedInput:
    """Tests for classifier request size limits."""

    def test_title_at_max_length(self):
        """Title at exactly 512 characters is accepted."""
        req = ClassifierRequest(title="x" * 512)
        assert len(req.title) == 512

    def test_title_over_max_length(self):
        """Title over 512 characters is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ClassifierRequest(title="x" * 513)
        assert "512" in str(exc_info.value).lower() or "max_length" in str(exc_info.value).lower()

    def test_body_at_max_length(self):
        """Body at exactly 16000 characters is accepted."""
        req = ClassifierRequest(body="x" * 16000)
        assert len(req.body) == 16000

    def test_body_over_max_length(self):
        """Body over 16000 characters is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ClassifierRequest(body="x" * 16001)
        assert "16000" in str(exc_info.value).lower() or "max_length" in str(exc_info.value).lower()

    def test_comments_at_max_count(self):
        """Exactly 100 comments is accepted."""
        req = ClassifierRequest(comments=["comment"] * 100)
        assert len(req.comments) == 100

    def test_comments_over_max_count(self):
        """More than 100 comments is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ClassifierRequest(comments=["comment"] * 101)
        assert "100" in str(exc_info.value).lower() or "max_length" in str(exc_info.value).lower()

    def test_comment_over_max_length(self):
        """Single comment over 4000 characters is rejected."""
        with pytest.raises(ValidationError):
            ClassifierRequest(comments=["x" * 4001])

    def test_empty_request_is_rejected(self):
        """Empty request is rejected by the schema."""
        with pytest.raises(ValidationError):
            ClassifierRequest(title=None, body=None, comments=None)

    def test_blank_comment_is_rejected(self):
        """Comments must contain non-empty text."""
        with pytest.raises(ValidationError):
            ClassifierRequest(comments=["   "])

    def test_validation_error_is_structured(self):
        """Validation error has structured fields, not a stack trace."""
        with pytest.raises(ValidationError) as exc_info:
            ClassifierRequest(title="x" * 513)
        error_msg = str(exc_info.value)
        assert "traceback" not in error_msg.lower()
        assert "stack" not in error_msg.lower()
