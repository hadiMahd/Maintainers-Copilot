"""Unit tests for summarization adapter timeout and LangSmith behavior."""

from __future__ import annotations

import asyncio

import pytest

from model_server.infra.summarization_adapter import (
    FakeSummarizationAdapter,
    AzureOpenAISummarizationAdapter,
    SummarizationTimeout,
    SummarizerUnavailable,
)


class TestFakeAdapter:
    def test_fake_adapter_is_configured_by_default(self):
        adapter = FakeSummarizationAdapter()
        assert adapter.configured

    def test_fake_adapter_provider_backend(self):
        adapter = FakeSummarizationAdapter()
        assert adapter.provider_backend == "fake_provider"

    def test_fake_adapter_no_tracing(self):
        adapter = FakeSummarizationAdapter()
        assert adapter.tracing_backend is None

    def test_fake_adapter_timeout_default(self):
        adapter = FakeSummarizationAdapter()
        assert adapter.timeout_seconds == 15

    def test_fake_adapter_custom_timeout(self):
        adapter = FakeSummarizationAdapter(timeout_seconds=10)
        assert adapter.timeout_seconds == 10

    async def test_fake_adapter_returns_summary(self):
        adapter = FakeSummarizationAdapter()
        result = await adapter.summarize("test issue")
        assert result.summary
        assert len(result.key_facts) == 2
        assert len(result.unresolved_questions) == 1

    async def test_fake_adapter_returns_different_for_different_input(self):
        adapter = FakeSummarizationAdapter()
        r1 = await adapter.summarize("issue A")
        r2 = await adapter.summarize("issue B")
        assert r1.summary != r2.summary

    async def test_fake_adapter_unavailable_mode(self):
        adapter = FakeSummarizationAdapter()
        adapter.set_failure_mode("unavailable")
        assert not adapter.configured
        with pytest.raises(SummarizerUnavailable):
            await adapter.summarize("test")

    async def test_fake_adapter_timeout_mode(self):
        adapter = FakeSummarizationAdapter()
        adapter.set_failure_mode("timeout")
        with pytest.raises(SummarizationTimeout):
            await adapter.summarize("test")

    def test_fake_adapter_reset_failure_mode(self):
        adapter = FakeSummarizationAdapter()
        adapter.set_failure_mode("timeout")
        adapter.set_failure_mode(None)
        assert adapter.configured


class TestAzureAdapter:
    def test_azure_adapter_not_configured_without_creds(self):
        adapter = AzureOpenAISummarizationAdapter()
        assert not adapter.configured

    def test_azure_adapter_configured_with_creds(self):
        adapter = AzureOpenAISummarizationAdapter(
            endpoint="https://test.openai.azure.com",
            api_key="fake-key",
            deployment_name="gpt-test",
        )
        assert adapter.configured

    def test_azure_adapter_provider_backend(self):
        adapter = AzureOpenAISummarizationAdapter()
        assert adapter.provider_backend == "azure_openai"

    def test_azure_adapter_tracing_backend(self):
        adapter = AzureOpenAISummarizationAdapter(langsmith_enabled=True)
        assert adapter.tracing_backend == "langsmith"

    def test_azure_adapter_no_tracing_when_disabled(self):
        adapter = AzureOpenAISummarizationAdapter(langsmith_enabled=False)
        assert adapter.tracing_backend is None

    def test_azure_adapter_default_timeout(self):
        adapter = AzureOpenAISummarizationAdapter()
        assert adapter.timeout_seconds == 15

    def test_azure_adapter_custom_timeout(self):
        adapter = AzureOpenAISummarizationAdapter(timeout_seconds=10)
        assert adapter.timeout_seconds == 10

    def test_azure_adapter_supports_next_step(self):
        adapter = AzureOpenAISummarizationAdapter()
        assert adapter.supports_next_step

    async def test_azure_adapter_summarize_raises_without_creds(self):
        adapter = AzureOpenAISummarizationAdapter()
        with pytest.raises(SummarizerUnavailable):
            await adapter.summarize("test issue")
