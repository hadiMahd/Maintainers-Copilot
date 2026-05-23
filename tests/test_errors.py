"""Tests for error handling."""

import httpx
import pytest
from fastapi import FastAPI

from app.api.error_handlers import register_error_handlers
from app.core.config import AppSettings
from app.core.middleware import RequestIDMiddleware
from app.domain.errors import DependencyError


@pytest.fixture
async def error_app():
    """Return a test app with temporary error-raising routes."""
    settings = AppSettings(
        environment="test",
        vault_addr="http://fake",
        vault_token="fake-token",
    )
    test_app = FastAPI()
    test_app.add_middleware(RequestIDMiddleware, settings=settings)
    register_error_handlers(test_app)

    @test_app.get("/test-dependency-error")
    async def dependency_error():
        raise DependencyError("service down")

    @test_app.get("/test-unhandled-exception")
    async def unhandled_exception():
        raise Exception("boom")

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=test_app), base_url="http://test"
    ) as client:
        yield client


@pytest.mark.asyncio
async def test_domain_error_returns_correct_code_and_status(error_app):
    """DependencyError returns 503 with correct error code."""
    response = await error_app.get("/test-dependency-error")
    assert response.status_code == 503
    body = response.json()
    assert body["error_code"] == "DEPENDENCY_UNAVAILABLE"


@pytest.mark.asyncio
async def test_unhandled_exception_returns_server_error(error_app):
    """Unhandled exception returns 500 with SERVER_ERROR code."""
    response = await error_app.get("/test-unhandled-exception")
    assert response.status_code == 500
    body = response.json()
    assert body["error_code"] == "SERVER_ERROR"


@pytest.mark.asyncio
async def test_error_response_contains_request_id(error_app):
    """Error response body contains request_id field."""
    response = await error_app.get("/test-dependency-error")
    body = response.json()
    assert "request_id" in body
    assert body["request_id"] != ""


@pytest.mark.asyncio
async def test_no_stack_trace_in_message(error_app):
    """Error response message does not contain stack trace text."""
    response = await error_app.get("/test-unhandled-exception")
    body = response.json()
    message = body["message"]
    assert "Traceback" not in message
    assert "File " not in message
    assert "line " not in message


@pytest.mark.asyncio
async def test_error_response_shape(error_app):
    """Error response has exactly error_code, message, request_id keys."""
    response = await error_app.get("/test-dependency-error")
    body = response.json()
    assert set(body.keys()) == {"error_code", "message", "request_id"}
