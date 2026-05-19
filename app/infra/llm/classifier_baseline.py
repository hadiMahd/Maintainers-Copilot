"""Azure OpenAI / fake-provider classifier baseline adapter."""

from __future__ import annotations

import hashlib
import json
import re
import time
from typing import Any, Protocol

from prompts.classifier import CLASSIFIER_SYSTEM_PROMPT, classifier_user_prompt

from app.domain.classifier import VALID_LABELS, PredictionRecord

FAKE_PROVIDER = "fake_provider"
AZURE_OPENAI_PROVIDER = "azure_openai"
DEFAULT_AZURE_OPENAI_API_VERSION = "2024-10-21"
_JSON_OBJECT_PATTERN = re.compile(r"\{.*\}", re.DOTALL)


class ClassifierProvider(Protocol):
    """Protocol shared by the fake and real baseline providers."""

    provider_backend: str
    model_version: str

    def classify(
        self,
        text: str,
        record_id: str = "",
        label_true: str = "",
    ) -> PredictionRecord:
        """Return one prediction for one text input."""

    def classify_batch(self, records: list[dict[str, Any]]) -> list[PredictionRecord]:
        """Return predictions for a list of dataset records."""


class FakeClassifierProvider:
    """Deterministic fake provider for testing."""

    def __init__(self, model_version: str = "0.0.1-fake"):
        self.model_version = model_version
        self.provider_backend = FAKE_PROVIDER

    def classify(self, text: str, record_id: str = "", label_true: str = "") -> PredictionRecord:
        text_hash = hashlib.sha256(text.encode()).hexdigest()
        label_index = int(text_hash, 16) % len(VALID_LABELS)
        predicted = VALID_LABELS[label_index]
        return PredictionRecord(
            record_id=record_id,
            approach="llm_baseline",
            label_true=label_true,
            label_predicted=predicted,
            confidence=0.5 + (int(text_hash[:8], 16) % 50) / 100.0,
            model_version=self.model_version,
            latency_ms=1.0,
            cost_usd=None,
        )

    def classify_batch(self, records: list[dict[str, Any]]) -> list[PredictionRecord]:
        results: list[PredictionRecord] = []
        for record in records:
            text = record.get("classifier_text", record.get("text_for_classifier", ""))
            results.append(
                self.classify(
                    text=text,
                    record_id=record.get("id", record.get("record_id", "")),
                    label_true=record.get("mapped_label", record.get("label_mapped", "")),
                )
            )
        return results


class AzureOpenAIClassifierProvider:
    """Classifier provider backed by LangChain AzureChatOpenAI."""

    def __init__(
        self,
        *,
        azure_openai_endpoint: str,
        azure_openai_api_key: str,
        azure_openai_model: str,
        api_version: str = DEFAULT_AZURE_OPENAI_API_VERSION,
        model_version: str | None = None,
    ):
        try:
            from langchain_core.messages import HumanMessage, SystemMessage
            from langchain_openai import AzureChatOpenAI
        except ImportError as exc:
            raise ValueError(
                "Azure OpenAI baseline requires the llm optional dependencies "
                "(install with: uv sync --extra llm)"
            ) from exc

        self._human_message_cls = HumanMessage
        self._system_message_cls = SystemMessage
        self._model = AzureChatOpenAI(
            api_version=api_version,
            azure_deployment=azure_openai_model,
            azure_endpoint=azure_openai_endpoint,
            api_key=azure_openai_api_key,
            temperature=0,
        )
        self.model_version = model_version or azure_openai_model
        self.provider_backend = AZURE_OPENAI_PROVIDER

    def classify(self, text: str, record_id: str = "", label_true: str = "") -> PredictionRecord:
        started = time.monotonic()
        response = self._model.invoke(
            [
                self._system_message_cls(content=CLASSIFIER_SYSTEM_PROMPT),
                self._human_message_cls(content=classifier_user_prompt(text)),
            ]
        )
        elapsed_ms = (time.monotonic() - started) * 1000
        payload = _parse_classifier_response(response.content)
        label = _normalize_label(payload.get("label"))
        confidence = _normalize_confidence(payload.get("confidence"))
        return PredictionRecord(
            record_id=record_id,
            approach="llm_baseline",
            label_true=label_true,
            label_predicted=label,
            confidence=confidence,
            model_version=self.model_version,
            latency_ms=round(elapsed_ms, 2),
            cost_usd=None,
        )

    def classify_batch(self, records: list[dict[str, Any]]) -> list[PredictionRecord]:
        results: list[PredictionRecord] = []
        for record in records:
            text = record.get("classifier_text", record.get("text_for_classifier", ""))
            results.append(
                self.classify(
                    text=text,
                    record_id=record.get("id", record.get("record_id", "")),
                    label_true=record.get("mapped_label", record.get("label_mapped", "")),
                )
            )
        return results


def create_classifier_provider(
    provider_backend: str = FAKE_PROVIDER,
    model_version: str = "0.0.1-fake",
    azure_openai_endpoint: str | None = None,
    azure_openai_api_key: str | None = None,
    azure_openai_model: str | None = None,
    azure_openai_api_version: str = DEFAULT_AZURE_OPENAI_API_VERSION,
) -> ClassifierProvider:
    """Create a classifier provider instance."""
    if provider_backend == FAKE_PROVIDER:
        return FakeClassifierProvider(model_version=model_version)

    if provider_backend == AZURE_OPENAI_PROVIDER:
        if not azure_openai_endpoint or not azure_openai_api_key or not azure_openai_model:
            raise ValueError(
                "Azure OpenAI provider requires endpoint, api_key, and openai_model"
            )
        return AzureOpenAIClassifierProvider(
            azure_openai_endpoint=azure_openai_endpoint,
            azure_openai_api_key=azure_openai_api_key,
            azure_openai_model=azure_openai_model,
            api_version=azure_openai_api_version,
            model_version=model_version,
        )

    raise ValueError(
        f"Unsupported provider backend: {provider_backend}. "
        f"Supported values are '{FAKE_PROVIDER}' and '{AZURE_OPENAI_PROVIDER}'."
    )


def _parse_classifier_response(content: Any) -> dict[str, Any]:
    if isinstance(content, list):
        content = "".join(
            part.get("text", "") if isinstance(part, dict) else str(part) for part in content
        )
    elif content is None:
        content = ""
    else:
        content = str(content)

    match = _JSON_OBJECT_PATTERN.search(content)
    candidate = match.group(0) if match else content
    try:
        payload = json.loads(candidate)
    except json.JSONDecodeError as exc:
        raise ValueError("Classifier baseline did not return valid JSON") from exc
    if not isinstance(payload, dict):
        raise ValueError("Classifier baseline returned a non-object JSON payload")
    return payload


def _normalize_label(label: Any) -> str:
    if not isinstance(label, str):
        raise ValueError("Classifier baseline response is missing a string label")
    normalized = label.strip().lower()
    if normalized not in VALID_LABELS:
        raise ValueError(f"Classifier baseline returned unsupported label: {label}")
    return normalized


def _normalize_confidence(confidence: Any) -> float | None:
    if confidence is None:
        return None
    try:
        normalized = float(confidence)
    except (TypeError, ValueError) as exc:
        raise ValueError("Classifier baseline confidence is not numeric") from exc
    if normalized < 0.0 or normalized > 1.0:
        raise ValueError("Classifier baseline confidence must be between 0 and 1")
    return normalized
