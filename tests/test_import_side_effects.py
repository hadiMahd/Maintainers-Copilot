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
]


@pytest.mark.parametrize("module", MODULES)
def test_import_no_network(module):
    """Import module in subprocess with blocked network and assert success."""
    env = {
        **dict(subprocess.os.environ),
        "VAULT_ADDR": "http://127.0.0.1:1",
        "ENVIRONMENT": "test",
        "VAULT_ROLE_ID": "fake",
        "VAULT_SECRET_ID": "fake",
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
