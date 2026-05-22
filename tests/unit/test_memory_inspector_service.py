"""Unit tests for MemoryInspectorService — repository is mocked."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.domain.memory_inspector import MemoryInspectionQuery
from app.infra.orm_models import LongTermMemory
from app.services.memory_inspector_service import MemoryInspectorService


@pytest.fixture
def mock_repo():
    repo = MagicMock()
    repo.list_by_user = AsyncMock()
    repo.list_all = AsyncMock()
    return repo


@pytest.fixture
def mock_session_factory(mock_repo):
    session = MagicMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=None)

    factory = MagicMock()
    factory.return_value = session

    repo_cls = MagicMock(return_value=mock_repo)
    return factory, repo_cls, mock_repo


def _make_row(owner="u1", mem_type="semantic", content="[REDACTED]", source="chat"):
    return LongTermMemory(
        id="mem-1",
        owner_user_id=owner,
        memory_type=mem_type,
        redacted_content=content,
        content_hash="abc",
        source=source,
        created_by_user_id="u1",
        created_at=datetime.now(timezone.utc),
    )


@pytest.mark.asyncio
async def test_user_sees_only_own_scope(mock_session_factory):
    factory, repo_cls, mock_repo = mock_session_factory
    mock_repo.list_by_user.return_value = [_make_row()]

    svc = MemoryInspectorService(repo_cls, factory)
    result = await svc.inspect_memory(MemoryInspectionQuery(limit=5), "u1", is_admin=False)
    assert result.scope == "own"
    assert len(result.items) == 1
    assert result.items[0].redacted_content == "[REDACTED]"


@pytest.mark.asyncio
async def test_admin_sees_admin_scope(mock_session_factory):
    factory, repo_cls, mock_repo = mock_session_factory
    mock_repo.list_all.return_value = [_make_row(), _make_row(owner="u2")]

    svc = MemoryInspectorService(repo_cls, factory)
    result = await svc.inspect_memory(MemoryInspectionQuery(limit=5), "admin-1", is_admin=True)
    assert result.scope == "admin"
    assert len(result.items) == 2


@pytest.mark.asyncio
async def test_pagination_returns_cursor(mock_session_factory):
    factory, repo_cls, mock_repo = mock_session_factory
    rows = [_make_row() for _ in range(3)]
    mock_repo.list_by_user.return_value = rows

    svc = MemoryInspectorService(repo_cls, factory)
    result = await svc.inspect_memory(MemoryInspectionQuery(limit=2), "u1", is_admin=False)
    assert len(result.items) == 2
    assert result.next_cursor is not None
