"""Tests for health endpoints."""

import uuid

import pytest

from app.domain.models import ReadinessCheck


@pytest.fixture
def mock_pgvector(monkeypatch):
    """Mock pgvector probe."""

    async def mock_probe(*args, **kwargs):
        return ReadinessCheck(name="pgvector", status="ok")

    monkeypatch.setattr("app.services.health_service.probe_pgvector", mock_probe)


@pytest.mark.asyncio
async def test_live_returns_200(app, mock_pgvector):
    """GET /health/live returns 200 with expected body."""
    response = await app.get("/health/live")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "maintainer-copilot"
    assert body["checks"] == []


@pytest.mark.asyncio
async def test_ready_all_ok_returns_200(app, mock_pgvector):
    """GET /health/ready with all deps healthy returns 200 and 5 ok checks."""
    response = await app.get("/health/ready")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    checks = body["checks"]
    assert len(checks) == 5
    names = {c["name"] for c in checks}
    assert names == {"postgres", "redis", "minio", "vault", "pgvector"}
    for c in checks:
        assert c["status"] == "ok"


@pytest.mark.asyncio
async def test_ready_postgres_fail_returns_503(app, mock_pgvector, monkeypatch):
    """Mock probe_database to unavailable and assert 503."""

    async def fail_probe(*args, **kwargs):
        return ReadinessCheck(name="postgres", status="unavailable")

    monkeypatch.setattr("app.services.health_service.probe_database", fail_probe)

    response = await app.get("/health/ready")
    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "unavailable"


@pytest.mark.asyncio
async def test_request_id_header_present_on_live(app):
    """X-Request-ID header exists in /health/live response."""
    response = await app.get("/health/live")
    assert "X-Request-ID" in response.headers


@pytest.mark.asyncio
async def test_request_id_header_present_on_ready(app):
    """X-Request-ID header exists in /health/ready response."""
    response = await app.get("/health/ready")
    assert "X-Request-ID" in response.headers


@pytest.mark.asyncio
async def test_request_id_echoed_from_request(app):
    """Send custom X-Request-ID and assert it is echoed."""
    custom_id = "my-custom-id-123"
    response = await app.get("/health/live", headers={"X-Request-ID": custom_id})
    assert response.headers["X-Request-ID"] == custom_id


@pytest.mark.asyncio
async def test_request_id_generated_when_absent(app):
    """Send no X-Request-ID and assert response header is a valid UUID4."""
    response = await app.get("/health/live")
    header = response.headers["X-Request-ID"]
    # Validate UUID4 format
    parsed = uuid.UUID(header)
    assert parsed.version == 4
