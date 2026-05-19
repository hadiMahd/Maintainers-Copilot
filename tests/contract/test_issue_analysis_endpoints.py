"""Contract tests for /ner and /summarize endpoints."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from model_server.main import create_app, lifespan


@pytest.fixture
def app():
    return create_app()


@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with lifespan(app):
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            yield c


class TestNerEndpoint:
    async def test_ner_returns_200_with_entities(self, client):
        payload = {
            "title": "TypeError in src/app/parser.py",
            "body": "Running pytest fails in parse_issue() on Python 3.11 with ERR_PARSER_42",
            "comments": ["Stack trace includes File 'src/app/parser.py', line 12, in parse_issue"],
        }
        response = await client.post("/ner", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "entities" in data
        assert isinstance(data["entities"], list)

    async def test_ner_returns_empty_entities_for_no_matches(self, client):
        payload = {
            "title": "hello world",
            "body": "nothing to see here",
        }
        response = await client.post("/ner", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "entities" in data
        assert data["entities"] == []

    async def test_ner_entities_have_required_fields(self, client):
        payload = {
            "title": "TypeError in src/app/parser.py",
            "body": "parse_issue() on Python 3.11 with ERR_PARSER_42",
        }
        response = await client.post("/ner", json=payload)
        assert response.status_code == 200
        data = response.json()
        for entity in data["entities"]:
            assert "text" in entity
            assert "type" in entity
            assert len(entity["text"]) >= 1
            assert entity["type"] in (
                "file_path", "function_name", "class_name", "package_name",
                "version_number", "error_code", "url", "stack_trace_marker",
                "environment_name", "command_snippet",
            )

    async def test_ner_returns_request_id_when_provided(self, client):
        payload = {"title": "TypeError in src/app/parser.py"}
        response = await client.post("/ner", json=payload, headers={"X-Request-ID": "req-123"})
        assert response.status_code == 200
        assert response.headers.get("X-Request-ID") == "req-123"

    async def test_ner_rejects_empty_payload(self, client):
        payload = {"title": "", "body": ""}
        response = await client.post("/ner", json=payload)
        assert response.status_code == 422

    async def test_ner_rejects_oversized_combined_input(self, client):
        payload = {"title": "x" * 4000, "body": "y" * 4001, "comments": []}
        response = await client.post("/ner", json=payload)
        assert response.status_code == 422
        data = response.json()
        assert data["detail"]["error"]["code"] == "invalid_tool_input"


class TestSummarizeEndpoint:
    async def test_summarize_returns_200_with_fake_adapter(self, client):
        payload = {
            "title": "Parser fails on Python 3.11",
            "body": "The issue appears after upgrading.",
            "comments": ["Maintainer asked whether this happens on Python 3.10."],
        }
        response = await client.post("/summarize", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "summary" in data
        assert "key_facts" in data
        assert "unresolved_questions" in data
        assert isinstance(data["key_facts"], list)
        assert isinstance(data["unresolved_questions"], list)

    async def test_summarize_returns_request_id(self, client):
        payload = {"title": "Test issue"}
        response = await client.post("/summarize", json=payload, headers={"X-Request-ID": "req-456"})
        assert response.status_code == 200
        assert response.headers.get("X-Request-ID") == "req-456"

    async def test_summarize_rejects_empty_payload(self, client):
        payload = {"title": "", "body": ""}
        response = await client.post("/summarize", json=payload)
        assert response.status_code == 422

    async def test_summarize_rejects_oversized_combined_input(self, client):
        payload = {"title": "x" * 4000, "body": "y" * 4001}
        response = await client.post("/summarize", json=payload)
        assert response.status_code == 422
        data = response.json()
        assert data["detail"]["error"]["code"] == "invalid_tool_input"

    async def test_summarize_accepts_max_summary_sentences(self, client):
        payload = {"title": "Test issue", "max_summary_sentences": 3}
        response = await client.post("/summarize", json=payload)
        assert response.status_code == 200
