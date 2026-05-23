"""Tests for MLflow run metadata and MinIO manifest validation."""

import json
from pathlib import Path

from app.infra.mlflow.tracking import build_run_metadata, save_run_metadata
from app.infra.redaction import redact_run_metadata
from app.infra.storage.classifier_artifacts import (
    build_manifest,
    save_manifest,
)


class TestRunMetadataRedaction:
    """Tests for MLflow run metadata redaction."""

    def test_redact_removes_secret_key_patterns(self):
        """Secret key patterns in run metadata are replaced."""
        metadata = {
            "run_id": "run-abc",
            "tracking_uri": "http://mlflow:5000",
            "api_key": "sk-AbCdEf123456789012345678",
        }
        result = redact_run_metadata(metadata)
        assert result["api_key"] == "[REDACTED]"
        assert result["run_id"] == "run-abc"

    def test_redact_marks_redaction_applied(self):
        """Redacted run metadata is marked."""
        metadata = build_run_metadata(
            run_id="run-xyz",
            tracking_uri="http://mlflow:5000",
            artifact_uri="s3://bucket/path",
            started_at="2026-05-19T00:00:00Z",
            parameters={"lr": 5e-5},
            redaction_applied=True,
        )
        assert metadata["redaction_applied"] is True

    def test_run_metadata_persistence_roundtrip(self, tmp_path):
        """Run metadata persists and loads correctly."""
        metadata = build_run_metadata(
            run_id="run-789",
            tracking_uri="http://mlflow:5000",
            artifact_uri="s3://mlflow/artifacts/run-789",
            started_at="2026-05-19T00:00:00Z",
            metrics={"accuracy": 0.85},
        )
        path = str(tmp_path / "metadata.json")
        save_run_metadata(metadata, path)
        loaded = json.loads(Path(path).read_text())
        assert loaded["run_id"] == "run-789"


class TestArtifactManifest:
    """Tests for classifier artifact manifest."""

    def test_build_manifest_with_required_fields(self):
        """Manifest builds with all required fields."""
        manifest = build_manifest(
            model_version="0.1.0",
            approach="transformer",
            artifact_sha256="abc123",
            training_data_hash="def456",
            source_artifact_path="artifacts/classifiers/transformer",
            minio_object_key="classifiers/transformer/v0.1.0",
        )
        assert manifest.model_version == "0.1.0"
        assert manifest.approach == "transformer"
        assert manifest.artifact_sha256 == "abc123"
        assert manifest.uploaded_at is not None

    def test_manifest_serialization_roundtrip(self, tmp_path):
        """Manifest survives JSON serialization roundtrip."""
        manifest = build_manifest(
            model_version="0.1.0",
            approach="transformer",
            artifact_sha256="abc123",
            training_data_hash="def456",
            source_artifact_path="artifacts/classifiers/transformer",
            minio_object_key="classifiers/transformer/v0.1.0",
        )
        path = str(tmp_path / "manifest.json")
        save_manifest(manifest, path)
        loaded = json.loads(Path(path).read_text())
        assert loaded["model_version"] == "0.1.0"
        assert loaded["approach"] == "transformer"

    def test_manifest_no_secrets_in_serialized_form(self, tmp_path):
        """Serialized manifest contains no secrets."""
        manifest = build_manifest(
            model_version="0.1.0",
            approach="transformer",
            artifact_sha256="abc123",
            training_data_hash="def456",
            source_artifact_path="artifacts/classifiers/transformer",
            minio_object_key="classifiers/transformer/v0.1.0",
        )
        path = str(tmp_path / "manifest.json")
        save_manifest(manifest, path)
        content = Path(path).read_text()
        secret_patterns = ["sk-", "password", "secret_key", "api_key"]
        for pattern in secret_patterns:
            assert pattern not in content.lower()
