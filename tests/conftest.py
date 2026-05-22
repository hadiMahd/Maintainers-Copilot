"""Pytest configuration and shared fixtures."""

import os
from unittest.mock import MagicMock

import pytest

# Set required env vars BEFORE importing any app modules that create AppSettings
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("VAULT_ADDR", "http://fake-vault:8200")
os.environ.setdefault("VAULT_TOKEN", "fake-token")


from app.core.config import AppSettings
from app.domain.models import ReadinessCheck


@pytest.fixture
def settings(monkeypatch):
    """Return test AppSettings."""
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("VAULT_ADDR", "http://fake-vault:8200")
    monkeypatch.setenv("VAULT_TOKEN", "fake-token")
    return AppSettings(
        environment="test",
        vault_addr="http://fake-vault:8200",
        vault_token="fake-token",
        database_url="postgresql+asyncpg://fake/fake",
        redis_url="redis://fake:6379/0",
        minio_endpoint="fake-minio:9000",
        minio_access_key="fake",
        minio_secret_key="fake",
    )


@pytest.fixture
def mock_vault_client():
    """Return a mock Vault client."""
    client = MagicMock()
    client.is_authenticated.return_value = True
    return client


@pytest.fixture
def mock_vault(monkeypatch, mock_vault_client):
    """Mock Vault client initialization and secret fetching."""

    def mock_init(settings):
        return mock_vault_client

    def mock_fetch(client, mount, path):
        return {
            "database_url": "postgresql+asyncpg://fake/fake",
            "redis_url": "redis://fake:6379/0",
            "minio_endpoint": "fake-minio:9000",
            "minio_access_key": "fake",
            "minio_secret_key": "fake",
        }

    monkeypatch.setattr("app.infra.vault_client.init_vault_client", mock_init)
    monkeypatch.setattr("app.infra.vault_client.fetch_secrets", mock_fetch)


@pytest.fixture
def mock_db(monkeypatch):
    """Mock database probe."""

    async def mock_probe(*args, **kwargs):
        return ReadinessCheck(name="postgres", status="ok")

    monkeypatch.setattr("app.infra.database.probe_database", mock_probe)
    monkeypatch.setattr("app.services.health_service.probe_database", mock_probe)


@pytest.fixture
def mock_redis(monkeypatch):
    """Mock Redis probe."""

    async def mock_probe(*args, **kwargs):
        return ReadinessCheck(name="redis", status="ok")

    monkeypatch.setattr("app.infra.redis_client.probe_redis", mock_probe)
    monkeypatch.setattr("app.services.health_service.probe_redis", mock_probe)


@pytest.fixture
def mock_minio(monkeypatch):
    """Mock MinIO probe."""

    async def mock_probe(*args, **kwargs):
        return ReadinessCheck(name="minio", status="ok")

    monkeypatch.setattr("app.infra.minio_client.probe_minio", mock_probe)
    monkeypatch.setattr("app.services.health_service.probe_minio", mock_probe)


@pytest.fixture
def mock_pgvector(monkeypatch):
    """Mock pgvector probe."""

    async def mock_probe(*args, **kwargs):
        return ReadinessCheck(name="pgvector", status="ok")

    monkeypatch.setattr("app.services.health_service.probe_pgvector", mock_probe)


@pytest.fixture
async def app(settings, mock_vault, mock_db, mock_redis, mock_minio, mock_vault_client):
    """Return an httpx.AsyncClient for the test app."""
    from contextlib import AsyncExitStack, asynccontextmanager

    import httpx

    from app.core.application import app as fastapi_app

    @asynccontextmanager
    async def test_lifespan(app):
        app.state.settings = settings
        app.state.db_engine = None
        app.state.redis = None
        app.state.minio = None
        app.state.vault_client = mock_vault_client
        yield

    fastapi_app.router.lifespan_context = test_lifespan

    async with AsyncExitStack() as stack:
        await stack.enter_async_context(test_lifespan(fastapi_app))
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=fastapi_app), base_url="http://test"
        ) as client:
            yield client


# ── Phase 2: Dataset Pipeline Fixtures ──


@pytest.fixture
def raw_issue_record():
    """Return a sample raw issue record."""
    return {
        "repo": "test/repo",
        "issue_number": 1,
        "title": "Test issue",
        "body": "Body text",
        "labels": ["bug"],
        "state": "closed",
        "created_at": "2024-01-01T00:00:00Z",
        "closed_at": "2024-01-02T00:00:00Z",
        "updated_at": "2024-01-02T00:00:00Z",
        "author_association": "CONTRIBUTOR",
        "comments_count": 2,
        "comments_url": "https://api.github.com/repos/test/repo/issues/1/comments",
        "comments": [],
        "html_url": "https://github.com/test/repo/issues/1",
    }


