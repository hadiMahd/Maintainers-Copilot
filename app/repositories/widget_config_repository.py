"""Widget configuration persistence.

Repository layer — owns SQL only.  Does NOT call ``.commit()`` or
``.rollback()``.  Transaction boundaries are owned by services.
"""

from __future__ import annotations

import json
import uuid
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infra.orm_models import WidgetConfig


class WidgetConfigRepository:
    """Async widget configuration persistence."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        name: str,
        allowed_origins: list[str],
        created_by_user_id: str,
        theme: str = "default",
        greeting: str | None = None,
        welcome_message: str | None = None,
        position: str = "bottom-right",
        enabled_tools: list[str] | None = None,
        is_enabled: bool = True,
    ) -> WidgetConfig:
        row = WidgetConfig(
            id=uuid.uuid4().hex,
            widget_id=uuid.uuid4().hex,
            name=name,
            allowed_origins=json.dumps(allowed_origins),
            theme=theme,
            greeting=greeting,
            welcome_message=welcome_message,
            position=position,
            enabled_tools=json.dumps(enabled_tools) if enabled_tools else None,
            is_enabled=is_enabled,
            created_by_user_id=created_by_user_id,
            updated_by_user_id=created_by_user_id,
        )
        self._session.add(row)
        return row

    async def get_by_id(self, config_id: str) -> WidgetConfig | None:
        result = await self._session.execute(
            select(WidgetConfig).where(WidgetConfig.id == config_id)
        )
        return result.scalar_one_or_none()

    async def get_by_widget_id(self, widget_id: str) -> WidgetConfig | None:
        result = await self._session.execute(
            select(WidgetConfig).where(WidgetConfig.widget_id == widget_id)
        )
        return result.scalar_one_or_none()

    async def list_all(self) -> Sequence[WidgetConfig]:
        result = await self._session.execute(
            select(WidgetConfig).order_by(WidgetConfig.updated_at.desc())
        )
        return result.scalars().all()

    async def update(
        self,
        config_id: str,
        updated_by_user_id: str,
        **fields,
    ) -> WidgetConfig | None:
        row = await self._session.get(WidgetConfig, config_id)
        if row is None:
            return None
        if "allowed_origins" in fields and fields["allowed_origins"] is not None:
            fields["allowed_origins"] = json.dumps(fields["allowed_origins"])
        for key, value in fields.items():
            if value is not None:
                setattr(row, key, value)
        from sqlalchemy import func as sa_func
        row.updated_by_user_id = updated_by_user_id
        row.updated_at = sa_func.now()
        return row

    async def delete(self, config_id: str) -> WidgetConfig | None:
        row = await self._session.get(WidgetConfig, config_id)
        if row is None:
            return None
        await self._session.delete(row)
        return row
