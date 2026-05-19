"""NER service — deterministic entity extraction via spaCy EntityRuler."""

from __future__ import annotations

import logging

from model_server.domain.issue_analysis import (
    IssueAnalysisRequest,
    NerResponse,
    ExtractedEntity,
    SourceSpan,
    EntityType,
    SUPPORTED_ENTITY_TYPES,
    normalize_comments,
)
from model_server.infra.entity_ruler_pipeline import (
    EntityRulerPipeline,
    EntityExtractionResult,
)

logger = logging.getLogger(__name__)


def _map_source_field(field_name: str, comment_index: int | None = None) -> str:
    return field_name


def _build_span(
    source_field: str,
    start: int,
    end: int,
    comment_index: int | None = None,
) -> SourceSpan:
    return SourceSpan(
        source_field=source_field,
        comment_index=comment_index,
        start=start,
        end=end,
    )


def _entity_key(entity: ExtractedEntity) -> tuple:
    return (
        entity.text,
        entity.type,
        entity.span.source_field if entity.span else "",
        entity.span.comment_index if entity.span else -1,
        entity.span.start if entity.span else -1,
        entity.span.end if entity.span else -1,
    )


def _deduplicate(entities: list[ExtractedEntity]) -> list[ExtractedEntity]:
    seen: set[tuple] = set()
    result: list[ExtractedEntity] = []
    for ent in entities:
        key = _entity_key(ent)
        if key not in seen:
            seen.add(key)
            result.append(ent)
    return result


def extract_entities_from_request(
    request: IssueAnalysisRequest,
    pipeline: EntityRulerPipeline,
) -> list[ExtractedEntity]:
    entities: list[ExtractedEntity] = []

    if request.title and request.title.strip():
        for result in pipeline.extract_entities(request.title):
            entities.append(ExtractedEntity(
                text=result.text,
                type=result.type,
                span=_build_span("title", result.start, result.end),
                source_field="title",
            ))

    if request.body and request.body.strip():
        for result in pipeline.extract_entities(request.body):
            entities.append(ExtractedEntity(
                text=result.text,
                type=result.type,
                span=_build_span("body", result.start, result.end),
                source_field="body",
            ))

    normalized = normalize_comments(request.comments)
    for idx, comment in enumerate(normalized):
        for result in pipeline.extract_entities(comment):
            entities.append(ExtractedEntity(
                text=result.text,
                type=result.type,
                span=_build_span("comments", result.start, result.end, comment_index=idx),
                source_field="comments",
            ))

    return _deduplicate(entities)


class NerService:
    def __init__(self, pipeline: EntityRulerPipeline) -> None:
        self._pipeline = pipeline

    @property
    def supported_types(self) -> list[str]:
        return list(self._pipeline.supported_entity_types)

    def analyze(
        self,
        request: IssueAnalysisRequest,
        request_id: str | None = None,
    ) -> NerResponse:
        entities = extract_entities_from_request(request, self._pipeline)
        return NerResponse(
            entities=entities,
            request_id=request_id,
        )
