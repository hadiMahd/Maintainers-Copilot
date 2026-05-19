"""Run the LLM classifier baseline against the shared test split.

Uses Azure OpenAI through LangChain AzureChatOpenAI when credentials are
available, and falls back to a fake/mock LangChain provider for testing
and local runs without real credentials.
"""

from __future__ import annotations

import json
import os
import tempfile
import time
from pathlib import Path

from app.core.config import AppSettings
from app.infra.llm.classifier_baseline import (
    AZURE_OPENAI_PROVIDER,
    FAKE_PROVIDER,
    create_classifier_provider,
)
from app.infra.vault_client import init_vault_client, resolve_classifier_secrets
from app.services.classifier_evaluation import (
    compute_metrics,
    save_predictions_jsonl,
)


def load_dataset(path: str) -> list[dict]:
    """Load a JSONL dataset split."""
    records = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def _enable_langsmith_tracing(resolved: dict) -> str:
    """Enable LangSmith tracing via environment variables from Vault secrets.

    Returns the tracing backend identifier string.
    """
    tracing_enabled = str(resolved.get("langchain_tracing", "")).lower() == "true"
    api_key = resolved.get("langchain_api_key")
    endpoint = resolved.get("langchain_endpoint")
    project = resolved.get("langchain_project")

    if tracing_enabled and api_key:
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGCHAIN_API_KEY"] = str(api_key)
        if endpoint:
            os.environ["LANGCHAIN_ENDPOINT"] = str(endpoint)
        if project:
            os.environ["LANGCHAIN_PROJECT"] = str(project).strip('"')
        return "langsmith"
    return "none"


def run_llm_classifier_baseline(
    test_path: str = "data/processed/test.jsonl",
    artifact_dir: str = "artifacts/classifiers/llm_baseline",
    provider_backend: str = FAKE_PROVIDER,
    model_version: str = "0.0.1-fake",
    azure_openai_api_version: str = "2024-10-21",
) -> None:
    """Run the LLM baseline and save predictions and metrics.

    Uses the fake provider by default. To use Azure OpenAI,
    set provider_backend='azure_openai' and ensure Vault-resolved
    credentials are available at runtime.
    """
    provider_kwargs: dict[str, object] = {
        "provider_backend": provider_backend,
        "model_version": model_version,
        "azure_openai_api_version": azure_openai_api_version,
    }
    secret_source = FAKE_PROVIDER
    tracing_backend = "none"
    if provider_backend == AZURE_OPENAI_PROVIDER:
        settings = AppSettings()
        vault_client = init_vault_client(settings)
        resolved = resolve_classifier_secrets(vault_client, settings)
        resolved_model = resolved.get("azure_openai_model")
        if model_version == "0.0.1-fake" and isinstance(resolved_model, str):
            model_version = resolved_model
            provider_kwargs["model_version"] = model_version
        provider_kwargs.update(
            azure_openai_endpoint=resolved.get("azure_openai_endpoint"),
            azure_openai_api_key=resolved.get("azure_openai_api_key"),
            azure_openai_model=resolved_model,
        )
        secret_source = "vault"
        tracing_backend = _enable_langsmith_tracing(resolved)

    provider = create_classifier_provider(**provider_kwargs)

    # Load test data
    test_data = load_dataset(test_path)

    # Run classification
    start_time = time.time()
    predictions = provider.classify_batch(test_data)
    elapsed_ms = (time.time() - start_time) * 1000

    # Compute metrics
    y_true = [p.label_true for p in predictions]
    y_pred = [p.label_predicted for p in predictions]
    metrics = compute_metrics(y_true, y_pred)
    metrics["total_latency_ms"] = elapsed_ms
    metrics["approach"] = "llm_baseline"
    metrics["version"] = model_version
    metrics["provider_backend"] = provider_backend
    metrics["secret_source"] = secret_source
    metrics["tracing_backend"] = tracing_backend

    # Create artifact directory
    artifact_path = Path(artifact_dir)
    artifact_path.mkdir(parents=True, exist_ok=True)

    # Save predictions
    save_predictions_jsonl(predictions, str(artifact_path / "predictions.jsonl"))

    # Save metrics
    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".json", dir=str(artifact_path))
    try:
        with os.fdopen(tmp_fd, "w") as f:
            json.dump(metrics, f, indent=2, default=str)
        os.replace(tmp_path, str(artifact_path / "metrics.json"))
    except Exception:
        os.unlink(tmp_path) if os.path.exists(tmp_path) else None
        raise

    # Save config
    config = {
        "approach": "llm_baseline",
        "version": model_version,
        "provider_backend": provider_backend,
        "secret_source": secret_source,
        "tracing_backend": tracing_backend,
        "test_samples": len(test_data),
    }
    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".json", dir=str(artifact_path))
    try:
        with os.fdopen(tmp_fd, "w") as f:
            json.dump(config, f, indent=2)
        os.replace(tmp_path, str(artifact_path / "config.json"))
    except Exception:
        os.unlink(tmp_path) if os.path.exists(tmp_path) else None
        raise

    print(f"LLM baseline complete. Metrics: accuracy={metrics['accuracy']:.4f}, macro_f1={metrics['macro_f1']:.4f}")
    print(f"Artifacts saved to {artifact_dir}")


if __name__ == "__main__":
    run_llm_classifier_baseline()
