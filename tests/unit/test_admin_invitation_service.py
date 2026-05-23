"""Unit tests for admin invitation service."""

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.domain.errors import InvitationError


@pytest.fixture
def mock_session_factory():
    @asynccontextmanager
    async def factory():
        yield AsyncMock()

    return factory


def _make_mock_repo_cls(method_returns: dict):
    """Create a mock repo class that returns an AsyncMock instance with
    the given method return values preset."""
    from unittest.mock import AsyncMock

    class MockRepo:
        def __init__(self, session):
            self._session = session

    for name, return_value in method_returns.items():
        setattr(MockRepo, name, AsyncMock(return_value=return_value))
    return MockRepo


class TestAdminInvitationService:
    async def test_create_invitation_sets_expiry(self, mock_session_factory):
        from app.services.admin_invitation_service import AdminInvitationService

        mock_inv = MagicMock(
            id="inv1",
            invitee_email="new@t.com",
            status="pending",
            created_by_user_id="admin1",
            expires_at="2026-06-01T00:00:00Z",
            token_hash="hash123",
        )

        InvitationRepo = _make_mock_repo_cls(
            {
                "get_by_email_and_status": None,
                "create": mock_inv,
            }
        )
        AuditRepo = _make_mock_repo_cls({"create": None})
        UserRepo = _make_mock_repo_cls({})

        svc = AdminInvitationService(
            invitation_repo=InvitationRepo,
            audit_repo=AuditRepo,
            user_repo=UserRepo,
            session_factory=mock_session_factory,
        )

        result = await svc.create_invitation(
            invitee_email="new@t.com",
            created_by_user_id="admin1",
        )
        assert result.invitee_email == "new@t.com"
        assert result.status == "pending"

    async def test_accept_invitation_grants_admin(self, mock_session_factory):
        from app.services.admin_invitation_service import AdminInvitationService

        mock_inv = MagicMock(
            id="inv1",
            invitee_email="target@t.com",
            token_hash="hash123",
            status="pending",
            created_by_user_id="admin1",
            expires_at="2027-01-01T00:00:00Z",
            accepted_at=None,
            accepted_by_user_id=None,
        )
        mock_user = MagicMock(id="target1", email="target@t.com", role="admin", is_active=True)

        InvitationRepo = _make_mock_repo_cls(
            {
                "get_by_token_hash": mock_inv,
                "mark_accepted": None,
            }
        )
        AuditRepo = _make_mock_repo_cls({"create": None})
        UserRepo = _make_mock_repo_cls(
            {
                "update_role": None,
                "get_by_id": mock_user,
            }
        )

        svc = AdminInvitationService(
            invitation_repo=InvitationRepo,
            audit_repo=AuditRepo,
            user_repo=UserRepo,
            session_factory=mock_session_factory,
        )

        result = await svc.accept_invitation(token="valid-token", accepted_by_user_id="target1")
        assert result.role == "admin"

    async def test_accept_expired_invitation_raises(self, mock_session_factory):
        import datetime

        from app.services.admin_invitation_service import AdminInvitationService

        mock_inv = MagicMock(
            id="inv1",
            invitee_email="target@t.com",
            token_hash="hash123",
            status="pending",
            expires_at=datetime.datetime.now(datetime.UTC) - datetime.timedelta(hours=1),
        )

        InvitationRepo = _make_mock_repo_cls(
            {
                "get_by_token_hash": mock_inv,
            }
        )
        AuditRepo = _make_mock_repo_cls({})
        UserRepo = _make_mock_repo_cls({})

        svc = AdminInvitationService(
            invitation_repo=InvitationRepo,
            audit_repo=AuditRepo,
            user_repo=UserRepo,
            session_factory=mock_session_factory,
        )

        with pytest.raises(InvitationError):
            await svc.accept_invitation(token="expired-token", accepted_by_user_id="u1")

    async def test_accept_already_accepted_invitation_raises(self, mock_session_factory):
        from app.services.admin_invitation_service import AdminInvitationService

        mock_inv = MagicMock(
            id="inv1",
            status="accepted",
            token_hash="hash123",
            expires_at="2027-01-01T00:00:00Z",
        )

        InvitationRepo = _make_mock_repo_cls(
            {
                "get_by_token_hash": mock_inv,
            }
        )
        AuditRepo = _make_mock_repo_cls({})
        UserRepo = _make_mock_repo_cls({})

        svc = AdminInvitationService(
            invitation_repo=InvitationRepo,
            audit_repo=AuditRepo,
            user_repo=UserRepo,
            session_factory=mock_session_factory,
        )

        with pytest.raises(InvitationError):
            await svc.accept_invitation(token="used-token", accepted_by_user_id="u1")

    async def test_accept_revoked_invitation_raises(self, mock_session_factory):
        from app.services.admin_invitation_service import AdminInvitationService

        mock_inv = MagicMock(
            id="inv1",
            status="revoked",
            token_hash="hash123",
            expires_at="2027-01-01T00:00:00Z",
        )

        InvitationRepo = _make_mock_repo_cls(
            {
                "get_by_token_hash": mock_inv,
            }
        )
        AuditRepo = _make_mock_repo_cls({})
        UserRepo = _make_mock_repo_cls({})

        svc = AdminInvitationService(
            invitation_repo=InvitationRepo,
            audit_repo=AuditRepo,
            user_repo=UserRepo,
            session_factory=mock_session_factory,
        )

        with pytest.raises(InvitationError):
            await svc.accept_invitation(token="revoked-token", accepted_by_user_id="u1")
