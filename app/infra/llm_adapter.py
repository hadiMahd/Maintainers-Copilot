"""Project-owned tool-calling LLM adapter seam."""

from __future__ import annotations

from typing import Any

from app.core.config import AppSettings
from app.domain.chat import ConversationMessage
from app.domain.chat_tools import LLMCompletion, LLMToolCall, ToolDefinition
from app.domain.errors import LLMUnavailableError
from app.infra.prompt_registry import PromptBundle


class BaseChatLLMAdapter:
    """Abstract tool-calling LLM interface used by the chat graph."""

    async def generate(
        self,
        *,
        messages: list[ConversationMessage],
        prompts: PromptBundle,
        tools: list[ToolDefinition],
        request_id: str,
        trace_id: str | None,
    ) -> LLMCompletion:
        raise NotImplementedError


class FakeLLMAdapter(BaseChatLLMAdapter):
    """Deterministic fake adapter that returns scripted completions."""

    def __init__(self, completions: list[LLMCompletion] | None = None) -> None:
        self._completions = list(completions or [])
        self.calls: list[dict[str, Any]] = []

    async def generate(
        self,
        *,
        messages: list[ConversationMessage],
        prompts: PromptBundle,
        tools: list[ToolDefinition],
        request_id: str,
        trace_id: str | None,
    ) -> LLMCompletion:
        self.calls.append(
            {
                "messages": [message.model_dump() for message in messages],
                "prompt_version": prompts.version,
                "tool_names": [tool.name for tool in tools],
                "request_id": request_id,
                "trace_id": trace_id,
            }
        )
        if self._completions:
            return self._completions.pop(0)
        return LLMCompletion(message="I do not need a tool for this request.")


class AzureChatLLMAdapter(BaseChatLLMAdapter):
    """Azure OpenAI tool-calling seam via LangChain.

    The fake adapter is used in tests. This adapter remains intentionally thin and
    raises a safe unavailability error if the provider is not configured.
    """

    def __init__(self, settings: AppSettings) -> None:
        self._settings = settings

    async def generate(
        self,
        *,
        messages: list[ConversationMessage],
        prompts: PromptBundle,
        tools: list[ToolDefinition],
        request_id: str,
        trace_id: str | None,
    ) -> LLMCompletion:
        _ = (messages, prompts, tools, request_id, trace_id)
        if (
            self._settings.azure_openai_endpoint is None
            or self._settings.azure_openai_api_key is None
            or self._settings.azure_openai_model is None
        ):
            raise LLMUnavailableError("Tool-calling LLM is not configured")
        raise LLMUnavailableError("Live Azure chat calls are not enabled in automated tests")
