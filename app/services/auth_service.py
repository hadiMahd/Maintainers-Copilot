"""Authentication service.

Owns transaction boundaries for registration, login, refresh, and
current-user lookup.  Repositories never call ``.commit()``; this
service commits or rolls back once per workflow.
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from typing import Callable

import structlog

from app.domain.auth import AuthContext, RefreshRequest, TokenPair, UserCreate, UserLogin, UserRead
from app.domain.errors import AuthenticationError, EmailAlreadyRegisteredError, TokenError
from app.infra.password_hasher import PasswordHasher
from app.infra.token_signer import TokenSigner

_log = structlog.get_logger


class AuthService:
    """Authentication workflows.

    Each public method propagates ``request_id`` from middleware context
    and generates a per-operation ``trace_id``.  Structured log events
    carry both identifiers and never include raw passwords, tokens, or
    secret material.
    """

    def __init__(
        self,
        user_repo: type,
        token_repo: type,
        hasher: PasswordHasher,
        signer: TokenSigner,
        session_factory: Callable,
    ) -> None:
        self._user_repo_cls = user_repo
        self._token_repo_cls = token_repo
        self._hasher = hasher
        self._signer = signer
        self._session_factory = session_factory

    # ── trace helpers ──────────────────────────────────────────────

    @staticmethod
    def _trace(request_id: str | None = None) -> dict[str, str]:
        rid = request_id or "unknown"
        tid = uuid.uuid4().hex[:12]
        return {"request_id": rid, "trace_id": tid}

    # ── public API ─────────────────────────────────────────────────

    async def register(self, data: UserCreate, request_id: str | None = None) -> UserRead:
        t = self._trace(request_id)
        log = _log().bind(**t)
        async with self._session_factory() as session:
            try:
                repo = self._user_repo_cls(session)
                existing = await repo.get_by_email(data.email)
                if existing:
                    raise EmailAlreadyRegisteredError(f"Email {data.email} already registered")
                hashed = self._hasher.hash(data.password)
                user = await repo.create(data.email, hashed, role="user")
                await session.commit()
                log.info("user_registered", email=user.email)
                return UserRead(
                    id=user.id,
                    email=user.email,
                    role=user.role,
                    is_active=user.is_active,
                )
            except Exception:
                await session.rollback()
                log.warning("register_rollback")
                raise

    async def login(self, data: UserLogin, request_id: str | None = None) -> TokenPair:
        t = self._trace(request_id)
        log = _log().bind(**t)
        async with self._session_factory() as session:
            try:
                user_repo = self._user_repo_cls(session)
                user = await user_repo.get_by_email(data.email)
                if not user:
                    raise AuthenticationError("Invalid credentials")
                if not user.is_active:
                    raise AuthenticationError("Account is disabled")
                if not self._hasher.verify(user.hashed_password, data.password):
                    raise AuthenticationError("Invalid credentials")

                pair = self._signer.create_token_pair(user.id, user.email, user.role)
                token_repo = self._token_repo_cls(session)
                expires_at = datetime.now(timezone.utc) + timedelta(days=7)
                refresh_hash = hashlib.sha256(pair.refresh_token.encode()).hexdigest()
                await token_repo.create(user.id, refresh_hash, expires_at)
                await session.commit()
                log.info("user_logged_in")
                return pair
            except AuthenticationError:
                await session.rollback()
                log.warning("auth_failed", email=data.email)
                raise
            except Exception:
                await session.rollback()
                log.warning("login_rollback")
                raise

    async def refresh_token(self, data: RefreshRequest, request_id: str | None = None) -> TokenPair:
        t = self._trace(request_id)
        log = _log().bind(**t)
        async with self._session_factory() as session:
            try:
                token_repo = self._token_repo_cls(session)
                token_hash = hashlib.sha256(data.refresh_token.encode()).hexdigest()
                existing = await token_repo.get_by_refresh_hash(token_hash)
                if not existing:
                    raise TokenError("Refresh token not found")

                if existing.revoked_at is not None:
                    raise TokenError("Refresh token revoked")
                if existing.rotated_at is not None:
                    await token_repo.mark_replay_detected(existing.id)
                    await session.commit()
                    raise TokenError("Refresh token already used (replay detected)")

                now = datetime.now(timezone.utc)
                if existing.expires_at is not None and existing.expires_at < now:
                    raise TokenError("Refresh token expired")

                user_repo = self._user_repo_cls(session)
                user = await user_repo.get_by_id(existing.user_id)
                if not user:
                    raise TokenError("User not found")

                pair = self._signer.create_token_pair(user.id, user.email, user.role)
                expires_at = datetime.now(timezone.utc) + timedelta(days=7)
                new_hash = hashlib.sha256(pair.refresh_token.encode()).hexdigest()
                await token_repo.rotate(existing.id, new_hash, expires_at)
                await session.commit()
                log.info("token_rotated")
                return pair
            except (TokenError, AuthenticationError):
                await session.rollback()
                log.warning("token_refresh_failed")
                raise
            except Exception:
                await session.rollback()
                log.warning("refresh_rollback")
                raise

    async def get_current_user(self, user_id: str, request_id: str | None = None) -> AuthContext:
        t = self._trace(request_id)
        log = _log().bind(**t)
        async with self._session_factory() as session:
            repo = self._user_repo_cls(session)
            user = await repo.get_by_id(user_id)
            if not user:
                log.warning("current_user_lookup_failed", user_id=user_id)
                raise AuthenticationError("User not found")
            if not user.is_active:
                log.warning("current_user_disabled", user_id=user_id)
                raise AuthenticationError("Account is disabled")
            return AuthContext(
                user_id=user.id,
                email=user.email,
                role=user.role,
            )
