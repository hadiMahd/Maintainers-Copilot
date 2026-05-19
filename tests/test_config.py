"""Tests for application configuration."""

import os

import pytest
from pydantic import ValidationError

from app.core.config import AppSettings


def test_valid_settings_construction(monkeypatch):
    """Construct AppSettings with all required fields."""
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("VAULT_ADDR", "http://localhost:8200")
    monkeypatch.setenv("VAULT_ROLE_ID", "role")
    monkeypatch.setenv("VAULT_SECRET_ID", "secret")
    settings = AppSettings()
    assert settings.environment == "test"
    assert settings.vault_addr == "http://localhost:8200"


def test_missing_vault_addr_raises(monkeypatch):
    """Omit VAULT_ADDR and assert ValidationError is raised."""
    monkeypatch.delenv("VAULT_ADDR", raising=False)
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("VAULT_ROLE_ID", "role")
    monkeypatch.setenv("VAULT_SECRET_ID", "secret")
    with pytest.raises(ValidationError):
        AppSettings()


def test_missing_vault_role_id_raises(monkeypatch):
    """Omit VAULT_ROLE_ID and assert ValidationError is raised."""
    monkeypatch.delenv("VAULT_ROLE_ID", raising=False)
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("VAULT_ADDR", "http://localhost:8200")
    monkeypatch.setenv("VAULT_SECRET_ID", "secret")
    with pytest.raises(ValidationError):
        AppSettings()


def test_missing_vault_secret_id_raises(monkeypatch):
    """Omit VAULT_SECRET_ID and assert ValidationError is raised."""
    monkeypatch.delenv("VAULT_SECRET_ID", raising=False)
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("VAULT_ADDR", "http://localhost:8200")
    monkeypatch.setenv("VAULT_ROLE_ID", "role")
    with pytest.raises(ValidationError):
        AppSettings()


def test_missing_environment_raises(monkeypatch):
    """Omit ENVIRONMENT and assert ValidationError is raised."""
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    monkeypatch.setenv("VAULT_ADDR", "http://localhost:8200")
    monkeypatch.setenv("VAULT_ROLE_ID", "role")
    monkeypatch.setenv("VAULT_SECRET_ID", "secret")
    with pytest.raises(ValidationError):
        AppSettings()


def test_vault_resolved_fields_default_none(monkeypatch):
    """Construct valid AppSettings and assert vault-resolved fields are None."""
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("VAULT_ADDR", "http://localhost:8200")
    monkeypatch.setenv("VAULT_ROLE_ID", "role")
    monkeypatch.setenv("VAULT_SECRET_ID", "secret")
    settings = AppSettings()
    assert settings.database_url is None
    assert settings.redis_url is None
    assert settings.minio_endpoint is None
    assert settings.minio_access_key is None
    assert settings.minio_secret_key is None
