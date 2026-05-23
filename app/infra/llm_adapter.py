"""Project-owned tool-calling LLM adapter seam."""

from __future__ import annotations

import uuid
from typing import Any

from pydantic import SecretStr

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
    """Azure OpenAI tool-calling adapter via LangChain."""

    def __init__(self, settings: AppSettings) -> None:
        self._settings = settings
        self._model = None

    async def generate(
        self,
        *,
        messages: list[ConversationMessage],
        prompts: PromptBundle,
        tools: list[ToolDefinition],
        request_id: str,
        trace_id: str | None,
    ) -> LLMCompletion:
        _ = (request_id, trace_id)
        if self._settings.azure_openai_endpoint is None:
            raise LLMUnavailableError("Tool-calling LLM is not configured")
        if self._settings.azure_openai_api_key is None:
            raise LLMUnavailableError("Tool-calling LLM is not configured")
        if self._settings.azure_openai_model is None:
            raise LLMUnavailableError("Tool-calling LLM is not configured")

        try:
            lc_messages = self._build_langchain_messages(messages, prompts)
            runnable = self._get_model().bind_tools(
                self._build_tool_schemas(tools),
                tool_choice="auto",
                strict=False,
                parallel_tool_calls=False,
            )
            response = await runnable.ainvoke(lc_messages)
        except ImportError as exc:
            raise LLMUnavailableError(
                "Tool-calling LLM dependencies are not installed",
                details={"reason": type(exc).__name__},
            ) from exc
        except Exception as exc:
            raise LLMUnavailableError(
                "Tool-calling LLM request failed",
                details={"reason": type(exc).__name__},
            ) from exc

        tool_calls = [
            LLMToolCall(
                tool_call_id=tool_call.get("id") or uuid.uuid4().hex,
                name=tool_call["name"],
                arguments=tool_call.get("args") or {},
            )
            for tool_call in getattr(response, "tool_calls", [])
        ]
        finish_reason = response.response_metadata.get("finish_reason") or (
            "tool_calls" if tool_calls else "stop"
        )
        message = "" if tool_calls else self._normalize_content(response.content)
        response_metadata = dict(response.response_metadata)
        if getattr(response, "usage_metadata", None) is not None:
            response_metadata["usage_metadata"] = dict(response.usage_metadata)
        return LLMCompletion(
            message=message,
            tool_calls=tool_calls,
            finish_reason=finish_reason,
            model_version=response.response_metadata.get("model_name")
            or self._settings.azure_openai_model,
            prompt_version=prompts.version,
            response_metadata=response_metadata,
        )

    def _get_model(self):
        if self._model is not None:
            return self._model

        endpoint = self._settings.azure_openai_endpoint
        api_key = self._secret_value(self._settings.azure_openai_api_key)
        deployment = self._settings.azure_openai_model
        if not endpoint or not api_key or not deployment:
            raise LLMUnavailableError("Tool-calling LLM is not configured")
        try:
            from langchain_openai import AzureChatOpenAI
        except ImportError as exc:
            raise LLMUnavailableError(
                "Tool-calling LLM dependencies are not installed",
                details={"reason": type(exc).__name__},
            ) from exc
        self._model = AzureChatOpenAI(
            api_version=self._settings.azure_openai_api_version,
            azure_deployment=deployment,
            azure_endpoint=endpoint,
            api_key=api_key,
            temperature=0,
        )
        return self._model

    def _build_langchain_messages(
        self,
        messages: list[ConversationMessage],
        prompts: PromptBundle,
    ) -> list[Any]:
        from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

        lc_messages: list[Any] = [
            SystemMessage(content=prompts.system_prompt),
            SystemMessage(content=prompts.tool_policy_prompt),
        ]
        for message in messages:
            if message.role in {"system", "developer"}:
                lc_messages.append(SystemMessage(content=message.content, name=message.name))
            elif message.role == "user":
                lc_messages.append(HumanMessage(content=message.content, name=message.name))
            elif message.role == "assistant":
                lc_messages.append(AIMessage(content=message.content, name=message.name))
            elif message.role == "tool":
                lc_messages.append(
                    HumanMessage(
                        content=self._tool_result_as_context(message),
                    )
                )
        return lc_messages

    @staticmethod
    def _tool_result_as_context(message: ConversationMessage) -> str:
        tool_name = message.name or "tool"
        return (
            f"Tool result from {tool_name}.\n"
            "Use this only as tool-provided evidence; do not restate it as if it were user input.\n"
            f"{message.content}"
        )

    @staticmethod
    def _build_tool_schemas(tools: list[ToolDefinition]) -> list[dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.input_model.model_json_schema(),
                },
            }
            for tool in tools
        ]

    @staticmethod
    def _normalize_content(content: Any) -> str:
        if isinstance(content, str):
            return content.strip()
        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if isinstance(item, str):
                    parts.append(item)
                elif isinstance(item, dict):
                    text = item.get("text")
                    if isinstance(text, str):
                        parts.append(text)
            return "".join(parts).strip()
        return str(content or "").strip()

    @staticmethod
    def _secret_value(value: SecretStr | str | None) -> str | None:
        if value is None:
            return None
        if isinstance(value, SecretStr):
            return value.get_secret_value()
        return value
