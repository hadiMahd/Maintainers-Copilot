"""Tests for classifier domain schema validation."""

import pytest
from pydantic import ValidationError

from app.domain.classifier import (
    VALID_LABELS,
    ClassifierPrediction,
    ClassifierRequest,
    ClassifierUnavailableError,
)


class TestClassifierRequest:
    """Tests for classifier request schema validation."""

    def test_valid_title_only(self):
        """Request with title only is valid."""
        req = ClassifierRequest(title="Bug in login")
        assert req.title == "Bug in login"
        assert req.body is None
        assert req.comments is None

    def test_valid_body_only(self):
        """Request with body only is valid."""
        req = ClassifierRequest(body="Details about the bug")
        assert req.body == "Details about the bug"

    def test_valid_all_fields(self):
        """Request with all fields is valid."""
        req = ClassifierRequest(
            title="Bug",
            body="Details",
            comments=["Comment 1", "Comment 2"],
        )
        assert req.title == "Bug"
        assert req.body == "Details"
        assert len(req.comments) == 2

    def test_classifier_text_combines_fields(self):
        """classifier_text() joins title, body, and comments."""
        req = ClassifierRequest(
            title="Bug",
            body="Details",
            comments=["Comment"],
        )
        text = req.classifier_text()
        assert "Bug" in text
        assert "Details" in text
        assert "Comment" in text

    def test_classifier_text_title_only(self):
        """classifier_text() with title only returns just the title."""
        req = ClassifierRequest(title="Bug in login")
        assert req.classifier_text() == "Bug in login"

    def test_title_max_length(self):
        """Title respects max length of 512."""
        long_title = "x" * 512
        req = ClassifierRequest(title=long_title)
        assert len(req.title) == 512

    def test_title_exceeds_max_length_raises(self):
        """Title exceeding 512 raises validation error."""
        with pytest.raises(ValidationError):
            ClassifierRequest(title="x" * 513)

    def test_body_max_length(self):
        """Body respects max length of 16000."""
        long_body = "x" * 16000
        req = ClassifierRequest(body=long_body)
        assert len(req.body) == 16000

    def test_body_exceeds_max_length_raises(self):
        """Body exceeding 16000 raises validation error."""
        with pytest.raises(ValidationError):
            ClassifierRequest(body="x" * 16001)

    def test_comments_max_items(self):
        """Comments respects max 100 items."""
        comments = ["comment"] * 100
        req = ClassifierRequest(comments=comments)
        assert len(req.comments) == 100

    def test_comments_exceeds_max_items_raises(self):
        """More than 100 comments raises validation error."""
        with pytest.raises(ValidationError):
            ClassifierRequest(comments=["c"] * 101)

    def test_empty_request_raises(self):
        """At least one non-empty text field is required."""
        with pytest.raises(ValidationError):
            ClassifierRequest()


class TestClassifierPrediction:
    """Tests for classifier prediction schema validation."""

    def test_valid_prediction(self):
        """Prediction with all fields is valid."""
        pred = ClassifierPrediction(label="bug", confidence=0.92, model_version="0.1.0")
        assert pred.label == "bug"
        assert pred.confidence == 0.92
        assert pred.model_version == "0.1.0"

    def test_prediction_without_confidence(self):
        """Prediction without confidence is valid."""
        pred = ClassifierPrediction(label="bug", model_version="0.1.0")
        assert pred.confidence is None

    def test_prediction_invalid_label_raises(self):
        """Prediction with invalid label raises validation error."""
        with pytest.raises(ValidationError):
            ClassifierPrediction(label="invalid", model_version="0.1.0")

    def test_prediction_all_valid_labels(self):
        """All four valid labels are accepted."""
        for label in VALID_LABELS:
            pred = ClassifierPrediction(label=label, model_version="0.1.0")
            assert pred.label == label

    def test_prediction_semantic_version(self):
        """Model version is a required string."""
        pred = ClassifierPrediction(label="bug", model_version="1.2.3")
        assert pred.model_version == "1.2.3"


class TestClassifierUnavailableError:
    """Tests for classifier unavailable error schema validation."""

    def test_valid_unavailable_error(self):
        """Unavailable error with all fields is valid."""
        err = ClassifierUnavailableError(
            code="classifier_model_unavailable",
            message="Model not loaded",
            reason="missing_artifact",
        )
        assert err.code == "classifier_model_unavailable"
        assert err.reason == "missing_artifact"

    def test_all_valid_reasons(self):
        """All four valid reasons are accepted."""
        for reason in [
            "missing_artifact",
            "invalid_artifact",
            "hash_mismatch",
            "startup_load_failed",
        ]:
            err = ClassifierUnavailableError(
                code="classifier_model_unavailable",
                message="Error",
                reason=reason,
            )
            assert err.reason == reason

    def test_invalid_code_raises(self):
        """Invalid error code raises validation error."""
        with pytest.raises(ValidationError):
            ClassifierUnavailableError(
                code="invalid_code",
                message="Error",
                reason="missing_artifact",
            )

    def test_invalid_reason_raises(self):
        """Invalid reason raises validation error."""
        with pytest.raises(ValidationError):
            ClassifierUnavailableError(
                code="classifier_model_unavailable",
                message="Error",
                reason="invalid_reason",
            )
