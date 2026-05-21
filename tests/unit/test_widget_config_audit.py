"""Unit tests for widget config audit row creation."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.domain.widget_config import WidgetConfigCreate, WidgetConfigUpdate
from app.services.widget_config_service import WidgetConfigService
from app.infra.orm_models import WidgetConfig as WC


@pytest.fixture
def mock_repo():
    repo = MagicMock()
    repo.create = AsyncMock()
    repo.get_by_id = AsyncMock()
    repo.update = AsyncMock()
    repo.delete = AsyncMock()
    return repo


@pytest.fixture
def mock_session_factory(mock_repo):
    session = MagicMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=None)
    session.commit = AsyncMock()

    factory = MagicMock()
    factory.return_value = session

    repo_cls = MagicMock(return_value=mock_repo)
    return factory, repo_cls, mock_repo


@pytest.fixture
def mock_audit_service():
    svc = MagicMock()
    svc.log_action = AsyncMock()
    return svc


def _make_row(id="cfg-1", name="Test", origins='["https://example.com"]', greeting="Hi", widget_id="wid-1"):
    return WC(
        id=id, widget_id=widget_id, name=name, allowed_origins=origins,
        theme="dark", welcome_message="Hello", greeting=greeting,
        position="bottom-right", enabled_tools='["classify_issue"]', is_enabled=True,
        created_by_user_id="u1", updated_by_user_id="u1",
        created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc),
    )


@pytest.mark.asyncio
async def test_create_logs_audit_row(mock_session_factory, mock_audit_service):
    factory, repo_cls, mock_repo = mock_session_factory
    row = _make_row()
    mock_repo.create.return_value = row

    svc = WidgetConfigService(repo_cls, factory)
    create = WidgetConfigCreate(name="Test", allowed_origins=["https://example.com"])
    await svc.create_config(create, "u1", audit_service=mock_audit_service)

    call = mock_audit_service.log_action.call_args
    assert call.kwargs["action"] == "widget_config.create"
    assert call.kwargs["target_type"] == "widget_config"
    assert call.kwargs["target_id"] == "wid-1"
    assert call.kwargs["actor_user_id"] == "u1"
    assert call.kwargs["extra_data"] == {"name": "Test"}


@pytest.mark.asyncio
async def test_update_logs_audit_row(mock_session_factory, mock_audit_service):
    factory, repo_cls, mock_repo = mock_session_factory
    row = _make_row()
    mock_repo.get_by_id.return_value = row

    def _update_side_effect(config_id, updated_by_user_id, **kwargs):
        for k, v in kwargs.items():
            if hasattr(row, k):
                setattr(row, k, v)
        row.updated_by_user_id = updated_by_user_id
        return row

    mock_repo.update = AsyncMock(side_effect=_update_side_effect)

    svc = WidgetConfigService(repo_cls, factory)
    update = WidgetConfigUpdate(theme="light")
    await svc.update_config("cfg-1", update, "u2", audit_service=mock_audit_service)

    call = mock_audit_service.log_action.call_args
    assert call.kwargs["action"] == "widget_config.update"
    assert call.kwargs["target_type"] == "widget_config"
    assert call.kwargs["target_id"] == "wid-1"
    assert call.kwargs["actor_user_id"] == "u2"
    assert "changed_fields" in call.kwargs["extra_data"]
    assert "theme" in call.kwargs["extra_data"]["changed_fields"]


@pytest.mark.asyncio
async def test_delete_logs_audit_row(mock_session_factory, mock_audit_service):
    factory, repo_cls, mock_repo = mock_session_factory
    row = _make_row()
    mock_repo.get_by_id.return_value = row
    mock_repo.delete = AsyncMock(return_value=row)

    svc = WidgetConfigService(repo_cls, factory)
    await svc.delete_config("cfg-1", "u3", audit_service=mock_audit_service)

    call = mock_audit_service.log_action.call_args
    assert call.kwargs["action"] == "widget_config.delete"
    assert call.kwargs["target_type"] == "widget_config"
    assert call.kwargs["target_id"] == "wid-1"
    assert call.kwargs["actor_user_id"] == "u3"
    assert call.kwargs["extra_data"] == {"name": "Test"}


@pytest.mark.asyncio
async def test_audit_redacts_secrets(mock_session_factory, mock_audit_service):
    """Audit extra_data must not contain raw config payloads or secrets."""
    factory, repo_cls, mock_repo = mock_session_factory
    row = _make_row()
    mock_repo.create.return_value = row

    svc = WidgetConfigService(repo_cls, factory)
    create = WidgetConfigCreate(
        name="Secret Widget",
        allowed_origins=["https://example.com"],
        greeting="Hello",
    )
    await svc.create_config(create, "u1", audit_service=mock_audit_service)

    call = mock_audit_service.log_action.call_args
    extra = call.kwargs["extra_data"]
    assert "allowed_origins" not in extra
    assert "greeting" not in extra
    assert "theme" not in extra
    assert "name" in extra
