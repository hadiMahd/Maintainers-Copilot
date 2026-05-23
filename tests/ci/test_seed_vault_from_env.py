"""Tests for Vault seed bootstrap environment requirements."""

from scripts.seed_vault_from_env import REQUIRED_ENV_VARS, require_seed_values


def test_vault_seed_does_not_require_paid_provider_env_values():
    minimal_env = {name: "value" for name in REQUIRED_ENV_VARS}

    require_seed_values(minimal_env)


def test_vault_seed_requires_core_runtime_values():
    minimal_env = {name: "value" for name in REQUIRED_ENV_VARS}
    minimal_env.pop("APP_DATABASE_URL")

    try:
        require_seed_values(minimal_env)
    except RuntimeError as exc:
        assert "APP_DATABASE_URL" in str(exc)
    else:
        raise AssertionError("Expected missing core runtime value to fail")
