"""Integration tests for auth lifecycle with Vault key resolution."""

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.domain.errors import AuthenticationError


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
def auth_service_with_keys(test_key_pair, mock_session_factory):
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


class TestRegistrationLoginLifecycle:
    async def test_register_then_login(self, auth_service_with_keys):
        from app.domain.auth import UserCreate, UserLogin

        svc = auth_service_with_keys
        svc._user_repo_cls.get_by_email = AsyncMock(return_value=None)
        svc._user_repo_cls.create = AsyncMock(
            return_value=MagicMock(
                id="u1",
                email="life@test.com",
                role="user",
                is_active=True,
            )
        )

        user = await svc.register(UserCreate(email="life@test.com", password="pass1234"))
        assert user.email == "life@test.com"

        svc._user_repo_cls.get_by_email = AsyncMock(
            return_value=MagicMock(
                id="u1",
                email="life@test.com",
                role="user",
                is_active=True,
                hashed_password=svc._hasher.hash("pass1234"),
            )
        )
        svc._token_repo_cls.create = AsyncMock()

        token_pair = await svc.login(UserLogin(email="life@test.com", password="pass1234"))
        assert token_pair.access_token
        assert token_pair.refresh_token
        assert token_pair.token_type == "bearer"

    async def test_login_bad_password(self, auth_service_with_keys):
        from app.domain.auth import UserLogin

        svc = auth_service_with_keys
        svc._user_repo_cls.get_by_email = AsyncMock(
            return_value=MagicMock(
                id="u1",
                email="x@t.com",
                role="user",
                is_active=True,
                hashed_password=svc._hasher.hash("real-password"),
            )
        )

        with pytest.raises(AuthenticationError):
            await svc.login(UserLogin(email="x@t.com", password="wrong-password"))

    async def test_register_duplicate_email(self, auth_service_with_keys):
        from app.domain.auth import UserCreate
        from app.domain.errors import EmailAlreadyRegisteredError
        from app.repositories.user_repository import UserRepository

        svc = auth_service_with_keys
        UserRepository.get_by_email = AsyncMock(return_value=MagicMock())

        with pytest.raises(EmailAlreadyRegisteredError):
            await svc.register(UserCreate(email="exists@test.com", password="pass1234"))

    async def test_signing_key_unavailable(self):
        from app.domain.errors import SigningKeyError
        from app.infra.token_signer import TokenSigner

        signer = TokenSigner(_make_settings())
        with pytest.raises(SigningKeyError):
            signer.create_access_token("u1", "e@t.com", "user")
