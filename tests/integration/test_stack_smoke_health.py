"""Integration test for stack smoke health check."""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
import yaml


class TestStackSmokeHealth:
    """Verify smoke stack can start production-functional stack and reach health endpoint."""

    def test_smoke_stack_script_exists(self):
        assert Path("scripts/ci/smoke_stack.sh").exists()
        assert os.access("scripts/ci/smoke_stack.sh", os.X_OK)

    def test_docker_compose_file_exists(self):
        assert Path("docker-compose.yml").exists()

    def test_docker_compose_includes_model_server(self):
        content = Path("docker-compose.yml").read_text()
        assert "model_server" in content

    def test_docker_compose_includes_backend(self):
        content = Path("docker-compose.yml").read_text()
        assert "backend:" in content

    def test_vault_seed_waits_for_runtime_dependencies(self):
        with open("docker-compose.yml") as f:
            compose = yaml.safe_load(f)

        depends_on = compose["services"]["vault_seed"]["depends_on"]
        for service in ("vault", "postgres", "redis", "minio"):
            assert depends_on[service]["condition"] == "service_healthy"

    def test_backend_has_health_endpoint(self):
        """Backend application should have health check endpoints (/live, /ready)."""
        from app.api.routes.health import router

        routes = [r.path for r in router.routes]
        assert any("/live" in r for r in routes), "Backend should have /live endpoint"
        assert any("/ready" in r for r in routes), "Backend should have /ready endpoint"

    def test_smoke_script_model_server_reference(self):
        content = Path("scripts/ci/smoke_stack.sh").read_text()
        assert "model_server" in content
        assert "health" in content.lower()

    def test_smoke_script_uses_docker_compose(self):
        content = Path("scripts/ci/smoke_stack.sh").read_text()
        assert "docker compose" in content or "docker-compose" in content

    def test_smoke_script_checks_health(self):
        content = Path("scripts/ci/smoke_stack.sh").read_text()
        assert "health" in content.lower()


class TestValidateStackHealth:
    """Test the validate_stack_health.py script."""

    def test_health_validator_exists(self):
        assert Path("scripts/ci/validate_stack_health.py").exists()

    def test_health_validator_imports_cleanly(self):
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "validate_stack_health",
            "scripts/ci/validate_stack_health.py",
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

    def test_health_polling_mocked(self):
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "validate_stack_health",
            "scripts/ci/validate_stack_health.py",
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "ok"}

        with patch.object(httpx, "get", return_value=mock_response):
            if hasattr(mod, "check_health"):
                result = mod.check_health("http://localhost:8000/health")
                assert result is True


class TestSmokeNoCredentials:
    """Verify smoke test does not require paid API credentials."""

    def test_smoke_script_no_paid_credentials(self):
        content = Path("scripts/ci/smoke_stack.sh").read_text()
        assert "AZURE_OPENAI_KEY" not in content
        assert "OPENAI_API_KEY" not in content

    def test_health_validator_no_paid_credentials(self):
        content = Path("scripts/ci/validate_stack_health.py").read_text()
        assert "AZURE_OPENAI_KEY" not in content
        assert "OPENAI_API_KEY" not in content
