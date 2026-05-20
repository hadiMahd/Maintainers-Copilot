"""Unit tests for authorization service."""

from unittest.mock import MagicMock

import pytest

from app.domain.auth import AuthContext
from app.domain.errors import AuthorizationError


class TestRequireAdmin:
    async def test_admin_passes(self, monkeypatch):
        from app.api.dependencies.authorization import require_admin

        request = MagicMock()
        request.state.request_id = "req-1"

        admin_ctx = AuthContext(user_id="admin1", email="a@t.com", role="admin")
        ctx = await require_admin(request=request, current_user=admin_ctx)
        assert ctx.role == "admin"

    async def test_regular_user_rejected(self, monkeypatch):
        from app.api.dependencies.authorization import require_admin

        request = MagicMock()
        request.state.request_id = "req-2"

        user_ctx = AuthContext(user_id="u1", email="u@t.com", role="user")
        with pytest.raises(AuthorizationError):
            await require_admin(request=request, current_user=user_ctx)
