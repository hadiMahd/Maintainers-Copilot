"""Integration tests for admin invitation flow."""

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.fixture
def mock_session_factory():
    @asynccontextmanager
    async def factory():
        yield AsyncMock()

    return factory


def _make_mock_repo_cls(method_returns: dict):
    from unittest.mock import AsyncMock

    class MockRepo:
        def __init__(self, session):
            self._session = session

    for name, return_value in method_returns.items():
        setattr(MockRepo, name, AsyncMock(return_value=return_value))
    return MockRepo


class TestAdminInvitationFlow:
    async def test_create_and_accept_invitation_creates_audit_rows(self, mock_session_factory):
        from app.services.admin_invitation_service import AdminInvitationService

        mock_inv = MagicMock(
            id="inv1",
            invitee_email="target@t.com",
            status="pending",
            created_by_user_id="admin1",
            token_hash="inv-hash-123",
            expires_at="2027-01-01T00:00:00Z",
        )
        audit_create_mock = AsyncMock()

        InvitationRepo = _make_mock_repo_cls(
            {
                "get_by_email_and_status": None,
                "create": mock_inv,
            }
        )
        AuditRepo = _make_mock_repo_cls({})
        AuditRepo.create = audit_create_mock
        UserRepo = _make_mock_repo_cls({"get_by_email": None})

        svc = AdminInvitationService(
            invitation_repo=InvitationRepo,
            audit_repo=AuditRepo,
            user_repo=UserRepo,
            session_factory=mock_session_factory,
        )

        result = await svc.create_invitation(
            invitee_email="target@t.com",
            created_by_user_id="admin1",
        )
        assert result.invitee_email == "target@t.com"

        call_args_list = audit_create_mock.call_args_list
        assert len(call_args_list) == 1
        assert call_args_list[0].kwargs["action"] == "admin_invitation.create"

    async def test_accept_invitation_records_role_change_audit(self, mock_session_factory):
        from app.services.admin_invitation_service import AdminInvitationService

        mock_inv = MagicMock(
            id="inv1",
            invitee_email="target@t.com",
            token_hash="inv-hash-456",
            status="pending",
            created_by_user_id="admin1",
            expires_at="2027-01-01T00:00:00Z",
            accepted_at=None,
            accepted_by_user_id=None,
        )
        mock_user = MagicMock(id="target1", email="target@t.com", role="admin", is_active=True)
        audit_create_mock = AsyncMock()

        InvitationRepo = _make_mock_repo_cls(
            {
                "get_by_token_hash": mock_inv,
                "mark_accepted": None,
            }
        )
        AuditRepo = _make_mock_repo_cls({})
        AuditRepo.create = audit_create_mock
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

        role_change_calls = [
            c for c in audit_create_mock.call_args_list if c.kwargs.get("action") == "role.change"
        ]
        assert len(role_change_calls) >= 1
