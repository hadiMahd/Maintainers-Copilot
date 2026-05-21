"""Unit tests for WidgetSessionService."""

from datetime import datetime, timedelta, timezone

import pytest

from app.domain.errors import WidgetSessionError
from app.services.widget_session_service import WidgetSessionService


class TestIssueToken:
    def test_returns_token_with_expected_fields(self):
        result = WidgetSessionService.issue_token(
            widget_id="wid-1",
            origin="https://example.com",
        )
        assert "token" in result
        assert "expires_at" in result
        assert "widget_id" in result
        assert result["widget_id"] == "wid-1"

    def test_token_is_hex_string(self):
        result = WidgetSessionService.issue_token(
            widget_id="wid-1",
            origin="https://example.com",
        )
        assert isinstance(result["token"], str)
        assert all(c in "0123456789abcdef" for c in result["token"])

    def test_token_length(self):
        result = WidgetSessionService.issue_token(
            widget_id="wid-1",
            origin="https://example.com",
        )
        # UUID4 hex = 32 chars
        assert len(result["token"]) == 32

    def test_expires_in_future(self):
        result = WidgetSessionService.issue_token(
            widget_id="wid-1",
            origin="https://example.com",
        )
        now = datetime.now(timezone.utc)
        assert result["expires_at"] > now
        # Should be ~60 minutes from now
        assert result["expires_at"] < now + timedelta(minutes=61)

    def test_unique_tokens(self):
        r1 = WidgetSessionService.issue_token(
            widget_id="wid-1",
            origin="https://example.com",
        )
        r2 = WidgetSessionService.issue_token(
            widget_id="wid-1",
            origin="https://example.com",
        )
        assert r1["token"] != r2["token"]


class TestValidateToken:
    def test_valid_token_returns_true(self):
        assert WidgetSessionService.validate_token(
            token="abc123",
            widget_id="wid-1",
            expected_origin="https://example.com",
        ) is True

    def test_missing_token_returns_false(self):
        assert WidgetSessionService.validate_token(
            token=None,
            widget_id="wid-1",
            expected_origin="https://example.com",
        ) is False

    def test_empty_token_returns_false(self):
        assert WidgetSessionService.validate_token(
            token="",
            widget_id="wid-1",
            expected_origin="https://example.com",
        ) is False

    def test_missing_origin_returns_false(self):
        assert WidgetSessionService.validate_token(
            token="abc123",
            widget_id="wid-1",
            expected_origin=None,
        ) is False
