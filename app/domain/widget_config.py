"""Widget configuration domain models."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class WidgetConfigCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    allowed_origins: list[str] = Field(min_length=1)
    theme: str = "default"
    greeting: str | None = Field(default=None, max_length=500)
    welcome_message: str | None = Field(default=None, max_length=500)
    position: str = "bottom-right"
    enabled_tools: list[str] = Field(default_factory=list)
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
    greeting: str | None = Field(default=None, max_length=500)
    welcome_message: str | None = Field(default=None, max_length=500)
    position: str | None = None
    enabled_tools: list[str] | None = None
    is_enabled: bool | None = None

    @field_validator("allowed_origins")
    @classmethod
    def origins_non_empty(cls, v: list[str] | None) -> list[str] | None:
        if v is not None and not any(o.strip() for o in v):
            raise ValueError("allowed_origins must contain at least one non-empty origin")
        return v


class WidgetConfigRead(BaseModel):
    id: str
    widget_id: str
    name: str
    allowed_origins: list[str]
    theme: str
    greeting: str | None = None
    welcome_message: str | None = None
    position: str
    enabled_tools: list[str]
    is_enabled: bool
    created_at: datetime
    updated_at: datetime


class PublicWidgetConfigRead(BaseModel):
    widget_id: str
    theme: str
    greeting: str | None = None
    position: str
    enabled_tools: list[str]


class WidgetSessionToken(BaseModel):
    token: str
    expires_at: datetime
    widget_id: str


class WidgetChatAccepted(BaseModel):
    conversation_id: str
    widget_id: str


class WidgetConfigDelete(BaseModel):
    id: str
    widget_id: str
    deleted_at: datetime


class EmbedSnippetRead(BaseModel):
    widget_config_id: str
    snippet: str
    generated_at: datetime | None = None
