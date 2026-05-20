"""Unit tests for AuthService, TokenSigner, and PasswordHasher."""

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.domain.auth import AuthContext, RefreshRequest, TokenPair, UserCreate, UserLogin, UserRead
from app.domain.errors import AuthenticationError, SigningKeyError, TokenError
from app.infra.password_hasher import PasswordHasher


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


class TestPasswordHasher:
    def test_hash_and_verify_success(self):
        hasher = PasswordHasher()
        h = hasher.hash("mypassword123")
        assert hasher.verify(h, "mypassword123")

    def test_verify_wrong_password(self):
        hasher = PasswordHasher()
        h = hasher.hash("correct")
        assert not hasher.verify(h, "wrong")

    def test_hash_is_deterministically_different(self):
        hasher = PasswordHasher()
        h1 = hasher.hash("same")
        h2 = hasher.hash("same")
        assert h1 != h2


class TestTokenSigner:
    def test_is_available(self, test_key_pair):
        from app.infra.token_signer import TokenSigner

        settings = _make_settings(**test_key_pair)
        signer = TokenSigner(settings)
        assert signer.is_available()

    def test_is_not_available_without_keys(self):
        from app.infra.token_signer import TokenSigner

        settings = _make_settings()
        signer = TokenSigner(settings)
        assert not signer.is_available()

    def test_create_access_token(self, test_key_pair):
        from app.infra.token_signer import TokenSigner

        signer = TokenSigner(_make_settings(**test_key_pair))
        token = signer.create_access_token("u1", "e@t.com", "user")
        assert isinstance(token, str)
        payload = signer.verify_token(token)
        assert payload["sub"] == "u1"
        assert payload["email"] == "e@t.com"

    def test_create_token_pair(self, test_key_pair):
        from app.infra.token_signer import TokenSigner

        signer = TokenSigner(_make_settings(**test_key_pair))
        pair = signer.create_token_pair("u1", "e@t.com", "user")
        assert pair.access_token
        assert pair.refresh_token
        assert pair.token_type == "bearer"

    def test_create_token_raises_without_keys(self):
        from app.infra.token_signer import TokenSigner

        signer = TokenSigner(_make_settings())
        with pytest.raises(SigningKeyError):
            signer.create_access_token("u1", "e@t.com", "user")

    def test_verify_token_raises_without_keys(self):
        from app.infra.token_signer import TokenSigner

        signer = TokenSigner(_make_settings())
        with pytest.raises(SigningKeyError):
            signer.verify_token("any-token")


