"""Integration tests for refresh token flow."""

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.domain.auth import RefreshRequest
from app.domain.errors import TokenError


@pytest.fixture
def test_key_pair():
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa

    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()
    public_pem = (
        private_key.public_key()
        .public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        .decode()
    )
    return {"private_key": private_pem, "public_key": public_pem}


@pytest.fixture
def mock_session_factory():
    @asynccontextmanager
    async def factory():
        yield AsyncMock()

    return factory


def _make_settings(**kw):
    ms = MagicMock()
    ms.jwt_private_key = kw.get("private_key")
    ms.jwt_public_key = kw.get("public_key")
    ms.jwt_algorithm = "RS256"
    ms.jwt_access_token_expire_minutes = 30
    ms.jwt_refresh_token_expire_days = 7
    return ms


@pytest.fixture
def auth_service(test_key_pair, mock_session_factory):
    from app.infra.password_hasher import PasswordHasher
    from app.infra.token_signer import TokenSigner
    from app.repositories.token_session_repository import TokenSessionRepository
    from app.repositories.user_repository import UserRepository
    from app.services.auth_service import AuthService

    signer = TokenSigner(_make_settings(**test_key_pair))
    hasher = PasswordHasher()

    return AuthService(
        user_repo=UserRepository,
        token_repo=TokenSessionRepository,
        hasher=hasher,
        signer=signer,
        session_factory=mock_session_factory,
    )


class TestRefreshTokenFlow:
    async def test_refresh_succeeds_with_valid_token(self, auth_service):
        import datetime
        import hashlib

        svc = auth_service
        refresh_token = "valid-refresh-token-abc"
        token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()

        mock_session = MagicMock(
            id="ts1",
            user_id="u1",
            refresh_token_hash=token_hash,
            expires_at=datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=1),
            rotated_at=None,
            revoked_at=None,
            reuse_detected_at=None,
        )
        svc._token_repo_cls.get_by_refresh_hash = AsyncMock(return_value=mock_session)
        svc._token_repo_cls.rotate = AsyncMock()
        svc._user_repo_cls.get_by_id = AsyncMock(
            return_value=MagicMock(
                id="u1",
                email="u@t.com",
                role="user",
                is_active=True,
            )
        )

        result = await svc.refresh_token(RefreshRequest(refresh_token=refresh_token))
        assert result.access_token
        assert result.refresh_token

    async def test_refresh_fails_with_expired_token(self, auth_service):
        import datetime
        import hashlib

        svc = auth_service
        token_hash = hashlib.sha256("expired-token".encode()).hexdigest()

        mock_session = MagicMock(
            id="ts1",
            user_id="u1",
            refresh_token_hash=token_hash,
            expires_at=datetime.datetime.now(datetime.UTC) - datetime.timedelta(days=1),
            rotated_at=None,
            revoked_at=None,
            reuse_detected_at=None,
        )
        svc._token_repo_cls.get_by_refresh_hash = AsyncMock(return_value=mock_session)

        with pytest.raises(TokenError):
            await svc.refresh_token(RefreshRequest(refresh_token="expired-token"))

    async def test_refresh_fails_with_revoked_token(self, auth_service):
        import datetime
        import hashlib

        svc = auth_service
        token_hash = hashlib.sha256("revoked-token".encode()).hexdigest()

        mock_session = MagicMock(
            id="ts1",
            user_id="u1",
            refresh_token_hash=token_hash,
            expires_at=datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=1),
            rotated_at=None,
            revoked_at=datetime.datetime.now(datetime.UTC),
            reuse_detected_at=None,
        )
        svc._token_repo_cls.get_by_refresh_hash = AsyncMock(return_value=mock_session)

        with pytest.raises(TokenError):
            await svc.refresh_token(RefreshRequest(refresh_token="revoked-token"))

    async def test_refresh_fails_with_replayed_token(self, auth_service):
        import datetime
        import hashlib

        svc = auth_service
        token_hash = hashlib.sha256("rotated-token".encode()).hexdigest()

        mock_session = MagicMock(
            id="ts1",
            user_id="u1",
            refresh_token_hash=token_hash,
            expires_at=datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=1),
            rotated_at=datetime.datetime.now(datetime.UTC) - datetime.timedelta(hours=1),
            revoked_at=None,
            reuse_detected_at=None,
        )
        svc._token_repo_cls.get_by_refresh_hash = AsyncMock(return_value=mock_session)
        svc._token_repo_cls.mark_replay_detected = AsyncMock()

        with pytest.raises(TokenError):
            await svc.refresh_token(RefreshRequest(refresh_token="rotated-token"))

    async def test_refresh_fails_with_missing_session(self, auth_service):
        svc = auth_service
        svc._token_repo_cls.get_by_refresh_hash = AsyncMock(return_value=None)

        with pytest.raises(TokenError):
            await svc.refresh_token(RefreshRequest(refresh_token="unknown-token"))
