"""Unit tests for WidgetConfigService — repository is mocked."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.domain.errors import WidgetConfigNotFoundError
from app.domain.widget_config import WidgetConfigCreate, WidgetConfigUpdate, WidgetConfigRead
from app.services.widget_config_service import WidgetConfigService
from app.infra.orm_models import WidgetConfig as WC


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


def _make_row(id="cfg-1", name="Test Widget", origins='["https://example.com"]', theme="dark", welcome="Hello"):
    return WC(
        id=id, name=name, allowed_origins=origins,
        theme=theme, welcome_message=welcome, is_enabled=True,
        created_by_user_id="u1", updated_by_user_id="u1",
        created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc),
    )


@pytest.mark.asyncio
async def test_create_and_read_config(mock_session_factory):
    factory, repo_cls, mock_repo = mock_session_factory
    row = _make_row()
    mock_repo.create.return_value = row
    mock_repo.list_all.return_value = [row]

    svc = WidgetConfigService(repo_cls, factory)
    create = WidgetConfigCreate(name="Test Widget", allowed_origins=["https://example.com"], theme="dark")
    result = await svc.create_config(create, "u1")
    assert result.name == "Test Widget"
    assert result.theme == "dark"


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
    assert "loader.js" in snippet.snippet
    assert "cfg-1" in snippet.snippet
