"""Contract tests for auth endpoints.

Covers: POST /auth/register, /auth/login, /auth/refresh, GET /users/me
"""

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.domain.auth import AuthContext, TokenPair, UserRead


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


def _patch_app_state(app, test_key_pair, mock_session_factory):
    settings = MagicMock()
    settings.jwt_private_key = test_key_pair["private_key"]
    settings.jwt_public_key = test_key_pair["public_key"]
    settings.jwt_algorithm = "RS256"
    settings.jwt_access_token_expire_minutes = 30
    settings.jwt_refresh_token_expire_days = 7
    settings.environment = "test"
    app.state.settings = settings

    import app.infra.database as db_mod
    db_mod.async_session_factory = mock_session_factory


@pytest.fixture
async def client(test_key_pair, mock_session_factory, monkeypatch):
    """Create app, patch state, return async client."""
    monkeypatch.delenv("VAULT_ADDR", raising=False)
    monkeypatch.delenv("VAULT_TOKEN", raising=False)
    monkeypatch.setenv("VAULT_ADDR", "http://fake-vault:8200")
    monkeypatch.setenv("VAULT_TOKEN", "fake-token")

    from app.core.application import create_app

    app = create_app()
    _patch_app_state(app, test_key_pair, mock_session_factory)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestAuthRegister:
    async def test_register_creates_user_returns_201(self, client, monkeypatch):
        user_read = UserRead(id="user1", email="new@test.com", role="user", is_active=True)
        mock_svc = AsyncMock()
        mock_svc.register = AsyncMock(return_value=user_read)

        import app.api.routes.auth as auth_mod
        monkeypatch.setattr(auth_mod, "_get_auth_service", lambda r: mock_svc)

        resp = await client.post("/auth/register", json={"email": "new@test.com", "password": "password123"})
        assert resp.status_code == 201
        data = resp.json()
        assert data["email"] == "new@test.com"
        assert data["role"] == "user"

    async def test_register_duplicate_returns_409(self, client, monkeypatch):
        from app.domain.errors import EmailAlreadyRegisteredError

        mock_svc = AsyncMock()
        mock_svc.register = AsyncMock(side_effect=EmailAlreadyRegisteredError("taken"))

        import app.api.routes.auth as auth_mod
        monkeypatch.setattr(auth_mod, "_get_auth_service", lambda r: mock_svc)

        resp = await client.post("/auth/register", json={"email": "exists@test.com", "password": "password123"})
        assert resp.status_code == 409

    async def test_register_invalid_input_returns_422(self, client):
        resp = await client.post("/auth/register", json={"email": "not-an-email", "password": "short"})
        assert resp.status_code == 422


class TestAuthLogin:
    async def test_login_valid_returns_200_with_tokens(self, client, monkeypatch):
        token_pair = TokenPair(
            access_token="access-abc", refresh_token="refresh-abc",
            token_type="bearer", expires_in=1800,
        )
        mock_svc = AsyncMock()
        mock_svc.login = AsyncMock(return_value=token_pair)

        import app.api.routes.auth as auth_mod
        monkeypatch.setattr(auth_mod, "_get_auth_service", lambda r: mock_svc)

        resp = await client.post("/auth/login", json={"email": "user@test.com", "password": "password123"})
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data

    async def test_login_invalid_credentials_returns_401(self, client, monkeypatch):
        from app.domain.errors import AuthenticationError

        mock_svc = AsyncMock()
        mock_svc.login = AsyncMock(side_effect=AuthenticationError("bad"))

        import app.api.routes.auth as auth_mod
        monkeypatch.setattr(auth_mod, "_get_auth_service", lambda r: mock_svc)

        resp = await client.post("/auth/login", json={"email": "user@test.com", "password": "wrong"})
        assert resp.status_code == 401


class TestAuthRefresh:
    async def test_refresh_valid_returns_200(self, client, monkeypatch):
        token_pair = TokenPair(
            access_token="new-access", refresh_token="new-refresh",
            token_type="bearer", expires_in=1800,
        )
        mock_svc = AsyncMock()
        mock_svc.refresh_token = AsyncMock(return_value=token_pair)

        import app.api.routes.auth as auth_mod
        monkeypatch.setattr(auth_mod, "_get_auth_service", lambda r: mock_svc)

        resp = await client.post("/auth/refresh", json={"refresh_token": "valid-refresh"})
        assert resp.status_code == 200

    async def test_refresh_invalid_returns_401(self, client, monkeypatch):
        from app.domain.errors import TokenError

        mock_svc = AsyncMock()
        mock_svc.refresh_token = AsyncMock(side_effect=TokenError("bad"))

        import app.api.routes.auth as auth_mod
        monkeypatch.setattr(auth_mod, "_get_auth_service", lambda r: mock_svc)

        resp = await client.post("/auth/refresh", json={"refresh_token": "bad"})
        assert resp.status_code == 401


class TestUsersMe:
    async def test_authenticated_returns_user(self, client, monkeypatch):
        auth_ctx = AuthContext(user_id="u1", email="u@t.com", role="user")

        async def mock_dep(request=None, credentials=None):
            return auth_ctx

        # Mock the user repo lookup that the /users/me route performs
        from app.repositories.user_repository import UserRepository
        mock_user = MagicMock(id="u1", email="u@t.com", role="user", is_active=True)
        UserRepository.get_by_id = AsyncMock(return_value=mock_user)

        fastapi_app = client._transport.app
        from app.api.dependencies.auth import get_current_user
        fastapi_app.dependency_overrides[get_current_user] = mock_dep

        resp = await client.get("/users/me")
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == "u@t.com"

        fastapi_app.dependency_overrides.clear()
