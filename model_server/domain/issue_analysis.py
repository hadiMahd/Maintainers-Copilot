"""Issue analysis domain models — request, response, and error schemas."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator

SUPPORTED_ENTITY_TYPES = (
    "file_path",
    "function_name",
    "class_name",
    "package_name",
    "version_number",
    "error_code",
    "url",
    "stack_trace_marker",
    "environment_name",
    "command_snippet",
)

EntityType = Literal[
    "file_path",
    "function_name",
    "class_name",
    "package_name",
    "version_number",
    "error_code",
    "url",
    "stack_trace_marker",
    "environment_name",
    "command_snippet",
]

MAX_COMBINED_INPUT_CHARS = 8_000
MAX_COMMENTS = 100
MAX_FIELD_LENGTH = 8_000


def _normalize_whitespace(text: str) -> str:
    return text.strip()


def _non_blank(text: str) -> bool:
    return bool(text and text.strip())


def count_combined_characters(
    title: str | None, body: str | None, comments: list[str] | None
) -> int:
    t = title or ""
    b = body or ""
    c = "".join(comments or [])
    return len(t) + len(b) + len(c)


def normalize_comments(comments: list[str] | None) -> list[str]:
    if not comments:
        return []
    return [c.strip() for c in comments if c and c.strip()]


class SourceSpan(BaseModel):
    source_field: Literal["title", "body", "comments"]
    comment_index: int | None = None
    start: int = Field(ge=0)
    end: int = Field(gt=0)


class ExtractedEntity(BaseModel):
    text: str = Field(min_length=1)
    type: EntityType
    confidence: float | None = Field(default=None, ge=0, le=1)
    span: SourceSpan | None = None
    source_field: Literal["title", "body", "comments"] | None = None


class IssueAnalysisRequest(BaseModel):
    title: str | None = Field(default=None, max_length=MAX_FIELD_LENGTH)
    body: str | None = Field(default=None, max_length=MAX_FIELD_LENGTH)
    comments: list[str] | None = Field(default=None, max_length=MAX_FIELD_LENGTH)

    @model_validator(mode="after")
    def check_at_least_one_non_blank(self) -> IssueAnalysisRequest:
        title_ok = self.title and self.title.strip()
        body_ok = self.body and self.body.strip()
        comments_ok = self.comments and any(c for c in self.comments if c and c.strip())
        if not (title_ok or body_ok or comments_ok):
            raise ValueError("At least one of title, body, or comments must be non-empty")
        return self


class SummarizationRequest(IssueAnalysisRequest):
    max_summary_sentences: int | None = Field(default=None, ge=1, le=8)


class NerResponse(BaseModel):
    entities: list[ExtractedEntity]
    warnings: list[str] | None = None
    request_id: str | None = None


class IssueSummary(BaseModel):
    summary: str = Field(min_length=1)
    key_facts: list[str]
    unresolved_questions: list[str]
    suggested_next_step: str | None = None
    limitations: list[str] | None = None
    request_id: str | None = None


TOOL_ERROR_CODES = (
    "invalid_tool_input",
    "ner_extraction_failed",
    "summarizer_unavailable",
    "summarizer_timeout",
    "tool_execution_failed",
    "internal_error",
)

ToolErrorCode = Literal[
    "invalid_tool_input",
    "ner_extraction_failed",
    "summarizer_unavailable",
    "summarizer_timeout",
    "tool_execution_failed",
    "internal_error",
]


class ToolError(BaseModel):
    code: ToolErrorCode
    message: str
    request_id: str | None = None
    details: dict | None = None


class ErrorBody(BaseModel):
    error: ToolError
