from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class CurrentUserView:
    id: str
    email: str
    role: str
    is_active: bool = True


@dataclass
class LoginCredentials:
    email: str
    password: str


@dataclass
class ChatMessage:
    role: str
    content: str


@dataclass
class ChatEventView:
    event_type: str
    content: str = ""
    sequence: int = 0
    trace_id: str | None = None
    error: UIErrorMessage | None = None


@dataclass
class WidgetConfigView:
    id: str
    widget_id: str = ""
    name: str = ""
    allowed_origins: list[str] = field(default_factory=list)
    theme: str = "light"
    greeting: str | None = None
    position: str = "bottom-right"
    enabled_tools: list[str] = field(default_factory=list)
    is_enabled: bool = True
    updated_at: str = ""


@dataclass
class WidgetConfigForm:
    name: str = ""
    allowed_origins: list[str] = field(default_factory=list)
    theme: str = "light"
    greeting: str = ""
    position: str = "bottom-right"
    enabled_tools: list[str] = field(default_factory=list)
    is_enabled: bool = True


@dataclass
class EmbedSnippetView:
    widget_config_id: str
    snippet: str
    generated_at: str = ""


@dataclass
class MemoryInspectionQuery:
    scope: str = "own"
    memory_type: str = ""
    search_text: str = ""
    limit: int = 25


@dataclass
class MemoryRecordView:
    id: str
    memory_type: str
    redacted_content: str
    source: str
    created_at: str
    owner_user_id: str = ""


@dataclass
class MemoryInspectionResult:
    items: list[MemoryRecordView] = field(default_factory=list)
    next_cursor: str | None = None
    scope: str = "own"


@dataclass
class UIErrorMessage:
    code: str
    message: str
    retryable: bool = False
    request_id: str | None = None
    trace_id: str | None = None
