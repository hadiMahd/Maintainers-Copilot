"""LangChain Azure OpenAI summarization adapter with fake adapter seam."""

from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod

from model_server.domain.issue_analysis import IssueSummary
from prompts.summarization import SUMMARIZATION_SYSTEM_PROMPT

logger = logging.getLogger(__name__)


class SummarizationError(Exception):
    """Exception raised when summarization fails at the adapter level."""


class SummarizationTimeout(SummarizationError):
    """Request exceeded the configured timeout."""


class SummarizerUnavailable(SummarizationError):
    """Summarization service is not configured or unavailable."""


class BaseSummarizationAdapter(ABC):
    """Abstract summarization adapter used by the summarization service."""

    @property
    @abstractmethod
    def configured(self) -> bool: ...

    @property
    @abstractmethod
    def provider_backend(self) -> str: ...

    @property
    @abstractmethod
    def tracing_backend(self) -> str | None: ...

    @property
    @abstractmethod
    def timeout_seconds(self) -> int: ...

    @abstractmethod
    async def summarize(self, prompt: str, max_sentences: int | None = None) -> IssueSummary: ...


class FakeSummarizationAdapter(BaseSummarizationAdapter):
    """Deterministic fake summarization adapter for automated tests.

    Returns fixed content based on a simple hash of the input prompt so that
    service tests can verify response shaping without real Azure credentials.
    """

    def __init__(self, timeout_seconds: int = 15) -> None:
        self._timeout_seconds = timeout_seconds
        self._should_fail: str | None = None  # "timeout" | "unavailable" | None

    @property
    def configured(self) -> bool:
        return self._should_fail != "unavailable"

    @property
    def provider_backend(self) -> str:
        return "fake_provider"

    @property
    def tracing_backend(self) -> str | None:
        return None

    @property
    def timeout_seconds(self) -> int:
        return self._timeout_seconds

    async def summarize(self, prompt: str, max_sentences: int | None = None) -> IssueSummary:
        if self._should_fail == "unavailable":
            raise SummarizerUnavailable("Fake summarization adapter is not configured")
        if self._should_fail == "timeout":
            raise SummarizationTimeout("Fake summarization adapter timed out")
        key = _hash_prompt(prompt)
        return IssueSummary(
            summary=f"Fake summary for issue {key}",
            key_facts=[f"Fake fact A for {key}", f"Fake fact B for {key}"],
            unresolved_questions=[f"Fake question for {key}"],
            suggested_next_step=f"Investigate issue {key}" if key % 2 == 0 else None,
            limitations=None,
        )

    def set_failure_mode(self, mode: str | None) -> None:
        self._should_fail = mode


def _hash_prompt(prompt: str) -> int:
    return hash(prompt) & 0x7FFFFFFF


class AzureOpenAISummarizationAdapter(BaseSummarizationAdapter):
    """Azure OpenAI summarization via LangChain AzureChatOpenAI."""

    _DEFAULT_API_VERSION = "2024-10-21"

    def __init__(
        self,
        *,
        endpoint: str | None = None,
        api_key: str | None = None,
        deployment_name: str | None = None,
        timeout_seconds: int = 15,
        langsmith_enabled: bool = False,
    ) -> None:
        self._endpoint = endpoint
        self._api_key = api_key
        self._deployment_name = deployment_name
        self._timeout_seconds = timeout_seconds
        self._langsmith_enabled = langsmith_enabled
        self._model: object | None = None

    def _ensure_model(self) -> None:
        if self._model is not None:
            return
        if not self.configured:
            raise SummarizerUnavailable("Azure OpenAI summarization adapter is not configured")
        try:
            from langchain_core.messages import HumanMessage, SystemMessage
            from langchain_openai import AzureChatOpenAI
        except ImportError as exc:
            raise SummarizerUnavailable(
                "Azure OpenAI summarization requires the llm optional dependencies "
                "(install with: uv sync --extra llm)"
            ) from exc
        self._model = AzureChatOpenAI(
            api_version=self._DEFAULT_API_VERSION,
            azure_deployment=self._deployment_name,
            azure_endpoint=self._endpoint,
            api_key=self._api_key,
            temperature=0,
            request_timeout=self._timeout_seconds,
        )
        self._human_message_cls = HumanMessage
        self._system_message_cls = SystemMessage

    @property
    def configured(self) -> bool:
        return bool(self._endpoint and self._api_key and self._deployment_name)

    @property
    def provider_backend(self) -> str:
        return "azure_openai"

    @property
    def tracing_backend(self) -> str | None:
        return "langsmith" if self._langsmith_enabled else None

    @property
    def timeout_seconds(self) -> int:
        return self._timeout_seconds

    @property
    def supports_next_step(self) -> bool:
        return True

    async def summarize(self, prompt: str, max_sentences: int | None = None) -> IssueSummary:
        self._ensure_model()
        try:
            response = await asyncio.wait_for(
                self._model.ainvoke([
                    self._system_message_cls(content=SUMMARIZATION_SYSTEM_PROMPT),
                    self._human_message_cls(content=prompt),
                ]),
                timeout=self._timeout_seconds,
            )
        except TimeoutError:
            raise SummarizationTimeout(
                f"Summarization request exceeded {self._timeout_seconds}s timeout"
            ) from None
        except Exception as exc:
            raise SummarizationError(f"Summarization failed: {exc}") from exc
        return _parse_summarization_response(response.content)


def _parse_summarization_response(content: str) -> IssueSummary:
    import json
    import re

    json_match = re.search(r"\{.*\}", content, re.DOTALL)
    if json_match:
        try:
            data = json.loads(json_match.group())
            return IssueSummary(
                summary=data.get("summary", "No summary produced"),
                key_facts=data.get("key_facts", []),
                unresolved_questions=data.get("unresolved_questions", []),
                suggested_next_step=data.get("suggested_next_step"),
                limitations=None,
            )
        except json.JSONDecodeError:
            pass
    return IssueSummary(
        summary=content.strip()[:500],
        key_facts=[],
        unresolved_questions=[],
    )
