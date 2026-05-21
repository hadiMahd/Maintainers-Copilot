"""Widget configuration domain models."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class WidgetConfigCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    allowed_origins: list[str] = Field(min_length=1)
    theme: str = "default"
    welcome_message: str | None = Field(default=None, max_length=500)
    is_enabled: bool = True

    @field_validator("allowed_origins")
    @classmethod
    def origins_non_empty(cls, v: list[str]) -> list[str]:
        if not any(o.strip() for o in v):
            raise ValueError("allowed_origins must contain at least one non-empty origin")
        return v


class WidgetConfigUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    allowed_origins: list[str] | None = Field(default=None, min_length=1)
    theme: str | None = None
    welcome_message: str | None = Field(default=None, max_length=500)
    is_enabled: bool | None = None

    @field_validator("allowed_origins")
    @classmethod
    def origins_non_empty(cls, v: list[str] | None) -> list[str] | None:
        if v is not None and not any(o.strip() for o in v):
            raise ValueError("allowed_origins must contain at least one non-empty origin")
        return v


class WidgetConfigRead(BaseModel):
    id: str
    name: str
    allowed_origins: list[str]
    theme: str
    welcome_message: str | None = None
    is_enabled: bool
    created_at: datetime
    updated_at: datetime


class EmbedSnippetRead(BaseModel):
    widget_config_id: str
    snippet: str
    generated_at: datetime | None = None
