"""RS256 JWT token signing adapter.

Resolves the RS256 private/public key pair from ``AppSettings`` (populated
by lifespan from Vault).  Access tokens carry user identity claims;
refresh tokens are opaque random strings stored hashed in the database.
"""

from __future__ import annotations

import datetime
import secrets
import time
import uuid

import jwt

from app.core.config import AppSettings
from app.domain.auth import TokenPair
from app.domain.errors import SigningKeyError


class TokenSigner:
    """Create and verify RS256 JWT access tokens, and generate opaque
    refresh tokens."""

    def __init__(self, settings: AppSettings) -> None:
        self._algorithm = settings.jwt_algorithm
        self._access_expire_minutes = settings.jwt_access_token_expire_minutes
        self._refresh_expire_days = settings.jwt_refresh_token_expire_days
        self._private_key = settings.jwt_private_key
        self._public_key = settings.jwt_public_key

    def is_available(self) -> bool:
        return self._private_key is not None and self._public_key is not None

    def _ensure_key(self) -> None:
        if not self.is_available():
            raise SigningKeyError("JWT signing key is not available")

    def create_access_token(self, user_id: str, email: str, role: str) -> str:
        """Create a signed RS256 JWT access token."""
        self._ensure_key()
        now = int(time.time())
        payload = {
            "sub": user_id,
            "email": email,
            "role": role,
            "iat": now,
            "exp": now + self._access_expire_minutes * 60,
            "jti": uuid.uuid4().hex,
        }
        return jwt.encode(  # type: ignore[no-any-return]
            payload, self._private_key, algorithm=self._algorithm
        )

    def create_refresh_token(self) -> str:
        """Generate an opaque refresh token."""
        return secrets.token_urlsafe(64)

    def create_token_pair(self, user_id: str, email: str, role: str) -> TokenPair:
        """Create access + refresh token pair."""
        return TokenPair(
            access_token=self.create_access_token(user_id, email, role),
            refresh_token=self.create_refresh_token(),
            expires_in=self._access_expire_minutes * 60,
        )

    def verify_token(self, token: str) -> dict:
        """Verify an access token and return its payload.

        Raises ``jwt.PyJWTError`` on any validation failure.
        """
        self._ensure_key()
        payload = jwt.decode(
            token,
            self._public_key,
            algorithms=[self._algorithm],
            options={"require": ["exp", "sub"]},
        )
        return payload  # type: ignore[no-any-return]
