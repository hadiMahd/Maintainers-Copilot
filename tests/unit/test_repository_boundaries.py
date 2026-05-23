"""Verify repositories never call .commit() — services own transactions."""

from unittest.mock import MagicMock

from sqlalchemy.ext.asyncio import AsyncSession


def _assert_session_never_commits(repo_factory, session: MagicMock) -> None:
    """Create a repo from *repo_factory* and assert the session is never
    committed or rolled back during instantiation."""
    repo_factory(session)
    session.commit.assert_not_called()
    session.rollback.assert_not_called()


def _repo_instantiation_does_not_commit(repo_cls) -> None:
    session = MagicMock(spec=AsyncSession)
    repo = repo_cls(session)
    session.commit.assert_not_called()
    session.rollback.assert_not_called()
    assert repo is not None


class TestUserRepositoryNoCommit:
    def test_instantiation_does_not_commit(self):
        from app.repositories.user_repository import UserRepository

        _repo_instantiation_does_not_commit(UserRepository)


class TestTokenSessionRepositoryNoCommit:
    def test_instantiation_does_not_commit(self):
        from app.repositories.token_session_repository import TokenSessionRepository

        _repo_instantiation_does_not_commit(TokenSessionRepository)


class TestAdminInvitationRepositoryNoCommit:
    def test_instantiation_does_not_commit(self):
        from app.repositories.admin_invitation_repository import AdminInvitationRepository

        _repo_instantiation_does_not_commit(AdminInvitationRepository)


class TestMemoryRepositoryNoCommit:
    def test_instantiation_does_not_commit(self):
        from app.repositories.memory_repository import MemoryRepository

        _repo_instantiation_does_not_commit(MemoryRepository)


class TestAuditLogRepositoryNoCommit:
    def test_instantiation_does_not_commit(self):
        from app.repositories.audit_log_repository import AuditLogRepository

        _repo_instantiation_does_not_commit(AuditLogRepository)
