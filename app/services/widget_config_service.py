"""Widget configuration service.

Owns transaction boundaries for widget config CRUD and embed snippet
generation.  Repositories never call ``.commit()``; this service commits
or rolls back once per workflow.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Callable

import structlog

from app.domain.errors import WidgetConfigNotFoundError
from app.domain.widget_config import EmbedSnippetRead, WidgetConfigCreate, WidgetConfigRead, WidgetConfigUpdate
from app.infra.orm_models import WidgetConfig

_log = structlog.get_logger


class WidgetConfigService:
    """Widget configuration CRUD and snippet generation."""

    def __init__(
        self,
        widget_config_repo: type,
        session_factory: Callable,
    ) -> None:
        self._repo_cls = widget_config_repo
        self._session_factory = session_factory

    @staticmethod
    def _trace(request_id: str | None = None) -> dict[str, str]:
        rid = request_id or "unknown"
        tid = uuid.uuid4().hex[:12]
        return {"request_id": rid, "trace_id": tid}

    async def create_config(
        self,
        data: WidgetConfigCreate,
        created_by_user_id: str,
        request_id: str | None = None,
    ) -> WidgetConfigRead:
        trace = self._trace(request_id)
        _log().info("widget_config.create", **trace)
        async with self._session_factory() as session:
            repo = self._repo_cls(session)
            row = await repo.create(
                name=data.name,
                allowed_origins=data.allowed_origins,
                theme=data.theme,
                welcome_message=data.welcome_message,
                is_enabled=data.is_enabled,
                created_by_user_id=created_by_user_id,
            )
            await session.commit()
            return self._to_read(row)

    async def list_configs(
        self,
        request_id: str | None = None,
    ) -> list[WidgetConfigRead]:
        async with self._session_factory() as session:
            repo = self._repo_cls(session)
            rows = await repo.list_all()
            return [self._to_read(row) for row in rows]

    async def get_config(
        self,
        config_id: str,
        request_id: str | None = None,
    ) -> WidgetConfigRead:
        trace = self._trace(request_id)
        async with self._session_factory() as session:
            repo = self._repo_cls(session)
            row = await repo.get_by_id(config_id)
            if row is None:
                raise WidgetConfigNotFoundError(
                    f"Widget configuration {config_id} not found",
                    details={"config_id": config_id, "request_id": request_id},
                    trace_id=trace["trace_id"],
                )
            return self._to_read(row)

    async def update_config(
        self,
        config_id: str,
        data: WidgetConfigUpdate,
        updated_by_user_id: str,
        request_id: str | None = None,
    ) -> WidgetConfigRead:
        trace = self._trace(request_id)
        _log().info("widget_config.update", **trace)
        async with self._session_factory() as session:
            repo = self._repo_cls(session)
            existing = await repo.get_by_id(config_id)
            if existing is None:
                raise WidgetConfigNotFoundError(
                    f"Widget configuration {config_id} not found",
                    details={"config_id": config_id, "request_id": request_id},
                    trace_id=trace["trace_id"],
                )
            update_fields = data.model_dump(exclude_unset=True)
            row = await repo.update(
                config_id=config_id,
                updated_by_user_id=updated_by_user_id,
                **update_fields,
            )
            await session.commit()
            if row is None:
                raise WidgetConfigNotFoundError(
                    f"Widget configuration {config_id} not found after update",
                    details={"config_id": config_id, "request_id": request_id},
                    trace_id=trace["trace_id"],
                )
            return self._to_read(row)

    async def generate_embed_snippet(
        self,
        config_id: str,
        request_id: str | None = None,
    ) -> EmbedSnippetRead:
        trace = self._trace(request_id)
        async with self._session_factory() as session:
            repo = self._repo_cls(session)
            row = await repo.get_by_id(config_id)
            if row is None:
                raise WidgetConfigNotFoundError(
                    f"Widget configuration {config_id} not found",
                    details={"config_id": config_id, "request_id": request_id},
                    trace_id=trace["trace_id"],
                )
        snippet = (
            f'<!-- Maintainer Copilot Widget (config: {row.id}) -->\n'
            f'<script data-mc-widget-config="{row.id}"></script>\n'
            f'<script src="BASE_URL/widget/loader.js"></script>'
        )
        return EmbedSnippetRead(
            widget_config_id=config_id,
            snippet=snippet,
            generated_at=datetime.now(timezone.utc),
        )

    @staticmethod
    def _to_read(row: WidgetConfig) -> WidgetConfigRead:
        import json

        origins = row.allowed_origins
        if isinstance(origins, str):
            origins = json.loads(origins)
        return WidgetConfigRead(
            id=row.id,
            name=row.name,
            allowed_origins=origins if isinstance(origins, list) else [],
            theme=row.theme or "default",
            welcome_message=row.welcome_message,
            is_enabled=row.is_enabled,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