@pytest.fixture
def processed_issue_record():
    """Return a sample processed issue record."""
    return {
        "id": "test/repo#1",
        "repo": "test/repo",
        "issue_number": 1,
        "title": "Test issue",
        "body": "Body text",
        "comments": [],
        "original_labels": ["bug"],
        "mapped_label": "bug",
        "created_at": "2024-01-01T00:00:00Z",
        "closed_at": "2024-01-02T00:00:00Z",
        "classifier_text": "Test issue\n\nBody text",
        "rag_text": "Test issue\n\nBody text",
        "source_url": "https://github.com/test/repo/issues/1",
    }


@pytest.fixture
def sample_label_mapping():
    """Return a sample label mapping dict."""
    return {
        "classes": {
            "bug": ["bug", "Bug", "type:bug"],
            "feature": ["feature", "enhancement", "type:feature"],
            "docs": ["documentation", "docs", "type:documentation"],
            "question": ["question", "help wanted", "type:question"],
        },
        "unmapped_policy": "exclude",
        "ambiguous_policy": "first_match",
        "priority_order": ["bug", "feature", "docs", "question"],
    }


# ── Phase 3: Classifier Fixtures ──


@pytest.fixture
def prediction_record():
    """Return a sample PredictionRecord."""
    from app.domain.classifier import PredictionRecord

    return PredictionRecord(
        record_id="fastapi/fastapi#1000",
        approach="classical",
        label_true="bug",
        label_predicted="bug",
        confidence=0.92,
        model_version="0.1.0",
        latency_ms=12.3,
    )


@pytest.fixture
def approach_metrics_completed():
    """Return a completed ApproachMetrics."""
    from app.domain.classifier import ApproachMetrics

    return ApproachMetrics(
        name="classical",
        version="0.1.0",
        status="completed",
        accuracy=0.82,
        macro_f1=0.79,
        per_class_f1={"bug": 0.85, "feature": 0.78, "docs": 0.76, "question": 0.77},
        confusion_matrix=[[25, 2, 1, 0], [1, 20, 2, 1], [0, 1, 18, 2], [1, 0, 2, 15]],
        latency={"p50": 10.0, "p95": 25.0},
        cost=None,
        artifact_path="artifacts/classifiers/classical",
        predictions_path="artifacts/classifiers/classical/predictions.jsonl",
        metrics_path="artifacts/classifiers/classical/metrics.json",
        config={"model_type": "tfidf_logreg"},
        provider_backend="sklearn",
        secret_source=None,
        run_id=None,
        run_logger_backend=None,
        minio_reference=None,
    )


@pytest.fixture
def approach_metrics_skipped():
    """Return a skipped ApproachMetrics."""
    from app.domain.classifier import ApproachMetrics

    return ApproachMetrics(
        name="llm_baseline",
        version="0.1.0",
        status="skipped",
        skip_reason="Azure OpenAI credentials not available",
    )


@pytest.fixture
def evaluation_report(approach_metrics_completed, approach_metrics_skipped):
    """Return a sample EvaluationReport."""
    from app.domain.classifier import EvaluationReport, SkippedApproach

    return EvaluationReport(
        dataset_test_hash="abc123",
        approaches=[approach_metrics_completed],
        skipped_approaches=[
            SkippedApproach(
                name="llm_baseline", skip_reason="Azure OpenAI credentials not available"
            )
        ],
        generated_at="2026-05-19T00:00:00Z",
    )


@pytest.fixture
def golden_set_item():
    """Return a sample GoldenSetItem."""
    from app.domain.classifier import GoldenSetItem

    return GoldenSetItem(
        id="golden-001",
        title="App crashes on startup",
        body="When I run the app it crashes immediately.",
        label="bug",
    )


@pytest.fixture
def model_card():
    """Return a sample ModelCard."""
    from app.domain.classifier import ModelCard

    return ModelCard(
        model_version="0.1.0",
        architecture_name="distilbert-base-uncased",
        training_data_hash="hash123",
        artifact_sha256="sha256abc",
        hyperparameters={"epochs": 3, "learning_rate": 5e-5},
        freeze_policy="none",
        metrics={"accuracy": 0.85, "macro_f1": 0.82},
        training_run_id="run-abc",
        redaction_applied=True,
    )


@pytest.fixture
def classifier_request():
    """Return a sample ClassifierRequest."""
    from app.domain.classifier import ClassifierRequest

    return ClassifierRequest(
        title="App crashes on startup",
        body="When I run the app it crashes immediately.",
    )


@pytest.fixture
def classifier_prediction():
    """Return a sample ClassifierPrediction."""
    from app.domain.classifier import ClassifierPrediction

    return ClassifierPrediction(
        label="bug",
        confidence=0.92,
        model_version="0.1.0",
        request_id="req-001",
    )
