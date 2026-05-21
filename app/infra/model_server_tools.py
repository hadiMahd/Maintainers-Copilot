"""Async tool clients for classifier, NER, and summarization."""

from __future__ import annotations

from typing import Any

import httpx

from app.domain.chat_tools import (
    ClassifyIssueInput,
    ClassifyIssueOutput,
    ExtractEntitiesInput,
    ExtractEntitiesOutput,
    ExtractedEntity,
    SummarizeIssueInput,
    SummarizeIssueOutput,
)


class BaseModelServerTools:
    """Project-owned issue-analysis tool seam."""

    async def classify_issue(
        self,
        payload: ClassifyIssueInput,
        *,
        request_id: str | None = None,
        trace_id: str | None = None,
    ) -> ClassifyIssueOutput:
        raise NotImplementedError

    async def extract_entities(
        self,
        payload: ExtractEntitiesInput,
        *,
        request_id: str | None = None,
        trace_id: str | None = None,
    ) -> ExtractEntitiesOutput:
        raise NotImplementedError

    async def summarize_issue(
        self,
        payload: SummarizeIssueInput,
        *,
        request_id: str | None = None,
        trace_id: str | None = None,
    ) -> SummarizeIssueOutput:
        raise NotImplementedError


class FakeModelServerTools(BaseModelServerTools):
    """Deterministic fake tool client for automated tests."""

    def __init__(
        self,
        *,
        classify_output: ClassifyIssueOutput | None = None,
        entities_output: ExtractEntitiesOutput | None = None,
        summary_output: SummarizeIssueOutput | None = None,
    ) -> None:
        self.classify_output = classify_output or ClassifyIssueOutput(
            label="bug",
            confidence=0.9,
            model_version="0.1.0",
        )
        self.entities_output = entities_output or ExtractEntitiesOutput(
            entities=[ExtractedEntity(text="app/services/auth_service.py", type="file_path")]
        )
        self.summary_output = summary_output or SummarizeIssueOutput(
            summary="Summarized issue thread.",
            key_facts=["key fact"],
            unresolved_questions=["open question"],
            suggested_next_step="investigate failing path",
        )

    async def classify_issue(self, payload: ClassifyIssueInput, **_: Any) -> ClassifyIssueOutput:
        _ = payload
        return self.classify_output

    async def extract_entities(self, payload: ExtractEntitiesInput, **_: Any) -> ExtractEntitiesOutput:
        _ = payload
        return self.entities_output

    async def summarize_issue(self, payload: SummarizeIssueInput, **_: Any) -> SummarizeIssueOutput:
        _ = payload
        return self.summary_output


class HTTPModelServerTools(BaseModelServerTools):
    """HTTP-backed tool client for model-server endpoints."""

    def __init__(self, base_url: str, timeout_seconds: float = 10.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds

    async def classify_issue(
        self,
        payload: ClassifyIssueInput,
        *,
        request_id: str | None = None,
        trace_id: str | None = None,
    ) -> ClassifyIssueOutput:
        body = await self._post(
            "/classifier/predict",
            payload.model_dump(exclude_none=True),
            request_id=request_id,
            trace_id=trace_id,
        )
        return ClassifyIssueOutput.model_validate(body)

    async def extract_entities(
        self,
        payload: ExtractEntitiesInput,
        *,
        request_id: str | None = None,
        trace_id: str | None = None,
    ) -> ExtractEntitiesOutput:
        body = await self._post(
            "/ner",
            payload.model_dump(exclude_none=True),
            request_id=request_id,
            trace_id=trace_id,
        )
        return ExtractEntitiesOutput.model_validate(body)

    async def summarize_issue(
        self,
        payload: SummarizeIssueInput,
        *,
        request_id: str | None = None,
        trace_id: str | None = None,
    ) -> SummarizeIssueOutput:
        body = await self._post(
            "/summarize",
            payload.model_dump(exclude_none=True),
            request_id=request_id,
            trace_id=trace_id,
        )
        return SummarizeIssueOutput.model_validate(body)

    async def _post(
        self,
        path: str,
        payload: dict[str, Any],
        *,
        request_id: str | None,
        trace_id: str | None,
    ) -> dict[str, Any]:
        headers = {}
        if request_id:
            headers["X-Request-ID"] = request_id
        if trace_id:
            headers["X-Trace-ID"] = trace_id
        async with httpx.AsyncClient(base_url=self._base_url, timeout=self._timeout_seconds) as client:
            response = await client.post(path, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()
