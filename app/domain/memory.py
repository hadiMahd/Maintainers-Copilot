"""Memory domain models."""

from enum import Enum

from pydantic import BaseModel, field_validator


class MemoryType(str, Enum):
    episodic = "episodic"
    semantic = "semantic"
    procedural = "procedural"


class ShortTermMemoryWrite(BaseModel):
    """Write short-term memory request."""

    conversation_id: str
    key: str
    value: str

    @field_validator("key")
    @classmethod
    def key_non_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Key must not be empty")
        return v


class ShortTermMemoryRead(BaseModel):
    """Read short-term memory response."""

    conversation_id: str
    key: str
    value: str | None = None
    expires_at: str | None = None


class WriteMemoryRequest(BaseModel):
    """Explicit long-term memory write request."""

    content: str
    memory_type: str
    metadata: dict | None = None

    @field_validator("content")
    @classmethod
    def content_non_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Content must not be empty")
        return v

    @field_validator("memory_type")
    @classmethod
    def memory_type_valid(cls, v: str) -> str:
        allowed = {t.value for t in MemoryType}
        if v not in allowed:
            raise ValueError(f"Memory type must be one of {sorted(allowed)}")
        return v


class LongTermMemoryRead(BaseModel):
    """Long-term memory response."""

    id: str
    memory_type: str
    content: str
    audit_log_id: str


class LongTermMemoryRecallRequest(BaseModel):
    """Cross-conversation recall request."""

    query: str
    conversation_id: str | None = None
    limit: int = 5

    @field_validator("query")
    @classmethod
    def query_non_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Query must not be empty")
        return v

    @field_validator("limit")
    @classmethod
    def limit_bounds(cls, v: int) -> int:
        if v < 1 or v > 20:
            raise ValueError("Limit must be between 1 and 20")
        return v


class LongTermMemoryRecallResponse(BaseModel):
    """Cross-conversation recall response."""

    items: list[LongTermMemoryRead]
