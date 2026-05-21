"""Integration test for admin create -> view -> update -> delete -> audit workflow."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timezone

import httpx
from fastapi import FastAPI

from app.api.routes.widget_configs import router as widget_configs_router
from app.api.dependencies.auth import get_current_user
from app.domain.auth import AuthContext


def _make_read_dict(id="cfg-1", name="Test", widget_id="wid-1", theme="dark"):
    return {
        "id": id,
        "widget_id": widget_id,
        "name": name,
        "allowed_origins": ["https://example.com"],
        "theme": theme,
        "greeting": "Hi",
        "welcome_message": "Hello",
        "position": "bottom-right",
        "enabled_tools": ["classify_issue"],
        "is_enabled": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


@pytest.mark.asyncio
async def test_create_view_update_delete_audit():
    """Full lifecycle: create -> view -> update -> delete -> verify audit."""
    audit_log = []

    async def mock_log_action(**kwargs):
        audit_log.append(kwargs)

    mock_audit = MagicMock()
    mock_audit.log_action = AsyncMock(side_effect=mock_log_action)

    created = MagicMock(
        model_dump=lambda mode=None: _make_read_dict(id="cfg-1", name="Integration Test", widget_id="wid-abc"),
    )
    updated = MagicMock(
        model_dump=lambda mode=None: _make_read_dict(id="cfg-1", name="Integration Test", widget_id="wid-abc", theme="light"),
    )
    deleted = MagicMock(
        id="cfg-1",
        widget_id="wid-abc",
        name="Integration Test",
    )

    async def _mock_create(data, created_by_user_id, audit_service, request_id=None):
        await audit_service.log_action(
            actor_user_id=created_by_user_id,
            action="widget_config.create",
            target_type="widget_config",
            target_id="wid-abc",
            extra_data={"name": "Integration Test"},
            request_id=request_id,
        )
        return created

    async def _mock_update(config_id, data, updated_by_user_id, audit_service, request_id=None):
        from app.domain.widget_config import WidgetConfigUpdate
        theme = "dark"
        if isinstance(data, WidgetConfigUpdate) and data.theme:
            theme = data.theme
        await audit_service.log_action(
            actor_user_id=updated_by_user_id,
            action="widget_config.update",
            target_type="widget_config",
            target_id="wid-abc",
            extra_data={"changed_fields": ["theme"]},
            request_id=request_id,
        )
        if theme == "light":
            return updated
        return created

    async def _mock_delete(config_id, deleted_by_user_id, audit_service, request_id=None):
        await audit_service.log_action(
            actor_user_id=deleted_by_user_id,
            action="widget_config.delete",
            target_type="widget_config",
            target_id="wid-abc",
            extra_data={"name": "Integration Test"},
            request_id=request_id,
        )
        return deleted

    mock_svc = MagicMock()
    mock_svc.list_configs = AsyncMock(return_value=[])
    mock_svc.create_config = AsyncMock(side_effect=_mock_create)
    mock_svc.get_config = AsyncMock(side_effect=lambda config_id, request_id=None: MagicMock(
        model_dump=lambda mode=None: _make_read_dict(id=config_id, name="Integration Test", widget_id="wid-abc"),
    ))
    mock_svc.update_config = AsyncMock(side_effect=_mock_update)
    mock_svc.delete_config = AsyncMock(side_effect=_mock_delete)

    import app.api.routes.widget_configs as wc_routes
    orig_get_svc = wc_routes._get_widget_config_service
    orig_get_audit = wc_routes._get_audit_service
    wc_routes._get_widget_config_service = lambda request: mock_svc
    wc_routes._get_audit_service = lambda request: mock_audit

    from app.api.error_handlers import register_error_handlers

    app = FastAPI()

    async def _fake_admin():
        return AuthContext(user_id="admin-1", email="admin@test.com", role="admin")

    app.dependency_overrides[get_current_user] = _fake_admin
    app.include_router(widget_configs_router, prefix="/admin/widget-configs")
    register_error_handlers(app)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
        # 1. Create
        resp = await ac.post(
            "/admin/widget-configs/",
            json={"name": "Integration Test", "allowed_origins": ["https://example.com"]},
        )
        assert resp.status_code == 201
        assert resp.json()["widget_id"] == "wid-abc"

        # 2. View (list)
        resp = await ac.get("/admin/widget-configs/")
        assert resp.status_code == 200

        # 3. Update
        resp = await ac.patch(
            "/admin/widget-configs/cfg-1",
            json={"theme": "light"},
        )
        assert resp.status_code == 200
        assert resp.json()["theme"] == "light"

        # 4. Delete
        resp = await ac.delete("/admin/widget-configs/cfg-1")
        assert resp.status_code == 200
        assert resp.json()["id"] == "cfg-1"

    # 5. Verify audit log
    assert len(audit_log) == 3
    actions = [entry["action"] for entry in audit_log]
    assert "widget_config.create" in actions
    assert "widget_config.update" in actions
    assert "widget_config.delete" in actions
