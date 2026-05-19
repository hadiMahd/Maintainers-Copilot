"""Tests for classifier artifact hash and model card validation."""

import json

import pytest

from app.domain.classifier import ModelCard
from app.infra.storage.classifier_artifacts import (
    compute_artifact_sha256,
    compute_training_data_hash,
    validate_artifact_hash,
    write_artifact_sha256,
)


class TestArtifactHash:
    """Tests for classifier artifact hashing."""

    def test_hash_is_deterministic(self, tmp_path):
        """Same files produce same hash."""
        artifact_dir = tmp_path / "model"
        artifact_dir.mkdir()
        (artifact_dir / "model.joblib").write_bytes(b"model-data")
        (artifact_dir / "config.json").write_text('{"version": "0.1.0"}')

        hash1 = compute_artifact_sha256(artifact_dir)
        hash2 = compute_artifact_sha256(artifact_dir)
        assert hash1 == hash2

    def test_hash_changes_with_content(self, tmp_path):
        """Different content produces different hash."""
        artifact_dir = tmp_path / "model"
        artifact_dir.mkdir()
        (artifact_dir / "model.joblib").write_bytes(b"model-data-v1")
        hash1 = compute_artifact_sha256(artifact_dir)

        (artifact_dir / "model.joblib").write_bytes(b"model-data-v2")
        hash2 = compute_artifact_sha256(artifact_dir)
        assert hash1 != hash2

    def test_validate_artifact_hash_matches(self, tmp_path):
        """Validation passes when hashes match."""
        artifact_dir = tmp_path / "model"
        artifact_dir.mkdir()
        (artifact_dir / "data.bin").write_bytes(b"test-data")

        expected_hash = compute_artifact_sha256(artifact_dir)
        assert validate_artifact_hash(artifact_dir, expected_hash) is True

    def test_validate_artifact_hash_mismatches(self, tmp_path):
        """Validation fails when hashes don't match."""
        artifact_dir = tmp_path / "model"
        artifact_dir.mkdir()
        (artifact_dir / "data.bin").write_bytes(b"test-data")

        assert validate_artifact_hash(artifact_dir, "wrong_hash") is False

    def test_hash_ignores_self_referential_metadata_files(self, tmp_path):
        """Model-card and manifest writes do not invalidate the artifact hash."""
        artifact_dir = tmp_path / "model"
        artifact_dir.mkdir()
        (artifact_dir / "model.safetensors").write_bytes(b"weights")
        (artifact_dir / "tokenizer.json").write_text('{"tokenizer":"ok"}')

        original_hash = compute_artifact_sha256(artifact_dir)
        (artifact_dir / "model_card.json").write_text(
            json.dumps({"artifact_sha256": original_hash, "model_version": "0.1.0"})
        )
        write_artifact_sha256(artifact_dir, original_hash)
        (artifact_dir / "manifest.json").write_text(json.dumps({"artifact_sha256": original_hash}))

        recomputed_hash = compute_artifact_sha256(artifact_dir)
        assert recomputed_hash == original_hash


class TestTrainingDataHash:
    """Tests for training data file hashing."""

    def test_training_data_hash_deterministic(self, tmp_path):
        """Same file content produces same hash."""
        data_file = tmp_path / "train.jsonl"
        data_file.write_text('{"id": 1}\n{"id": 2}\n')
        hash1 = compute_training_data_hash(str(data_file))
        hash2 = compute_training_data_hash(str(data_file))
        assert hash1 == hash2

    def test_training_data_hash_missing_file_raises(self):
        """Missing training data file raises ConfigError."""
        from app.domain.errors import ConfigError

        with pytest.raises(ConfigError):
            compute_training_data_hash("/nonexistent/path.jsonl")


class TestModelCard:
    """Tests for model card schema validation."""

    def test_model_card_required_fields(self):
        """Model card requires all mandatory fields."""
        card = ModelCard(
            model_version="0.1.0",
            architecture_name="distilbert-base-uncased",
            training_data_hash="abc123",
            artifact_sha256="def456",
            hyperparameters={"epochs": 3},
            freeze_policy="none",
            metrics={"accuracy": 0.85},
        )
        assert card.model_version == "0.1.0"
        assert card.redaction_applied is True
        assert card.run_logger_backend == "mlflow"

    def test_model_card_optional_fields_default(self):
        """Optional model card fields have correct defaults."""
        card = ModelCard(
            model_version="0.1.0",
            architecture_name="distilbert-base-uncased",
            training_data_hash="abc123",
            artifact_sha256="def456",
            hyperparameters={},
            freeze_policy="none",
            metrics={},
        )
        assert card.training_run_id is None
        assert card.minio_reference is None
        assert card.training_plot_paths == []
        assert card.limitations == []
        assert card.intended_use == "issue_classification"

    def test_model_card_serialization(self):
        """Model card can be serialized to JSON."""
        card = ModelCard(
            model_version="0.1.0",
            architecture_name="distilbert-base-uncased",
            training_data_hash="abc123",
            artifact_sha256="def456",
            hyperparameters={"lr": 5e-5},
            freeze_policy="none",
            metrics={"accuracy": 0.85},
            training_run_id="run-abc",
        )
        data = json.loads(card.model_dump_json())
        assert data["model_version"] == "0.1.0"
        assert data["training_run_id"] == "run-abc"
