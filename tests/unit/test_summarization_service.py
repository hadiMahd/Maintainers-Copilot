"""Unit tests for summarization service success-path shaping and normalization."""

from __future__ import annotations

import pytest

from model_server.domain.issue_analysis import SummarizationRequest
from model_server.infra.summarization_adapter import FakeSummarizationAdapter
from model_server.services.summarization_service import SummarizationService, _assemble_issue_text


@pytest.fixture
def adapter() -> FakeSummarizationAdapter:
    return FakeSummarizationAdapter()


@pytest.fixture
def service(adapter) -> SummarizationService:
    return SummarizationService(adapter)


class TestAssembleIssueText:
    def test_title_only(self):
        request = SummarizationRequest(title="My issue")
        text = _assemble_issue_text(request)
        assert "Title: My issue" in text

    def test_title_and_body(self):
        request = SummarizationRequest(title="My issue", body="The problem is...")
        text = _assemble_issue_text(request)
        assert "Title: My issue" in text
        assert "Body: The problem is..." in text

    def test_with_comments(self):
        request = SummarizationRequest(
            title="Issue",
            comments=["First comment", "Second comment"],
        )
        text = _assemble_issue_text(request)
        assert "Comment 0" in text
        assert "Comment 1" in text
        assert "First comment" in text
        assert "Second comment" in text

    def test_normalizes_empty_comments(self):
        request = SummarizationRequest(
            title="Issue",
            comments=["  ", "", "Real comment"],
        )
        text = _assemble_issue_text(request)
        assert "Real comment" in text
        assert "Comment 0" in text  # Only one comment after normalization
        # Only one comment index after normalization
        text_after_comments = text.split("Comments:\n")[1]
        assert text_after_comments.count("Comment") == 1

    def test_no_blank_fields_in_output(self):
        request = SummarizationRequest(title="Issue", body="", comments=["  ", ""])
        text = _assemble_issue_text(request)
        assert "Title: Issue" in text
        assert "Body:" not in text  # blank body excluded
        assert "Comments:" not in text  # all blank comments excluded


class TestSummarizationService:
    async def test_summarize_returns_structured_response(self, service):
        request = SummarizationRequest(title="Test issue", body="Some problem")
        result = await service.summarize(request)
        assert result.summary
        assert isinstance(result.key_facts, list)
        assert isinstance(result.unresolved_questions, list)

    async def test_summarize_sets_request_id(self, service):
        request = SummarizationRequest(title="Test issue")
        result = await service.summarize(request, request_id="req-7")
        assert result.request_id == "req-7"

    async def test_summarize_passes_max_sentences(self, service):
        request = SummarizationRequest(title="Test issue", max_summary_sentences=5)
        result = await service.summarize(request)
        assert result.summary

    async def test_summarize_handles_no_title(self, service):
        request = SummarizationRequest(body="Just a body")
        result = await service.summarize(request)
        assert result.summary
