"""RAG generation client — grounded answer generation adapter seams."""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import re
from abc import ABC, abstractmethod

from app.domain.rag import GroundedAnswer, RetrievalResult

logger = logging.getLogger(__name__)

_JSON_PATTERN = re.compile(r"\{.*\}", re.DOTALL)

_GENERATION_SYSTEM_PROMPT = (
    "You are a maintainer assistant answering questions based ONLY on the "
    "retrieved evidence provided below. If the evidence is insufficient to "
    "answer the question, you MUST set insufficient_evidence to true and "
    "explain why. Never invent information not present in the evidence.\n\n"
    "Respond with a JSON object with keys: answer (string), "
    "supporting_chunk_ids (list of strings), insufficient_evidence (boolean), "
    "limitations (list of strings, optional)."
)


class BaseGenerationClient(ABC):
    """Abstract generation client for grounded answer production."""

    @property
    @abstractmethod
    def provider_backend(self) -> str: ...

    @abstractmethod
    async def generate(
        self,
        question: str,
        retrieved: list[RetrievalResult],
    ) -> GroundedAnswer: ...


class FakeGenerationClient(BaseGenerationClient):
    """Fake generation adapter for automated tests.

    Produces deterministic answers derived from the question hash so that
    service tests can verify response shaping without real API calls.
    """

    def __init__(self) -> None:
        pass

    @property
    def provider_backend(self) -> str:
        return "fake_provider"

    def _build_answer(
        self,
        question: str,
        retrieved: list[RetrievalResult],
    ) -> GroundedAnswer:
        if not retrieved:
            return GroundedAnswer(
                answer="Insufficient evidence to answer the question.",
                supporting_chunk_ids=[],
                insufficient_evidence=True,
                limitations=["No relevant chunks found"],
            )
        top_chunks = retrieved[:3]
        answer = " ".join(chunk.chunk.content.strip() for chunk in top_chunks)
        if not answer:
            key = _hash_text(question)
            answer = f"Grounded answer for question {key}."
        return GroundedAnswer(
            answer=answer[:500],
            supporting_chunk_ids=[chunk.chunk.chunk_id for chunk in top_chunks],
            insufficient_evidence=False,
            limitations=None,
        )

    async def generate(
        self,
        question: str,
        retrieved: list[RetrievalResult],
    ) -> GroundedAnswer:
        return self._build_answer(question, retrieved)


def _hash_text(text: str) -> int:
    return int(hashlib.sha256(text.encode()).hexdigest(), 16) & 0x7FFFFFFF


class AzureGenerationClient(BaseGenerationClient):
    """Azure OpenAI grounded generation via LangChain AzureChatOpenAI.

    Wired when Azure credentials are present at runtime.
    """

    _DEFAULT_API_VERSION = "2024-10-21"

    def __init__(
        self,
        *,
        endpoint: str,
        api_key: str,
        deployment_name: str,
        timeout_seconds: int = 30,
    ) -> None:
        self._endpoint = endpoint
        self._api_key = api_key
        self._deployment_name = deployment_name
        self._timeout_seconds = timeout_seconds
        self._model: object | None = None

    @property
    def provider_backend(self) -> str:
        return "azure_openai"

    def _ensure_model(self) -> None:
        if self._model is not None:
            return
        try:
            from langchain_core.messages import HumanMessage, SystemMessage
            from langchain_openai import AzureChatOpenAI
        except ImportError as exc:
            raise RuntimeError(
                "Azure OpenAI generation requires the llm optional dependencies "
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

    def _build_evidence_prompt(self, question: str, retrieved: list[RetrievalResult]) -> str:
        chunks_text = "\n\n---\n\n".join(
            f"[chunk_id: {r.chunk.chunk_id}]\n{r.chunk.content[:2000]}" for r in retrieved[:10]
        )
        return (
            f"Question: {question}\n\n"
            f"Retrieved evidence ({len(retrieved)} chunks):\n\n"
            f"{chunks_text}"
        )

    async def generate(
        self,
        question: str,
        retrieved: list[RetrievalResult],
    ) -> GroundedAnswer:
        self._ensure_model()
        evidence = self._build_evidence_prompt(question, retrieved)
        try:
            response = await asyncio.wait_for(
                self._model.ainvoke(
                    [
                        self._system_message_cls(content=_GENERATION_SYSTEM_PROMPT),
                        self._human_message_cls(content=evidence),
                    ]
                ),
                timeout=self._timeout_seconds,
            )
        except TimeoutError:
            return GroundedAnswer(
                answer="Generation timed out. Please try again with a narrower question.",
                supporting_chunk_ids=[],
                insufficient_evidence=True,
                limitations=["Generation request exceeded timeout"],
            )
        except Exception as exc:
            logger.warning("Azure generation failed: %s", exc)
            raise
        return _parse_generation_response(
            str(response.content),
            [r.chunk.chunk_id for r in retrieved],
        )


def _parse_generation_response(
    content: str,
    available_chunk_ids: list[str],
) -> GroundedAnswer:
    json_match = re.search(r"\{.*\}", content, re.DOTALL)
    if json_match:
        try:
            data = json.loads(json_match.group())
            answer = data.get("answer", content.strip()[:500])
            supporting_chunk_ids = [
                cid for cid in data.get("supporting_chunk_ids", []) if cid in available_chunk_ids
            ]
            return GroundedAnswer(
                answer=answer,
                supporting_chunk_ids=supporting_chunk_ids,
                insufficient_evidence=bool(data.get("insufficient_evidence", False)),
                limitations=data.get("limitations"),
            )
        except json.JSONDecodeError:
            pass
    return GroundedAnswer(
        answer=content.strip()[:500],
        supporting_chunk_ids=[],
        insufficient_evidence=True,
        limitations=["Could not parse structured generation output"],
    )


def resolve_generation_client(settings: object | None = None) -> BaseGenerationClient:
    """Return a generation client based on settings or Azure env vars."""
    endpoint = (
        getattr(settings, "rag_azure_generation_endpoint", None)
        or getattr(settings, "azure_openai_endpoint", None)
        or os.environ.get("RAG_AZURE_GENERATION_ENDPOINT")
    )
    api_key = (
        getattr(settings, "rag_azure_generation_api_key", None)
        or _secret_value(getattr(settings, "azure_openai_api_key", None))
        or os.environ.get("RAG_AZURE_GENERATION_API_KEY")
    )
    model = (
        getattr(settings, "rag_azure_generation_model", None)
        or getattr(settings, "azure_openai_model", None)
        or os.environ.get("RAG_AZURE_GENERATION_MODEL")
    )
    if endpoint and api_key and model:
        timeout = int(
            getattr(settings, "rag_generation_timeout_seconds", None)
            or os.environ.get("RAG_GENERATION_TIMEOUT_SECONDS", "30")
        )
        return AzureGenerationClient(
            endpoint=endpoint,
            api_key=api_key,
            deployment_name=model,
            timeout_seconds=timeout,
        )
    return FakeGenerationClient()


def _secret_value(value: object | None) -> str | None:
    if value is None:
        return None
    getter = getattr(value, "get_secret_value", None)
    if getter is not None:
        return str(getter())
    return str(value)


__all__ = [
    "BaseGenerationClient",
    "FakeGenerationClient",
    "AzureGenerationClient",
    "resolve_generation_client",
]
