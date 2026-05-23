"""Unit tests for WidgetEmbedService origin policy."""

from app.services.widget_embed_service import WidgetEmbedService


class TestNormalizeOrigin:
    def test_strips_trailing_slash(self):
        assert WidgetEmbedService.normalize_origin("https://example.com/") == "https://example.com"

    def test_no_trailing_slash_unchanged(self):
        assert WidgetEmbedService.normalize_origin("https://example.com") == "https://example.com"

    def test_none_returns_none(self):
        assert WidgetEmbedService.normalize_origin(None) is None


class TestOriginAllowed:
    def test_exact_match(self):
        decision = WidgetEmbedService.origin_allowed(
            "https://example.com",
            ["https://example.com", "https://other.com"],
        )
        assert decision.allowed is True
        assert decision.reason == "allowed"
        assert decision.matched_origin == "https://example.com"

    def test_match_with_trailing_slash(self):
        decision = WidgetEmbedService.origin_allowed(
            "https://example.com/",
            ["https://example.com"],
        )
        assert decision.allowed is True

    def test_not_in_list(self):
        decision = WidgetEmbedService.origin_allowed(
            "https://evil.com",
            ["https://example.com"],
        )
        assert decision.allowed is False
        assert decision.reason == "origin_not_allowed"
        assert decision.matched_origin is None

    def test_empty_origin(self):
        decision = WidgetEmbedService.origin_allowed(
            None,
            ["https://example.com"],
        )
        assert decision.allowed is False
        assert decision.reason == "origin_not_provided"

    def test_empty_allowed_list(self):
        decision = WidgetEmbedService.origin_allowed(
            "https://example.com",
            [],
        )
        assert decision.allowed is False
        assert decision.reason == "origin_not_allowed"


class TestBuildCspFrameAncestors:
    def test_single_origin(self):
        csp = WidgetEmbedService.build_csp_frame_ancestors(["https://example.com"])
        assert csp == "frame-ancestors https://example.com"

    def test_multiple_origins(self):
        csp = WidgetEmbedService.build_csp_frame_ancestors(
            ["https://example.com", "https://other.com"]
        )
        assert csp == "frame-ancestors https://example.com https://other.com"

    def test_empty_list(self):
        csp = WidgetEmbedService.build_csp_frame_ancestors([])
        assert csp == "frame-ancestors 'none'"

    def test_strips_trailing_slashes(self):
        csp = WidgetEmbedService.build_csp_frame_ancestors(["https://example.com/"])
        assert csp == "frame-ancestors https://example.com"


class TestValidateWidgetForEmbed:
    def test_disabled_widget(self):
        decision = WidgetEmbedService.validate_widget_for_embed(
            is_enabled=False,
            allowed_origins=["https://example.com"],
            requested_origin="https://example.com",
            widget_id="wid-1",
        )
        assert decision.allowed is False
        assert decision.reason == "disabled"

    def test_enabled_and_origin_allowed(self):
        decision = WidgetEmbedService.validate_widget_for_embed(
            is_enabled=True,
            allowed_origins=["https://example.com"],
            requested_origin="https://example.com",
            widget_id="wid-1",
        )
        assert decision.allowed is True
        assert decision.reason == "allowed"

    def test_enabled_but_origin_blocked(self):
        decision = WidgetEmbedService.validate_widget_for_embed(
            is_enabled=True,
            allowed_origins=["https://example.com"],
            requested_origin="https://evil.com",
            widget_id="wid-1",
        )
        assert decision.allowed is False
        assert decision.reason == "origin_not_allowed"

    def test_enabled_but_no_origin(self):
        decision = WidgetEmbedService.validate_widget_for_embed(
            is_enabled=True,
            allowed_origins=["https://example.com"],
            requested_origin=None,
            widget_id="wid-1",
        )
        assert decision.allowed is False
        assert decision.reason == "origin_not_provided"
