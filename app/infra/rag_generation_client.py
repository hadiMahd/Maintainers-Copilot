"""RAG generation client — grounded answer generation adapter seams."""

from __future__ import annotations

import hashlib
import json
import logging
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

    def _build_answer(self, question: str, chunk_count: int) -> GroundedAnswer:
        key = _hash_text(question)
        if chunk_count == 0:
            return GroundedAnswer(
                answer="Insufficient evidence to answer the question.",
                supporting_chunk_ids=[],
                insufficient_evidence=True,
                limitations=["No relevant chunks found"],
            )
        return GroundedAnswer(
            answer=f"Answer for question {key}: the evidence suggests a resolution.",
            supporting_chunk_ids=[f"chunk-{key}"],
            insufficient_evidence=False,
            limitations=None,
        )

    async def generate(
        self,
        question: str,
        retrieved: list[RetrievalResult],
    ) -> GroundedAnswer:
        return self._build_answer(question, len(retrieved))


def _hash_text(text: str) -> int:
    return int(hashlib.sha256(text.encode()).hexdigest(), 16) & 0x7FFFFFFF


class AzureGenerationStub(BaseGenerationClient):
    """Azure OpenAI grounded generation stub.

    Config seam — wired when Azure credentials are present.
    Actual AzureChatOpenAI calls are out of scope for the US1 pass.
    """

    def __init__(self, model_name: str = "gpt-4o-mini") -> None:
        self._model_name = model_name

    @property
    def provider_backend(self) -> str:
        return "azure_openai"

    async def generate(
        self,
        question: str,
        retrieved: list[RetrievalResult],
    ) -> GroundedAnswer:
        raise NotImplementedError("Azure grounded generation calls are not implemented in this pass")


def resolve_generation_client() -> BaseGenerationClient:
    return FakeGenerationClient()


__all__ = [
    "BaseGenerationClient",
    "FakeGenerationClient",
    "AzureGenerationStub",
    "resolve_generation_client",
]
