"""Unit tests for WidgetConfigService — repository is mocked."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.domain.errors import WidgetConfigNotFoundError
from app.domain.widget_config import WidgetConfigCreate, WidgetConfigUpdate
from app.infra.orm_models import WidgetConfig as WC
from app.services.widget_config_service import WidgetConfigService


@pytest.fixture
def mock_repo():
    repo = MagicMock()
    repo.create = AsyncMock()
    repo.get_by_id = AsyncMock()
    repo.list_all = AsyncMock()
    repo.update = AsyncMock()
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


def _make_row(
    id="cfg-1",
    name="Test Widget",
    origins='["https://example.com"]',
    theme="dark",
    welcome="Hello",
    greeting="Hi there",
    widget_id="wid-1",
    position="bottom-right",
    enabled_tools='["classify_issue"]',
):
    row = WC(
        id=id,
        widget_id=widget_id,
        name=name,
        allowed_origins=origins,
        theme=theme,
        welcome_message=welcome,
        greeting=greeting,
        position=position,
        enabled_tools=enabled_tools,
        is_enabled=True,
        created_by_user_id="u1",
        updated_by_user_id="u1",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    return row


@pytest.fixture
def mock_audit_service():
    svc = MagicMock()
    svc.log_action = AsyncMock()
    return svc


@pytest.mark.asyncio
async def test_create_and_read_config(mock_session_factory, mock_audit_service):
    factory, repo_cls, mock_repo = mock_session_factory
    row = _make_row()
    mock_repo.create.return_value = row
    mock_repo.list_all.return_value = [row]

    svc = WidgetConfigService(repo_cls, factory)
    create = WidgetConfigCreate(
        name="Test Widget", allowed_origins=["https://example.com"], theme="dark"
    )
    result = await svc.create_config(create, "u1", audit_service=mock_audit_service)
    assert result.name == "Test Widget"
    assert result.theme == "dark"
    assert result.widget_id == "wid-1"
    assert mock_audit_service.log_action.call_count == 1
    assert mock_audit_service.log_action.call_args.kwargs["action"] == "widget_config.create"


@pytest.mark.asyncio
async def test_get_config_not_found(mock_session_factory):
    factory, repo_cls, mock_repo = mock_session_factory
    mock_repo.get_by_id.return_value = None

    svc = WidgetConfigService(repo_cls, factory)
    with pytest.raises(WidgetConfigNotFoundError):
        await svc.get_config("nonexistent")


@pytest.mark.asyncio
async def test_generate_embed_snippet(mock_session_factory):
    factory, repo_cls, mock_repo = mock_session_factory
    row = _make_row()
    mock_repo.get_by_id.return_value = row

    svc = WidgetConfigService(repo_cls, factory)
    snippet = await svc.generate_embed_snippet("cfg-1")
    assert snippet.widget_config_id == "cfg-1"
    assert "/widget.js" in snippet.snippet
    assert "wid-1" in snippet.snippet
    assert "data-widget-id=" in snippet.snippet


@pytest.mark.asyncio
async def test_delete_config_with_audit(mock_session_factory, mock_audit_service):
    factory, repo_cls, mock_repo = mock_session_factory
    row = _make_row()
    mock_repo.get_by_id.return_value = row
    mock_repo.delete = AsyncMock(return_value=row)

    svc = WidgetConfigService(repo_cls, factory)
    result = await svc.delete_config("cfg-1", "u1", audit_service=mock_audit_service)
    assert result.id == "cfg-1"
    assert mock_repo.delete.call_count == 1
    assert mock_audit_service.log_action.call_count == 1
    assert mock_audit_service.log_action.call_args.kwargs["action"] == "widget_config.delete"


@pytest.mark.asyncio
async def test_delete_config_not_found(mock_session_factory, mock_audit_service):
    factory, repo_cls, mock_repo = mock_session_factory
    mock_repo.get_by_id.return_value = None

    svc = WidgetConfigService(repo_cls, factory)
    with pytest.raises(WidgetConfigNotFoundError):
        await svc.delete_config("nonexistent", "u1", audit_service=mock_audit_service)
    assert mock_audit_service.log_action.call_count == 0


@pytest.mark.asyncio
async def test_update_config_with_audit(mock_session_factory, mock_audit_service):
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
    result = await svc.update_config("cfg-1", update, "u1", audit_service=mock_audit_service)
    assert result.theme == "light"
    assert mock_audit_service.log_action.call_count == 1
    assert mock_audit_service.log_action.call_args.kwargs["action"] == "widget_config.update"


@pytest.mark.asyncio
async def test_embed_snippet_uses_widget_id_and_data_widget_id(mock_session_factory):
    factory, repo_cls, mock_repo = mock_session_factory
    row = _make_row()
    mock_repo.get_by_id.return_value = row

    svc = WidgetConfigService(repo_cls, factory)
    snippet = await svc.generate_embed_snippet("cfg-1")
    assert "data-widget-id=" in snippet.snippet
    assert "wid-1" in snippet.snippet
    assert "/widget.js" in snippet.snippet
    assert "data-mc-widget-config" not in snippet.snippet


@pytest.mark.asyncio
async def test_read_config_includes_greeting_and_position(mock_session_factory):
    factory, repo_cls, mock_repo = mock_session_factory
    row = _make_row(greeting="Welcome!", position="bottom-left")
    mock_repo.get_by_id.return_value = row

    svc = WidgetConfigService(repo_cls, factory)
    result = await svc.get_config("cfg-1")
    assert result.greeting == "Welcome!"
    assert result.position == "bottom-left"
    assert result.widget_id == "wid-1"
