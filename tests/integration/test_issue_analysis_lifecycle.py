"""Integration tests for issue-analysis lifespan wiring and failure isolation."""

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


class TestLifespanWiring:
    async def test_ner_pipeline_initialized_on_startup(self, client, app):
        pipeline = app.state.ner_pipeline
        assert pipeline.configured

    async def test_summarization_adapter_initialized_on_startup(self, client, app):
        adapter = app.state.summarization_adapter
        assert adapter is not None
        assert adapter.configured

    async def test_health_endpoint_includes_ner_summarizer_status(self, client):
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "ner_configured" in data
        assert "summarizer_configured" in data
        assert data["ner_configured"] is True
        assert data["summarizer_configured"] is True


class TestFailureIsolation:
    async def test_ner_failure_does_not_crash_server(self, client):
        response = await client.post("/ner", json={"title": "hello world"})
        assert response.status_code in (200, 500)
        health = await client.get("/health")
        assert health.status_code == 200

    async def test_summarizer_failure_does_not_crash_server(self, client):
        response = await client.post("/summarize", json={"title": "test"})
        assert response.status_code in (200, 503)
        health = await client.get("/health")
        assert health.status_code == 200

    async def test_request_id_propagated_to_responses(self, client):
        response = await client.get("/health", headers={"X-Request-ID": "lifecycle-1"})
        assert response.headers.get("X-Request-ID") == "lifecycle-1"

    async def test_trace_id_set_on_responses(self, client):
        response = await client.get("/health")
        assert "X-Trace-ID" in response.headers
