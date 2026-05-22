"""Phase 7 tool schemas and LLM tool-call contracts."""

from __future__ import annotations

import re
import uuid
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

ToolName = Literal[
    "classify_issue",
    "extract_entities",
    "summarize_issue",
    "answer_project_question",
    "recall_memory",
    "write_memory",
]

ToolExecutionStatus = Literal["success", "failed"]
ClassifierLabel = Literal["bug", "feature", "docs", "question"]

_EXPLICIT_MEMORY_PATTERNS = (
    re.compile(r"\bremember\b", re.IGNORECASE),
    re.compile(r"\bstore\b.*\b(for later|this|that|it)\b", re.IGNORECASE),
    re.compile(r"\bsave\b.*\b(for later|this|that|it)\b", re.IGNORECASE),
)


class ToolSourceReference(BaseModel):
    """Bounded safe source metadata returned from a tool."""

    source_id: str
    source_path: str | None = None
    score: float | None = None


class RetrievedSnapshotReference(BaseModel):
    """Redacted snapshot reference returned after a RAG call."""

    snapshot_id: str | None = None
    retrieval_trace_id: str | None = None


class MemoryWriteIntent(BaseModel):
    """Explicit remember intent signal."""

    present: bool
    evidence: str
    target_content_reference: str | None = None


def detect_write_memory_intent(message: str) -> MemoryWriteIntent:
    """Detect explicit remember intent from the user message."""
    cleaned = message.strip()
    for pattern in _EXPLICIT_MEMORY_PATTERNS:
        if pattern.search(cleaned):
            return MemoryWriteIntent(
                present=True,
                evidence="explicit remember request detected",
                target_content_reference=cleaned[:160],
            )
    return MemoryWriteIntent(
        present=False,
        evidence="no explicit remember request detected",
        target_content_reference=None,
    )


class ClassifyIssueInput(BaseModel):
    title: str | None = None
    body: str | None = None
    comments: list[str] | None = None

    @model_validator(mode="after")
    def validate_has_text(self):
        if not any(
            [
                self.title and self.title.strip(),
                self.body and self.body.strip(),
                self.comments and any(comment.strip() for comment in self.comments),
            ]
        ):
            raise ValueError("At least one text field must be provided")
        return self


class ClassifyIssueOutput(BaseModel):
    label: ClassifierLabel
    confidence: float | None = Field(default=None, ge=0, le=1)
    model_version: str


class ExtractedEntity(BaseModel):
    text: str = Field(min_length=1)
    type: str = Field(min_length=1)
    confidence: float | None = Field(default=None, ge=0, le=1)
    source_span: dict[str, Any] | None = None


class ExtractEntitiesInput(BaseModel):
    title: str | None = None
    body: str | None = None
    comments: list[str] | None = None

    @model_validator(mode="after")
    def validate_has_text(self):
        if not any(
            [
                self.title and self.title.strip(),
                self.body and self.body.strip(),
                self.comments and any(comment.strip() for comment in self.comments),
            ]
        ):
            raise ValueError("At least one text field must be provided")
        return self


class ExtractEntitiesOutput(BaseModel):
    entities: list[ExtractedEntity]


class SummarizeIssueInput(BaseModel):
    title: str | None = None
    body: str | None = None
    comments: list[str] | None = None

    @model_validator(mode="after")
    def validate_has_text(self):
        if not any(
            [
                self.title and self.title.strip(),
                self.body and self.body.strip(),
                self.comments and any(comment.strip() for comment in self.comments),
            ]
        ):
            raise ValueError("At least one text field must be provided")
        return self


class SummarizeIssueOutput(BaseModel):
    summary: str
    key_facts: list[str] = Field(default_factory=list)
    unresolved_questions: list[str] = Field(default_factory=list)
    suggested_next_step: str | None = None


class AnswerProjectQuestionInput(BaseModel):
    question: str = Field(min_length=1)
    metadata_filters: dict[str, Any] = Field(default_factory=dict)
    query_transformation_enabled: bool = False


class RAGRetrievedChunk(BaseModel):
    chunk_id: str
    source_path: str | None = None
    score: float | None = None
    preview: str | None = None


class RAGToolClientResponse(BaseModel):
    answer: str
    supporting_sources: list[ToolSourceReference] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    retrieval_trace_id: str | None = None
    retrieved_chunks: list[RAGRetrievedChunk] = Field(default_factory=list)


