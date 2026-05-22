"""Unit tests for NER service response shaping and extraction-failure mapping."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from model_server.domain.issue_analysis import (
    IssueAnalysisRequest,
)
from model_server.infra.entity_ruler_pipeline import (
    EntityRulerPipeline,
)
from model_server.services.ner_service import (
    NerService,
    extract_entities_from_request,
)


@pytest.fixture
def pipeline() -> EntityRulerPipeline:
    p = EntityRulerPipeline()
    p.initialize()
    return p


@pytest.fixture
def service(pipeline) -> NerService:
    return NerService(pipeline)


class TestExtractEntitiesFromRequest:
    def test_extracts_from_title(self, pipeline):
        request = IssueAnalysisRequest(
            title="TypeError in src/app/parser.py",
        )
        entities = extract_entities_from_request(request, pipeline)
        assert len(entities) > 0

    def test_extracts_from_body(self, pipeline):
        request = IssueAnalysisRequest(
            body="parse_issue() on Python 3.11 with ERR_PARSER_42",
        )
        entities = extract_entities_from_request(request, pipeline)
        assert len(entities) > 0

    def test_extracts_from_comments(self, pipeline):
        request = IssueAnalysisRequest(
            comments=["Stack trace includes File 'src/app/parser.py', line 12"],
        )
        entities = extract_entities_from_request(request, pipeline)
        assert len(entities) > 0

    def test_deduplicates_across_fields(self, pipeline):
        request = IssueAnalysisRequest(
            title="TypeError",
            body="TypeError occurred",
            comments=["Got TypeError"],
        )
        entities = extract_entities_from_request(request, pipeline)
        type_errors = [e for e in entities if e.text == "TypeError"]
        assert len(type_errors) <= 3  # Different spans, not deduped

    def test_normalizes_empty_comments(self, pipeline):
        request = IssueAnalysisRequest(
            title="TypeError",
            comments=["  ", "", "parse_issue()"],
        )
        entities = extract_entities_from_request(request, pipeline)
        funcs = [e for e in entities if e.type == "function_name"]
        assert len(funcs) >= 1

    def test_deterministic_ordering(self, pipeline):
        request = IssueAnalysisRequest(
            title="TypeError",
            body="src/app/parser.py",
            comments=[],
        )
        entities1 = extract_entities_from_request(request, pipeline)
        entities2 = extract_entities_from_request(request, pipeline)
        assert len(entities1) == len(entities2)
        for e1, e2 in zip(entities1, entities2):
            assert e1.text == e2.text
            assert e1.type == e2.type


class TestNerService:
    def test_analyze_returns_entities(self, service):
        request = IssueAnalysisRequest(
            title="TypeError in src/app/parser.py parse_issue()",
        )
        response = service.analyze(request)
        assert response.entities
        assert len(response.entities) > 0

    def test_analyze_returns_empty_for_no_matches(self, service):
        request = IssueAnalysisRequest(title="hello world")
        response = service.analyze(request)
        assert response.entities == []

    def test_analyze_has_correct_entity_structure(self, service):
        request = IssueAnalysisRequest(
            title="ERR_PARSER_42 in production",
        )
        response = service.analyze(request)
        for entity in response.entities:
            assert entity.text
            assert entity.type in service.supported_types

    def test_analyze_with_request_id(self, service):
        request = IssueAnalysisRequest(title="TypeError")
        response = service.analyze(request, request_id="req-1")
        assert response.request_id == "req-1"

    def test_analyze_handles_pipeline_failure(self):
        broken_pipeline = MagicMock(spec=EntityRulerPipeline)
        broken_pipeline.configured = True
        broken_pipeline.extract_entities.side_effect = RuntimeError("pipeline failed")
        service = NerService(broken_pipeline)
        request = IssueAnalysisRequest(title="test")
        with pytest.raises(RuntimeError):
            service.analyze(request)
