"""Phase 6 structured observability coverage tests."""

from __future__ import annotations

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock

import pytest


class FakeLogger:
    def __init__(self) -> None:
        self.bind_calls: list[dict] = []
        self.info_calls: list[tuple[str, dict]] = []
        self.warning_calls: list[tuple[str, dict]] = []

    def bind(self, **kwargs):
        self.bind_calls.append(kwargs)
        return self

    def info(self, event: str, **kwargs):
        self.info_calls.append((event, kwargs))

    def warning(self, event: str, **kwargs):
        self.warning_calls.append((event, kwargs))


def _make_log_factory(fake_logger: FakeLogger):
    return lambda: fake_logger


def _make_repo_cls(methods: dict):
    class Repo:
        def __init__(self, session):
            self._session = session

    for name, impl in methods.items():
        setattr(Repo, name, impl)
    return Repo


@pytest.fixture
def session_factory():
    @asynccontextmanager
    async def factory():
        yield AsyncMock()

    return factory


class TestObservabilityCoverage:
    async def test_auth_failure_logs_request_and_trace_without_password(self, monkeypatch, session_factory):
        from app.infra.password_hasher import PasswordHasher
        from app.services.auth_service import AuthService
        from app.domain.auth import UserLogin
        from app.domain.errors import AuthenticationError

        fake_logger = FakeLogger()
        monkeypatch.setattr("app.services.auth_service._log", _make_log_factory(fake_logger))

        hasher = PasswordHasher()
        user = MagicMock(
            id="u1",
            email="user@t.com",
            role="user",
            is_active=True,
            hashed_password=hasher.hash("correct-password"),
        )
        user_repo = _make_repo_cls({"get_by_email": AsyncMock(return_value=user)})
        token_repo = _make_repo_cls({})

        service = AuthService(
            user_repo=user_repo,
            token_repo=token_repo,
            hasher=hasher,
            signer=MagicMock(),
            session_factory=session_factory,
        )

        with pytest.raises(AuthenticationError):
            await service.login(
                UserLogin(email="user@t.com", password="wrong-password"),
                request_id="req-auth-1",
            )

        assert fake_logger.bind_calls
        bind = fake_logger.bind_calls[0]
        assert bind["request_id"] == "req-auth-1"
        assert bind["trace_id"]
        event, payload = fake_logger.warning_calls[-1]
        assert event == "auth_failed"
        assert payload["email"] == "user@t.com"
        assert "wrong-password" not in str(payload)

    async def test_role_change_logs_request_and_trace_without_invitation_token(self, monkeypatch, session_factory):
        from app.services.admin_invitation_service import AdminInvitationService

        fake_logger = FakeLogger()
        monkeypatch.setattr("app.services.admin_invitation_service._log", _make_log_factory(fake_logger))

        invitation = MagicMock(
            id="inv1",
            status="pending",
            token_hash="hashed-token",
            expires_at="2099-01-01T00:00:00+00:00",
        )
        invitation_repo = _make_repo_cls(
            {
                "get_by_token_hash": AsyncMock(return_value=invitation),
                "mark_accepted": AsyncMock(return_value=None),
            }
        )
        audit_repo = _make_repo_cls({"create": AsyncMock(return_value=MagicMock(id="a1"))})
        user_repo = _make_repo_cls(
            {
                "update_role": AsyncMock(return_value=None),
                "get_by_id": AsyncMock(
                    return_value=MagicMock(id="u1", email="u1@t.com", is_active=True)
                ),
            }
        )

        service = AdminInvitationService(
            invitation_repo=invitation_repo,
            audit_repo=audit_repo,
            user_repo=user_repo,
            session_factory=session_factory,
        )

        await service.accept_invitation(
            token="raw-secret-token",
            accepted_by_user_id="u1",
            request_id="req-role-1",
        )

        bind = fake_logger.bind_calls[0]
        assert bind["request_id"] == "req-role-1"
        assert bind["trace_id"]
        event, payload = fake_logger.info_calls[-1]
        assert event == "invitation_accepted"
        assert payload["invitation_id"] == "inv1"
        assert "raw-secret-token" not in str(payload)

    async def test_short_term_memory_write_logs_redaction_safely(self, monkeypatch):
        from app.domain.memory import ShortTermMemoryWrite
        from app.services.short_term_memory_service import ShortTermMemoryService

        fake_logger = FakeLogger()
        monkeypatch.setattr("app.services.short_term_memory_service._log", _make_log_factory(fake_logger))

        class Adapter:
            async def set(self, **kwargs):
                from datetime import datetime, timezone

                return datetime.now(timezone.utc)

        service = ShortTermMemoryService(adapter=Adapter(), ttl_seconds=30)
        await service.write_memory(
            user_id="u1",
            data=ShortTermMemoryWrite(
                conversation_id="c1",
                key="summary",
                value="password=supersecret",
            ),
            request_id="req-stm-1",
        )

        bind = fake_logger.bind_calls[0]
        assert bind["request_id"] == "req-stm-1"
        assert bind["trace_id"]
        event, payload = fake_logger.info_calls[-1]
        assert event == "short_term_memory_written"
        assert payload["redaction_applied"] is True
        assert "supersecret" not in str(payload)

    async def test_long_term_recall_logs_safely(self, monkeypatch, session_factory):
        from app.domain.memory import LongTermMemoryRecallRequest
        from app.services.long_term_memory_service import LongTermMemoryService

        fake_logger = FakeLogger()
        monkeypatch.setattr("app.services.long_term_memory_service._log", _make_log_factory(fake_logger))

        row = MagicMock(
            id="m1",
            owner_user_id="u1",
            memory_type="semantic",
            redacted_content="favorite editor=vim",
            extra_data={"audit_log_id": "a1"},
        )
        memory_repo = _make_repo_cls(
            {"search_same_user_semantic": AsyncMock(return_value=[row])}
        )

        class EmbeddingClient:
            async def embed(self, text: str):
                return [0.1, 0.2, 0.3]

        service = LongTermMemoryService(
            memory_repo=memory_repo,
            audit_repo=MagicMock(),
            embedding_client=EmbeddingClient(),
            session_factory=session_factory,
        )

        await service.recall_memory(
            user_id="u1",
            data=LongTermMemoryRecallRequest(
                query="favorite editor",
                conversation_id="later-c2",
                limit=5,
            ),
            request_id="req-recall-1",
        )

        bind = fake_logger.bind_calls[0]
        assert bind["request_id"] == "req-recall-1"
        assert bind["trace_id"]
        event, payload = fake_logger.info_calls[-1]
        assert event == "long_term_memory_recalled"
        assert payload["result_count"] == 1

    async def test_long_term_audit_failure_logs_without_raw_secret(self, monkeypatch, session_factory):
        from app.domain.errors import AuditError
        from app.domain.memory import WriteMemoryRequest
        from app.services.long_term_memory_service import LongTermMemoryService

        fake_logger = FakeLogger()
        monkeypatch.setattr("app.services.long_term_memory_service._log", _make_log_factory(fake_logger))

        memory_row = MagicMock(
            id="m1",
            memory_type="semantic",
            redacted_content="token=[REDACTED]",
            content_hash="hash1",
            extra_data={},
        )
        memory_repo = _make_repo_cls({"create": AsyncMock(return_value=memory_row)})

        class FailingAuditRepo:
            def __init__(self, session):
                self._session = session

            async def create(self, **kwargs):
                raise RuntimeError("audit backend down")

        class EmbeddingClient:
            async def embed(self, text: str):
                return [0.1, 0.2, 0.3]

        service = LongTermMemoryService(
            memory_repo=memory_repo,
            audit_repo=FailingAuditRepo,
            embedding_client=EmbeddingClient(),
            session_factory=session_factory,
        )

        with pytest.raises(AuditError):
            await service.write_memory(
                user_id="u1",
                data=WriteMemoryRequest(content="token=supersecret", memory_type="semantic"),
                request_id="req-audit-1",
            )

        bind = fake_logger.bind_calls[0]
        assert bind["request_id"] == "req-audit-1"
        assert bind["trace_id"]
        event, payload = fake_logger.warning_calls[-1]
        assert event == "long_term_memory_audit_failed"
        assert "supersecret" not in str(payload)