class RAGToolResult(BaseModel):
    answer: str
    supporting_sources: list[ToolSourceReference] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    retrieval_trace_id: str | None = None
    snapshot_id: str | None = None
    untrusted_context_used: bool = True


class WriteMemoryInput(BaseModel):
    content: str = Field(min_length=1)
    memory_type: str = "semantic"
    metadata: dict[str, Any] = Field(default_factory=dict)


class RecalledMemoryItem(BaseModel):
    id: str
    memory_type: str
    content: str
    audit_log_id: str


class RecallMemoryInput(BaseModel):
    query: str = Field(min_length=1)
    limit: int = Field(default=5, ge=1, le=20)


class RecallMemoryOutput(BaseModel):
    items: list[RecalledMemoryItem] = Field(default_factory=list)


class WriteMemoryOutput(BaseModel):
    memory_id: str
    audit_log_id: str
    redaction_summary: str


class ToolDefinition(BaseModel):
    """Registered tool contract exposed to the LLM."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: ToolName
    description: str
    input_model: type[BaseModel]
    output_model: type[BaseModel]
    timeout_seconds: int = Field(ge=1)
    requires_explicit_intent: bool = False


class LLMToolCall(BaseModel):
    """One tool call requested by the LLM."""

    tool_call_id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class ToolExecutionError(BaseModel):
    """Safe tool failure payload."""

    code: str
    message: str
    request_id: str | None = None
    trace_id: str | None = None
    details: dict[str, Any] | None = None


class ToolExecutionResult(BaseModel):
    """Validated tool result passed back into chat orchestration."""

    tool_call_id: str
    name: str
    status: ToolExecutionStatus
    output: dict[str, Any] | None = None
    error: ToolExecutionError | None = None
    redacted_input: dict[str, Any] | None = None
    redacted_output: dict[str, Any] | None = None
    duration_ms: int = 0


class LLMCompletion(BaseModel):
    """One tool-calling LLM completion."""

    message: str = ""
    tool_calls: list[LLMToolCall] = Field(default_factory=list)
    finish_reason: str = "stop"
    model_version: str = "fake-tool-calling-llm"
    prompt_version: str = "chatbot-prompts-v1"
    response_metadata: dict[str, Any] = Field(default_factory=dict)


def build_default_tool_definitions(timeout_seconds: int) -> dict[str, ToolDefinition]:
    """Build the registered Phase 7 tool set."""
    return {
        "classify_issue": ToolDefinition(
            name="classify_issue",
            description="Classify an issue into bug, feature, docs, or question.",
            input_model=ClassifyIssueInput,
            output_model=ClassifyIssueOutput,
            timeout_seconds=timeout_seconds,
        ),
        "extract_entities": ToolDefinition(
            name="extract_entities",
            description="Extract code-shaped entities from issue text.",
            input_model=ExtractEntitiesInput,
            output_model=ExtractEntitiesOutput,
            timeout_seconds=timeout_seconds,
        ),
        "summarize_issue": ToolDefinition(
            name="summarize_issue",
            description="Summarize long issue threads for maintainers.",
            input_model=SummarizeIssueInput,
            output_model=SummarizeIssueOutput,
            timeout_seconds=timeout_seconds,
        ),
        "answer_project_question": ToolDefinition(
            name="answer_project_question",
            description="Answer a maintainer question using retrieved project evidence.",
            input_model=AnswerProjectQuestionInput,
            output_model=RAGToolResult,
            timeout_seconds=timeout_seconds,
        ),
        "recall_memory": ToolDefinition(
            name="recall_memory",
            description=(
                "Search same-user long-term semantic memory for user-approved facts, "
                "preferences, tools, environments, and workflow context relevant to the request."
            ),
            input_model=RecallMemoryInput,
            output_model=RecallMemoryOutput,
            timeout_seconds=timeout_seconds,
        ),
        "write_memory": ToolDefinition(
            name="write_memory",
            description="Persist long-term memory only when the user explicitly asks.",
            input_model=WriteMemoryInput,
            output_model=WriteMemoryOutput,
            timeout_seconds=timeout_seconds,
            requires_explicit_intent=True,
        ),
    }
