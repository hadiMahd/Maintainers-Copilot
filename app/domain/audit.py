"""Audit domain models."""

from typing import Literal

from pydantic import BaseModel

AuditAction = Literal[
    "memory.write",
    "role.change",
    "admin_invitation.create",
    "widget_config.create",
    "widget_config.update",
    "widget_config.delete",
    "conversation.delete",
]


class AuditLogEntry(BaseModel):
    """Audit log entry."""

    id: str
    actor_user_id: str | None
    action: str
    target_type: str | None
    target_id: str | None
    timestamp: str
    metadata: dict | None = None
