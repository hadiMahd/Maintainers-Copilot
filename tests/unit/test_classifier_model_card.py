"""Tests for model card schema validation (separate from hash tests)."""

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.domain.classifier import ModelCard
from app.infra.mlflow.tracking import build_run_metadata, save_run_metadata
from app.infra.redaction import redact_model_card


class TestModelCardValidation:
    """Tests for model card structural validation rules."""

    def test_model_card_rejects_empty_version(self):
        """Model card requires a semantic version string."""
        with pytest.raises(ValidationError):
            ModelCard(
                model_version="",
                architecture_name="distilbert-base-uncased",
                training_data_hash="abc",
                artifact_sha256="def",
                hyperparameters={},
                freeze_policy="none",
                metrics={},
            )

    def test_model_card_rejects_missing_hash_fields(self):
        """Model card requires both training_data_hash and artifact_sha256."""
        card = ModelCard(
            model_version="0.1.0",
            architecture_name="distilbert-base-uncased",
            training_data_hash="abc123",
            artifact_sha256="def456",
            hyperparameters={},
            freeze_policy="none",
            metrics={},
        )
        assert card.training_data_hash == "abc123"
        assert card.artifact_sha256 == "def456"

    def test_model_card_redaction_removes_secrets(self):
        """Redacted model card must not contain secrets."""
        card_dict = {
            "model_version": "0.1.0",
            "architecture_name": "distilbert-base-uncased",
            "training_data_hash": "abc123",
            "artifact_sha256": "def456",
            "hyperparameters": {"lr": 5e-5},
            "freeze_policy": "none",
            "metrics": {"accuracy": 0.85},
            "api_key": "sk-secret-key-12345678901234567890",
        }
        redacted = redact_model_card(card_dict)
        assert redacted["api_key"] == "[REDACTED]"
        assert redacted["redaction_applied"] is True

    def test_model_card_json_roundtrip(self):
        """Model card survives JSON serialization roundtrip."""
        card = ModelCard(
            model_version="0.1.0",
            architecture_name="distilbert-base-uncased",
            training_data_hash="abc123",
            artifact_sha256="def456",
            hyperparameters={"epochs": 3, "lr": 5e-5},
            freeze_policy="none",
            metrics={"accuracy": 0.85},
            training_run_id="run-123",
        )
        json_str = card.model_dump_json()
        loaded = ModelCard(**json.loads(json_str))
        assert loaded.model_version == card.model_version
        assert loaded.artifact_sha256 == card.artifact_sha256


class TestRunMetadata:
    """Tests for MLflow run metadata."""

    def test_build_run_metadata_applies_redaction(self):
        """Run metadata is redacted when redaction_applied=True."""
        metadata = build_run_metadata(
            run_id="run-xyz",
            tracking_uri="http://mlflow:5000",
            artifact_uri="s3://bucket/path",
            started_at="2026-05-19T00:00:00Z",
            parameters={"lr": 5e-5, "api_key": "sk-secret-key-that-should-be-redacted-long"},
            redaction_applied=True,
        )
        assert metadata["redaction_applied"] is True
        assert metadata["run_id"] == "run-xyz"

    def test_build_run_metadata_without_redaction(self):
        """Run metadata preserves fields when redaction_applied=False."""
        metadata = build_run_metadata(
            run_id="run-123",
            tracking_uri="http://mlflow:5000",
            artifact_uri="s3://mlflow/artifacts/run-123",
            started_at="2026-05-19T00:00:00Z",
            redaction_applied=False,
        )
        assert metadata["run_id"] == "run-123"
        assert metadata["backend"] == "mlflow"

    def test_save_and_load_run_metadata(self, tmp_path):
        """Run metadata survives save/load roundtrip."""
        metadata = build_run_metadata(
            run_id="run-456",
            tracking_uri="http://mlflow:5000",
            artifact_uri="s3://mlflow/artifacts/run-456",
            started_at="2026-05-19T00:00:00Z",
        )
        path = str(tmp_path / "run_metadata.json")
        save_run_metadata(metadata, path)
        loaded = json.loads(Path(path).read_text())
        assert loaded["run_id"] == "run-456"
        assert loaded["backend"] == "mlflow"
