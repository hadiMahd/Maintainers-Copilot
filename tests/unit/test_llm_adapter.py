"""Unit tests for the chat LLM adapter."""

from __future__ import annotations

import pytest
from langchain_core.messages import AIMessage
from pydantic import SecretStr

from app.core.config import AppSettings
from app.domain.chat import ConversationMessage
from app.domain.chat_tools import ClassifyIssueInput, ClassifyIssueOutput, ToolDefinition
from app.domain.errors import LLMUnavailableError
from app.infra.llm_adapter import AzureChatLLMAdapter
from app.infra.prompt_registry import PromptBundle


class _FakeBoundModel:
    def __init__(self, response: AIMessage) -> None:
        self._response = response
        self.bound_tools = None
        self.bound_kwargs = None
        self.messages = None

    def bind_tools(self, tools, **kwargs):
        self.bound_tools = tools
        self.bound_kwargs = kwargs
        return self

    async def ainvoke(self, messages):
        self.messages = messages
        return self._response


def _settings() -> AppSettings:
    return AppSettings(
        vault_addr="http://vault.local",
        vault_token="token",
        azure_openai_endpoint="https://example.openai.azure.com/",
        azure_openai_api_key=SecretStr("secret-key"),
        azure_openai_model="gpt-5.4-nano",
    )


def _prompts() -> PromptBundle:
    return PromptBundle(
        system_prompt="system rules",
        tool_policy_prompt="tool policy",
        untrusted_context_prompt="untrusted context",
        version="prompt-v1",
    )


def _tools() -> list[ToolDefinition]:
    return [
        ToolDefinition(
            name="classify_issue",
            description="Classify an issue.",
            input_model=ClassifyIssueInput,
            output_model=ClassifyIssueOutput,
            timeout_seconds=5,
        )
    ]


@pytest.mark.asyncio
async def test_azure_chat_adapter_raises_when_required_config_missing():
    adapter = AzureChatLLMAdapter(
        AppSettings(
            vault_addr="http://vault.local",
            vault_token="token",
            azure_openai_endpoint=None,
            azure_openai_api_key=None,
            azure_openai_model=None,
        )
    )
    with pytest.raises(LLMUnavailableError, match="Tool-calling LLM is not configured"):
        await adapter.generate(
            messages=[ConversationMessage(role="user", content="hello")],
            prompts=_prompts(),
            tools=_tools(),
            request_id="req-1",
            trace_id="trace-1",
        )


@pytest.mark.asyncio
async def test_azure_chat_adapter_parses_tool_calls_and_builds_prompt_messages(monkeypatch):
    response = AIMessage(
        content="",
        tool_calls=[
            {
                "name": "classify_issue",
                "args": {"title": "bug report"},
                "id": "call-123",
                "type": "tool_call",
            }
        ],
        response_metadata={"finish_reason": "tool_calls", "model_name": "gpt-5.4-nano"},
    )
    adapter = AzureChatLLMAdapter(_settings())
    fake_model = _FakeBoundModel(response)
    monkeypatch.setattr(adapter, "_get_model", lambda: fake_model)

    completion = await adapter.generate(
        messages=[
            ConversationMessage(role="user", content="please classify this"),
            ConversationMessage(role="tool", name="classify_issue", content="label=bug"),
        ],
        prompts=_prompts(),
        tools=_tools(),
        request_id="req-1",
        trace_id="trace-1",
    )

    assert completion.message == ""
    assert completion.finish_reason == "tool_calls"
    assert completion.model_version == "gpt-5.4-nano"
    assert completion.prompt_version == "prompt-v1"
    assert completion.tool_calls[0].tool_call_id == "call-123"
    assert completion.tool_calls[0].name == "classify_issue"
    assert completion.tool_calls[0].arguments == {"title": "bug report"}
    assert fake_model.bound_tools[0]["function"]["name"] == "classify_issue"
    assert fake_model.bound_kwargs == {
        "tool_choice": "auto",
        "strict": False,
        "parallel_tool_calls": False,
    }
    assert fake_model.messages[0].content == "system rules"
    assert fake_model.messages[1].content == "tool policy"
    assert fake_model.messages[2].content == "please classify this"
    assert "Tool result from classify_issue." in fake_model.messages[3].content


@pytest.mark.asyncio
async def test_azure_chat_adapter_returns_plain_message_when_no_tool_calls(monkeypatch):
    response = AIMessage(
        content=[{"text": "Done."}],
        response_metadata={"model_name": "gpt-5.4-nano"},
        usage_metadata={"input_tokens": 12, "output_tokens": 4, "total_tokens": 16},
    )
    adapter = AzureChatLLMAdapter(_settings())
    monkeypatch.setattr(adapter, "_get_model", lambda: _FakeBoundModel(response))

    completion = await adapter.generate(
        messages=[ConversationMessage(role="user", content="hello")],
        prompts=_prompts(),
        tools=_tools(),
        request_id="req-1",
        trace_id="trace-1",
    )

    assert completion.message == "Done."
    assert completion.finish_reason == "stop"
    assert completion.response_metadata["usage_metadata"]["total_tokens"] == 16
