"""Integration tests for the fake-provider LLM classifier baseline."""

import pytest

from app.domain.classifier import VALID_LABELS
from app.infra.llm.classifier_baseline import (
    AZURE_OPENAI_PROVIDER,
    FAKE_PROVIDER,
    FakeClassifierProvider,
    create_classifier_provider,
)


class TestFakeClassifierProvider:
    """Tests for the deterministic fake provider."""

    def test_classify_returns_valid_label(self):
        """Fake provider returns one of the four valid labels."""
        provider = FakeClassifierProvider()
        result = provider.classify(text="some input text", record_id="r1", label_true="bug")
        assert result.label_predicted in VALID_LABELS

    def test_classify_is_deterministic(self):
        """Same input produces same output."""
        provider = FakeClassifierProvider()
        r1 = provider.classify(text="deterministic test", record_id="r1", label_true="bug")
        r2 = provider.classify(text="deterministic test", record_id="r1", label_true="bug")
        assert r1.label_predicted == r2.label_predicted
        assert r1.confidence == r2.confidence

    def test_classify_approach_is_llm_baseline(self):
        """Fake provider uses the llm_baseline approach name."""
        provider = FakeClassifierProvider()
        result = provider.classify(text="test", record_id="r1", label_true="bug")
        assert result.approach == "llm_baseline"

    def test_classify_model_version_customizable(self):
        """Model version can be set on the fake provider."""
        provider = FakeClassifierProvider(model_version="1.2.3-fake")
        result = provider.classify(text="test", record_id="r1", label_true="bug")
        assert result.model_version == "1.2.3-fake"

    def test_classify_has_latency_and_no_cost(self):
        """Fake provider has latency but no cost."""
        provider = FakeClassifierProvider()
        result = provider.classify(text="test", record_id="r1", label_true="bug")
        assert result.latency_ms is not None
        assert result.cost_usd is None

    def test_classify_batch(self):
        """Batch classification processes all records."""
        provider = FakeClassifierProvider()
        records = [
            {"id": "r1", "classifier_text": "bug report", "mapped_label": "bug"},
            {"id": "r2", "classifier_text": "new feature", "mapped_label": "feature"},
        ]
        results = provider.classify_batch(records)
        assert len(results) == 2
        assert all(r.label_predicted in VALID_LABELS for r in results)


class TestCreateClassifierProvider:
    """Tests for the provider factory."""

    def test_create_fake_provider(self):
        """Factory creates a fake provider."""
        provider = create_classifier_provider(provider_backend=FAKE_PROVIDER)
        assert isinstance(provider, FakeClassifierProvider)

    def test_create_unsupported_provider_raises(self):
        """Factory raises for unsupported provider backends."""
        with pytest.raises(ValueError, match="Unsupported provider backend"):
            create_classifier_provider(provider_backend="unsupported")

    def test_create_azure_provider_without_required_settings_raises(self):
        """Azure provider requires runtime-resolved connection settings."""
        with pytest.raises(ValueError, match="requires endpoint, api_key, and openai_model"):
            create_classifier_provider(provider_backend=AZURE_OPENAI_PROVIDER)
