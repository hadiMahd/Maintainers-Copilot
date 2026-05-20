"""Tests that importing modules does not trigger network calls."""

import subprocess
import sys

import pytest

MODULES = [
    "app.core.application",
    "app.core.config",
    "app.core.lifespan",
    "app.api.routes.health",
    "app.infra.database",
    "app.infra.redis_client",
    "app.infra.vault_client",
    "app.infra.minio_client",
    "app.infra.redaction",
    "app.domain.classifier",
    "app.infra.llm.classifier_baseline",
    "app.infra.storage.classifier_artifacts",
    "app.infra.mlflow.tracking",
    "app.services.classifier_evaluation",
    "app.api.routes.chat",
    "app.infra.prompt_registry",
    "app.infra.chatbot_graph",
    "app.infra.llm_adapter",
    "app.infra.model_server_tools",
    "app.infra.rag_tool_client",
    "app.infra.memory_tool_client",
    "app.infra.tracing",
    "app.services.chatbot_service",
    "app.services.chatbot_graph_service",
    "app.services.tool_execution_service",
    "app.services.conversation_state_service",
    "app.services.chat_tracing_service",
]


@pytest.mark.parametrize("module", MODULES)
def test_import_no_network(module):
    """Import module in subprocess with blocked network and assert success."""
    env = {
        **dict(subprocess.os.environ),
        "VAULT_ADDR": "http://127.0.0.1:1",
        "ENVIRONMENT": "test",
        "VAULT_TOKEN": "fake-token",
    }
    result = subprocess.run(
        [sys.executable, "-c", f"import {module}"],
        capture_output=True,
        text=True,
        env=env,
        timeout=10,
    )
    assert result.returncode == 0, (
        f"Import of {module} failed:\nstdout: {result.stdout}\nstderr: {result.stderr}"
    )
    stderr = result.stderr.lower()
    assert "connectionrefusederror" not in stderr
    assert "connection refused" not in stderr
    assert "sqlalchemy" not in stderr or "connection" not in stderr
