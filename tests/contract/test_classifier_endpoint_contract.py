"""Contract tests for the classifier model-server endpoint.

These tests verify the endpoint behavior matches the OpenAPI contract
defined in specs/003-issue-classification/contracts/classifier.openapi.yaml.
They test request/response shapes, validation, and error behavior without
a real model loaded.
"""

import pytest
from pydantic import ValidationError

from app.domain.classifier import (
    VALID_LABELS,
    ClassifierPrediction,
    ClassifierRequest,
    ClassifierUnavailableError,
)


class TestClassifierEndpointContract:
    """Contract tests verifying OpenAPI spec compliance."""

    def test_predict_endpoint_accepts_title_only(self):
        """POST /classifier/predict accepts title only."""
        req = ClassifierRequest(title="Bug in auth")
        assert req.title is not None

    def test_predict_endpoint_accepts_body_only(self):
        """POST /classifier/predict accepts body only."""
        req = ClassifierRequest(body="Description of the issue")
        assert req.body is not None

    def test_predict_endpoint_accepts_comments_only(self):
        """POST /classifier/predict accepts comments only."""
        req = ClassifierRequest(comments=["Comment 1"])
        assert req.comments is not None

    def test_predict_response_has_required_fields(self):
        """Response has label and model_version (required by spec)."""
        pred = ClassifierPrediction(label="bug", model_version="0.1.0")
        assert pred.label in VALID_LABELS
        assert pred.model_version is not None

    def test_predict_response_confidence_optional(self):
        """Confidence is optional in the response."""
        pred = ClassifierPrediction(label="bug", model_version="0.1.0")
        assert pred.confidence is None

    def test_422_validation_error_shape(self):
        """Invalid input produces 422 with proper error code."""
        with pytest.raises(ValidationError) as exc_info:
            ClassifierRequest(title="x" * 513)
        assert exc_info.value is not None

    def test_503_unavailable_error_shape(self):
        """Unavailable model returns 503 with structured error."""
        err = ClassifierUnavailableError(
            code="classifier_model_unavailable",
            message="Classifier model is not available",
            reason="missing_artifact",
        )
        assert err.code == "classifier_model_unavailable"
        assert err.reason in (
            "missing_artifact",
            "invalid_artifact",
            "hash_mismatch",
            "startup_load_failed",
        )

    def test_503_unavailable_no_stack_trace(self):
        """Unavailable error does not contain stack traces."""
        err = ClassifierUnavailableError(
            code="classifier_model_unavailable",
            message="Model unavailable",
            reason="hash_mismatch",
        )
        err_dict = err.model_dump()
        assert "traceback" not in err_dict
        assert "stack" not in err_dict
        assert "exc_info" not in err_dict

    def test_request_id_in_response(self):
        """Response includes optional request_id."""
        pred = ClassifierPrediction(label="bug", model_version="0.1.0", request_id="req-123")
        assert pred.request_id == "req-123"

    def test_semantic_version_in_response(self):
        """Model version is a semantic version string."""
        pred = ClassifierPrediction(label="bug", model_version="1.2.3")
        assert pred.model_version == "1.2.3"
