"""Model-server route-boundary coverage for issue-analysis handlers."""

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


class TestNerRouteBoundaries:
    async def test_ner_route_exists(self, client):
        response = await client.post("/ner", json={"title": "test"})
        assert response.status_code in (200, 422, 500)

    async def test_ner_requires_post(self, client):
        response = await client.get("/ner")
        assert response.status_code == 405

    async def test_ner_requires_json(self, client):
        response = await client.post("/ner", content="not json")
        assert response.status_code == 422

    async def test_ner_validates_entity_types_in_response(self, client):
        payload = {"title": "TypeError in src/app/parser.py"}
        response = await client.post("/ner", json=payload)
        assert response.status_code == 200
        data = response.json()
        for entity in data["entities"]:
            assert entity["type"] in (
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


class TestSummarizeRouteBoundaries:
    async def test_summarize_route_exists(self, client):
        response = await client.post("/summarize", json={"title": "test"})
        assert response.status_code in (200, 422, 503)

    async def test_summarize_requires_post(self, client):
        response = await client.get("/summarize")
        assert response.status_code == 405

    async def test_summarize_accepts_full_request(self, client):
        payload = {
            "title": "Test issue",
            "body": "Description of the problem",
            "comments": ["User report", "Maintainer response"],
            "max_summary_sentences": 3,
        }
        response = await client.post("/summarize", json=payload)
        assert response.status_code == 200


class TestCorrelationHeaders:
    async def test_ner_response_includes_request_id_header(self, client):
        response = await client.post(
            "/ner",
            json={"title": "test"},
            headers={"X-Request-ID": "boundary-test-1"},
        )
        assert response.headers.get("X-Request-ID") == "boundary-test-1"

    async def test_summarize_response_includes_trace_id(self, client):
        response = await client.post("/summarize", json={"title": "test"})
        assert "X-Trace-ID" in response.headers
