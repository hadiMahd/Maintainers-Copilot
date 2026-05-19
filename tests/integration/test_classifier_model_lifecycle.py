"""Integration tests for classifier lifecycle and runtime behavior."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.domain.classifier import ClassifierRequest
from model_server.api.classifier import predict
from model_server.infra.classifier_loader import ArtifactLoadError, ClassifierLoader
from model_server.services.classifier_service import ClassifierService


def _build_classical_artifact(artifact_dir: Path) -> tuple[object, str]:
    import joblib
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import Pipeline

    artifact_dir.mkdir(parents=True, exist_ok=True)
    pipeline = Pipeline(
        [
            ("tfidf", TfidfVectorizer()),
            ("clf", LogisticRegression(max_iter=200, random_state=42)),
        ]
    )
    texts = [
        "crash on startup",
        "segmentation fault in parser",
        "please add dark mode",
        "feature request for export",
        "docs typo in readme",
        "how do i configure redis",
    ]
    labels = ["bug", "bug", "feature", "feature", "docs", "question"]
    pipeline.fit(texts, labels)
    joblib.dump(pipeline, artifact_dir / "model.joblib")
    (artifact_dir / "config.json").write_text(
        json.dumps({"version": "0.1.0", "approach": "classical"})
    )
    return pipeline, "docs typo in readme"


def _build_request_with_loader(loader: ClassifierLoader | None) -> SimpleNamespace:
    app = SimpleNamespace(state=SimpleNamespace(classifier_loader=loader))
    state = SimpleNamespace(request_id="req-123")
    return SimpleNamespace(app=app, state=state)


class TestClassifierModelLifecycle:
    """Tests for model loading, hash validation, and unavailable model behavior."""

    def test_missing_artifact_raises_structured_error(self):
        loader = ClassifierLoader(artifact_dir="/nonexistent/path")
        with pytest.raises(ArtifactLoadError) as exc_info:
            loader.load()
        assert exc_info.value.reason == "missing_artifact"

    def test_hash_validation_detects_mismatch(self, tmp_path):
        artifact_dir = tmp_path / "transformer"
        artifact_dir.mkdir()
        (artifact_dir / "model.safetensors").write_bytes(b"original-weights")
        (artifact_dir / "tokenizer.json").write_text('{"tokenizer":"ok"}')
        (artifact_dir / "model_card.json").write_text(
            json.dumps({"model_version": "0.1.0", "artifact_sha256": "wrong"})
        )

        loader = ClassifierLoader(artifact_dir=str(artifact_dir))
        with pytest.raises(ArtifactLoadError) as exc_info:
            loader.load()
        assert exc_info.value.reason == "hash_mismatch"

    def test_loader_predicts_with_loaded_classical_model(self, tmp_path):
        artifact_dir = tmp_path / "classical"
        pipeline, sample_text = _build_classical_artifact(artifact_dir)

        loader = ClassifierLoader(artifact_dir=str(artifact_dir))
        loader.load()

        service = ClassifierService(loader)
        response = service.predict(sample_text, request_id="req-1")
        expected_label = pipeline.predict([sample_text])[0]

        assert response.label == expected_label
        assert response.model_version == "0.1.0"
        assert response.confidence is not None

    def test_loader_resolves_single_nested_artifact_directory(self, tmp_path):
        root_dir = tmp_path / "classical"
        nested_dir = root_dir / "pandas_logreg"
        _build_classical_artifact(nested_dir)

        loader = ClassifierLoader(artifact_dir=str(root_dir))
        loader.load()

        assert loader.is_loaded is True
        assert loader.artifact_kind == "classical"

    def test_route_returns_503_for_unavailable_model(self):
        request = _build_request_with_loader(None)
        response = asyncio.run(predict(ClassifierRequest(title="bug in auth"), request))

        assert response.status_code == 503
        payload = json.loads(response.body)
        assert payload["error"]["code"] == "classifier_model_unavailable"
        assert payload["error"]["details"]["reason"] == "missing_artifact"

    def test_unavailable_error_has_no_stack_trace(self):
        loader = ClassifierLoader(artifact_dir="/nonexistent/path")
        response = loader.get_unavailable_error(request_id="req-1")
        err_dict = response.model_dump()
        assert "traceback" not in err_dict
        assert "exc_info" not in err_dict
        assert "stack" not in err_dict
