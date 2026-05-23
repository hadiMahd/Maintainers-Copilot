"""Widget session service — anonymous session token issuance."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import structlog

_log = structlog.get_logger

_SESSION_TTL_MINUTES = 60


class WidgetSessionService:
    """Issue and validate widget-scoped anonymous session tokens."""

    @staticmethod
    def issue_token(
        *,
        widget_id: str,
        origin: str,
        request_id: str | None = None,
    ) -> dict:
        token = uuid.uuid4().hex
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=_SESSION_TTL_MINUTES)
        _log().info(
            "widget_session_token_issued",
            widget_id=widget_id,
            origin=origin,
            request_id=request_id,
        )
        return {
            "token": token,
            "expires_at": expires_at,
            "widget_id": widget_id,
        }

    @staticmethod
    def validate_token(
        *,
        token: str | None,
        widget_id: str,
        expected_origin: str | None,
        request_id: str | None = None,
    ) -> bool:
        if not token:
            _log().info(
                "widget_session_token_missing",
                widget_id=widget_id,
                request_id=request_id,
            )
            return False
        if not expected_origin:
            _log().info(
                "widget_session_token_no_origin",
                widget_id=widget_id,
                request_id=request_id,
            )
            return False
        _log().info(
            "widget_session_token_validated",
            widget_id=widget_id,
            request_id=request_id,
        )
        return True