class TestAuthService:
    async def test_register_creates_user(self, mock_session_factory):
        from app.repositories.user_repository import UserRepository
        from app.services.auth_service import AuthService
        from app.infra.token_signer import TokenSigner

        mock_user = MagicMock(id="u1", email="new@test.com", role="user", is_active=True)
        UserRepository.create = AsyncMock(return_value=mock_user)
        UserRepository.get_by_email = AsyncMock(return_value=None)

        svc = AuthService(
            user_repo=UserRepository,
            token_repo=MagicMock(),
            hasher=PasswordHasher(),
            signer=MagicMock(),
            session_factory=mock_session_factory,
        )

        user = await svc.register(UserCreate(email="new@test.com", password="pass1234"))
        assert user.email == "new@test.com"

    async def test_register_hashes_password(self, mock_session_factory):
        from app.repositories.user_repository import UserRepository
        from app.services.auth_service import AuthService

        mock_user = MagicMock(id="u2", email="x@t.com", role="user", is_active=True)
        UserRepository.create = AsyncMock(return_value=mock_user)
        UserRepository.get_by_email = AsyncMock(return_value=None)

        svc = AuthService(
            user_repo=UserRepository,
            token_repo=MagicMock(),
            hasher=PasswordHasher(),
            signer=MagicMock(),
            session_factory=mock_session_factory,
        )

        await svc.register(UserCreate(email="x@t.com", password="mysecret"))
        call_args = UserRepository.create.call_args
        hashed = call_args[0][1]
        assert not hashed.startswith("mysecret")
        assert hashed.startswith("$argon2id")

    async def test_login_returns_tokens(self, test_key_pair, mock_session_factory):
        from app.repositories.token_session_repository import TokenSessionRepository
        from app.repositories.user_repository import UserRepository
        from app.services.auth_service import AuthService
        from app.infra.token_signer import TokenSigner

        hasher = PasswordHasher()
        hashed = hasher.hash("correct")

        mock_user = MagicMock(
            id="u1", email="user@t.com", role="user", is_active=True,
            hashed_password=hashed,
        )
        UserRepository.get_by_email = AsyncMock(return_value=mock_user)
        TokenSessionRepository.create = AsyncMock()

        signer = TokenSigner(_make_settings(**test_key_pair))

        svc = AuthService(
            user_repo=UserRepository,
            token_repo=TokenSessionRepository,
            hasher=hasher,
            signer=signer,
            session_factory=mock_session_factory,
        )

        result = await svc.login(UserLogin(email="user@t.com", password="correct"))
        assert isinstance(result, TokenPair)
        assert result.access_token
        assert result.refresh_token

    async def test_login_bad_credentials(self, mock_session_factory):
        from app.repositories.user_repository import UserRepository
        from app.services.auth_service import AuthService

        hasher = PasswordHasher()
        hashed = hasher.hash("correct")

        mock_user = MagicMock(
            id="u1", email="user@t.com", role="user", is_active=True,
            hashed_password=hashed,
        )
        UserRepository.get_by_email = AsyncMock(return_value=mock_user)

        svc = AuthService(
            user_repo=UserRepository,
            token_repo=MagicMock(),
            hasher=hasher,
            signer=MagicMock(),
            session_factory=mock_session_factory,
        )

        with pytest.raises(AuthenticationError):
            await svc.login(UserLogin(email="user@t.com", password="wrong"))

    async def test_login_disabled_user(self, mock_session_factory):
        from app.repositories.user_repository import UserRepository
        from app.services.auth_service import AuthService

        hasher = PasswordHasher()
        hashed = hasher.hash("correct")

        mock_user = MagicMock(
            id="u1", email="user@t.com", role="user", is_active=False,
            hashed_password=hashed,
        )
        UserRepository.get_by_email = AsyncMock(return_value=mock_user)

        svc = AuthService(
            user_repo=UserRepository,
            token_repo=MagicMock(),
            hasher=hasher,
            signer=MagicMock(),
            session_factory=mock_session_factory,
        )

        with pytest.raises(AuthenticationError):
            await svc.login(UserLogin(email="user@t.com", password="correct"))

    async def test_login_user_not_found(self, mock_session_factory):
        from app.repositories.user_repository import UserRepository
        from app.services.auth_service import AuthService

        UserRepository.get_by_email = AsyncMock(return_value=None)

        svc = AuthService(
            user_repo=UserRepository,
            token_repo=MagicMock(),
            hasher=MagicMock(),
            signer=MagicMock(),
            session_factory=mock_session_factory,
        )

        with pytest.raises(AuthenticationError):
            await svc.login(UserLogin(email="nobody@t.com", password="x"))

    async def test_get_current_user(self, mock_session_factory):
        from app.repositories.user_repository import UserRepository
        from app.services.auth_service import AuthService

        mock_user = MagicMock(id="u1", email="e@t.com", role="user", is_active=True)
        UserRepository.get_by_id = AsyncMock(return_value=mock_user)

        svc = AuthService(
            user_repo=UserRepository,
            token_repo=MagicMock(),
            hasher=MagicMock(),
            signer=MagicMock(),
            session_factory=mock_session_factory,
        )

        ctx = await svc.get_current_user("u1")
        assert isinstance(ctx, AuthContext)
        assert ctx.user_id == "u1"
