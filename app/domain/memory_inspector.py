"""Memory inspector domain models."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class MemoryInspectionQuery(BaseModel):
    owner_user_id: str | None = None
    memory_type: str | None = None
    limit: int = Field(default=25, ge=1, le=100)
    cursor: str | None = None

    @field_validator("memory_type")
    @classmethod
    def memory_type_valid(cls, v: str | None) -> str | None:
        if v is not None and v not in {"episodic", "semantic", "procedural"}:
            raise ValueError("memory_type must be episodic, semantic, or procedural")
        return v


class MemoryRecordRead(BaseModel):
    id: str
    owner_user_id: str
    memory_type: str
    redacted_content: str
    source: str | None = None
    created_at: datetime


class MemoryInspectionResult(BaseModel):
    items: list[MemoryRecordRead]
    next_cursor: str | None = None
    scope: str = "own"
