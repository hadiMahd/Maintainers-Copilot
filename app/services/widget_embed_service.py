"""Widget embed service — origin validation, public config shaping, CSP headers."""

from __future__ import annotations

import structlog

from app.domain.errors import WidgetEmbedError

_log = structlog.get_logger


class OriginDecision:
    def __init__(
        self,
        allowed: bool,
        reason: str,
        matched_origin: str | None = None,
    ) -> None:
        self.allowed = allowed
        self.reason = reason
        self.matched_origin = matched_origin


class WidgetEmbedService:
    """Origin validation and public config shaping for widget embed."""

    @staticmethod
    def normalize_origin(origin: str | None) -> str | None:
        if origin is None:
            return None
        return origin.rstrip("/")

    @staticmethod
    def origin_allowed(
        requested_origin: str | None,
        allowed_origins: list[str],
    ) -> OriginDecision:
        if not requested_origin:
            return OriginDecision(
                allowed=False,
                reason="origin_not_provided",
            )
        normalized = WidgetEmbedService.normalize_origin(requested_origin)
        for allowed in allowed_origins:
            if WidgetEmbedService.normalize_origin(allowed) == normalized:
                return OriginDecision(
                    allowed=True,
                    reason="allowed",
                    matched_origin=allowed,
                )
        return OriginDecision(
            allowed=False,
            reason="origin_not_allowed",
        )

    @staticmethod
    def build_csp_frame_ancestors(allowed_origins: list[str]) -> str:
        origins = " ".join(
            WidgetEmbedService.normalize_origin(o)
            for o in allowed_origins
            if WidgetEmbedService.normalize_origin(o)
        )
        if origins:
            return f"frame-ancestors {origins}"
        return "frame-ancestors 'none'"

    @staticmethod
    def to_public_config(
        widget_id: str,
        theme: str,
        greeting: str | None,
        position: str,
        enabled_tools: list[str],
    ) -> dict:
        return {
            "widget_id": widget_id,
            "theme": theme,
            "greeting": greeting,
            "position": position,
            "enabled_tools": enabled_tools,
        }

    @staticmethod
    def validate_widget_for_embed(
        *,
        is_enabled: bool,
        allowed_origins: list[str],
        requested_origin: str | None,
        widget_id: str,
        request_id: str | None = None,
    ) -> OriginDecision:
        if not is_enabled:
            _log().info(
                "widget_embed_disabled",
                widget_id=widget_id,
                request_id=request_id,
            )
            return OriginDecision(
                allowed=False,
                reason="disabled",
            )
        decision = WidgetEmbedService.origin_allowed(
            requested_origin,
            allowed_origins,
        )
        if not decision.allowed:
            _log().info(
                "widget_embed_origin_blocked",
                widget_id=widget_id,
                requested_origin=requested_origin,
                reason=decision.reason,
                request_id=request_id,
            )
        return decision
