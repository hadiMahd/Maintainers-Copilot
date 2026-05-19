"""Summarization service — Azure OpenAI summarization via LangChain adapter."""

from __future__ import annotations

import logging

from model_server.domain.issue_analysis import (
    SummarizationRequest,
    IssueSummary,
    normalize_comments,
)
from model_server.infra.summarization_adapter import (
    BaseSummarizationAdapter,
)

logger = logging.getLogger(__name__)


def _assemble_issue_text(request: SummarizationRequest) -> str:
    parts: list[str] = []
    if request.title and request.title.strip():
        parts.append(f"Title: {request.title}")
    if request.body and request.body.strip():
        parts.append(f"Body: {request.body}")
    normalized = normalize_comments(request.comments)
    if normalized:
        comments_text = "\n".join(f"Comment {i}: {c}" for i, c in enumerate(normalized))
        parts.append(f"Comments:\n{comments_text}")
    return "\n\n".join(parts)


class SummarizationService:
    def __init__(self, adapter: BaseSummarizationAdapter) -> None:
        self._adapter = adapter

    @property
    def adapter(self) -> BaseSummarizationAdapter:
        return self._adapter

    async def summarize(
        self,
        request: SummarizationRequest,
        request_id: str | None = None,
    ) -> IssueSummary:
        issue_text = _assemble_issue_text(request)
        result = await self._adapter.summarize(
            prompt=issue_text,
            max_sentences=request.max_summary_sentences,
        )
        result.request_id = request_id
        return result
