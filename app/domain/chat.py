"""Phase 7 chat domain models."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
import uuid

from pydantic import BaseModel, Field


ChatEventType = Literal["message_delta", "tool_status", "warning", "error", "done"]
ChatMessageRole = Literal["system", "developer", "user", "assistant", "tool"]


def new_message_id() -> str:
    """Create a stable message identifier."""
    return uuid.uuid4().hex


def new_trace_id() -> str:
    """Create a stable trace identifier."""
    return uuid.uuid4().hex[:12]


def utc_now_iso() -> str:
    """Return the current UTC timestamp in ISO-8601 format."""
    return datetime.now(timezone.utc).isoformat()


class ChatRequest(BaseModel):
    """Authenticated chat request payload."""

    conversation_id: str
    message: str
    stream: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)


class ChatErrorBody(BaseModel):
    """Safe chat error shape for SSE events."""

    code: str
    message: str
    request_id: str | None = None
    trace_id: str | None = None
    details: dict[str, Any] | None = None


class ChatStreamEvent(BaseModel):
    """One ordered SSE event emitted for a chat response."""

    event_type: ChatEventType
    conversation_id: str
    sequence: int
    message_id: str | None = None
    content: str | None = None
    trace_id: str | None = None
    error: ChatErrorBody | None = None


class ConversationMessage(BaseModel):
    """One bounded message used for chat context."""

    role: ChatMessageRole
    content: str
    name: str | None = None


class ChatLimits(BaseModel):
    """Runtime bounds for one chat request."""

    request_size_limit_bytes: int = Field(ge=1)
    context_size_limit_chars: int = Field(ge=1)
    max_tool_calls: int = Field(ge=1)
    recursion_limit: int = Field(ge=1)
    total_timeout_seconds: int = Field(ge=1)
    per_tool_timeout_seconds: int = Field(ge=1)


class ConversationState(BaseModel):
    """User-scoped short-term chat state."""

    user_id: str
    conversation_id: str
    messages: list[ConversationMessage] = Field(default_factory=list)
    updated_at: str = Field(default_factory=utc_now_iso)
    expires_at: str | None = None
    degraded: bool = False


class TraceRoot(BaseModel):
    """Root trace metadata for a user chat message."""

    trace_id: str
    run_id: str | None = None
    backend: str


class ChatExecutionResult(BaseModel):
    """Completed chat execution returned before SSE formatting."""

    request_id: str
    conversation_id: str
    message_id: str
    trace_id: str | None = None
    run_id: str | None = None
    events: list[ChatStreamEvent] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class ChatGraphState(BaseModel):
    """State passed through the thin chat workflow."""

    request_id: str
    user_id: str
    conversation_id: str
    message_id: str
    pending_user_message: str
    messages: list[ConversationMessage] = Field(default_factory=list)
    tool_calls: list["LLMToolCall"] = Field(default_factory=list)
    tool_results: list["ToolExecutionResult"] = Field(default_factory=list)
    tool_call_count: int = 0
    remaining_steps: int | None = None
    limits: ChatLimits
    trace_id: str | None = None
    run_id: str | None = None
    final_response: str = ""
    warnings: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


from app.domain.chat_tools import LLMToolCall, ToolExecutionResult  # noqa: E402

ChatGraphState.model_rebuild()
