"""Issue analysis API routes — NER and summarization endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse

from model_server.domain.issue_analysis import (
    IssueAnalysisRequest,
    SummarizationRequest,
    NerResponse,
    IssueSummary,
    ErrorBody,
    ToolError,
    count_combined_characters,
    MAX_COMBINED_INPUT_CHARS,
)
from model_server.services.ner_service import NerService
from model_server.services.summarization_service import SummarizationService
from model_server.infra.entity_ruler_pipeline import EntityRulerPipeline
from model_server.infra.summarization_adapter import (
    BaseSummarizationAdapter,
    SummarizationError,
    SummarizationTimeout,
    SummarizerUnavailable,
)

router = APIRouter()

__all__ = ["router"]


def _get_ner_service(request: Request) -> NerService | None:
    pipeline: EntityRulerPipeline | None = getattr(request.app.state, "ner_pipeline", None)
    if pipeline is None or not pipeline.configured:
        return None
    return NerService(pipeline)


def _get_summarization_service(request: Request) -> SummarizationService | None:
    adapter: BaseSummarizationAdapter | None = getattr(request.app.state, "summarization_adapter", None)
    if adapter is None or not adapter.configured:
        return None
    return SummarizationService(adapter)


@router.post("/ner", response_model=NerResponse)
async def extract_entities(payload: IssueAnalysisRequest, request: Request):
    combined = count_combined_characters(payload.title, payload.body, payload.comments)
    if combined > MAX_COMBINED_INPUT_CHARS:
        raise HTTPException(
            status_code=422,
            detail=ErrorBody(
                error=ToolError(
                    code="invalid_tool_input",
                    message=f"Combined input length {combined} exceeds maximum {MAX_COMBINED_INPUT_CHARS}",
                    request_id=getattr(request.state, "request_id", None),
                    details={"combined_characters": combined},
                )
            ).model_dump(),
        )
    service = _get_ner_service(request)
    if service is None:
        raise HTTPException(
            status_code=500,
            detail=ErrorBody(
                error=ToolError(
                    code="ner_extraction_failed",
                    message="NER pipeline is not configured",
                    request_id=getattr(request.state, "request_id", None),
                )
            ).model_dump(),
        )
    try:
        response = service.analyze(payload, request_id=getattr(request.state, "request_id", None))
        return response.model_dump()
    except RuntimeError:
        raise HTTPException(
            status_code=500,
            detail=ErrorBody(
                error=ToolError(
                    code="internal_error",
                    message="NER extraction failed due to an internal error",
                    request_id=getattr(request.state, "request_id", None),
                )
            ).model_dump(),
        )


@router.post("/summarize", response_model=IssueSummary)
async def summarize_issue(payload: SummarizationRequest, request: Request):
    combined = count_combined_characters(payload.title, payload.body, payload.comments)
    if combined > MAX_COMBINED_INPUT_CHARS:
        raise HTTPException(
            status_code=422,
            detail=ErrorBody(
                error=ToolError(
                    code="invalid_tool_input",
                    message=f"Combined input length {combined} exceeds maximum {MAX_COMBINED_INPUT_CHARS}",
                    request_id=getattr(request.state, "request_id", None),
                    details={"combined_characters": combined},
                )
            ).model_dump(),
        )
    service = _get_summarization_service(request)
    if service is None:
        raise HTTPException(
            status_code=503,
            detail=ErrorBody(
                error=ToolError(
                    code="summarizer_unavailable",
                    message="Summarization adapter is not configured",
                    request_id=getattr(request.state, "request_id", None),
                )
            ).model_dump(),
        )
    try:
        response = await service.summarize(
            payload,
            request_id=getattr(request.state, "request_id", None),
        )
        return response.model_dump()
    except SummarizationTimeout:
        raise HTTPException(
            status_code=503,
            detail=ErrorBody(
                error=ToolError(
                    code="summarizer_timeout",
                    message="Summarization request timed out",
                    request_id=getattr(request.state, "request_id", None),
                    details={"timeout_seconds": service.adapter.timeout_seconds},
                )
            ).model_dump(),
        )
    except SummarizerUnavailable:
        raise HTTPException(
            status_code=503,
            detail=ErrorBody(
                error=ToolError(
                    code="summarizer_unavailable",
                    message="Summarization adapter is not available",
                    request_id=getattr(request.state, "request_id", None),
                )
            ).model_dump(),
        )
    except SummarizationError:
        raise HTTPException(
            status_code=503,
            detail=ErrorBody(
                error=ToolError(
                    code="tool_execution_failed",
                    message="Summarization execution failed",
                    request_id=getattr(request.state, "request_id", None),
                )
            ).model_dump(),
        )

