"""Unit tests for lifespan provider secret hydration."""

from pydantic import SecretStr

from app.core.config import AppSettings
from app.core.lifespan import _apply_optional_provider_settings


def test_apply_optional_provider_settings_populates_azure_and_langsmith_fields():
    settings = AppSettings(vault_addr="http://vault.local", vault_token="token")

    _apply_optional_provider_settings(
        settings,
        {
            "azure_openai_endpoint": "https://example.openai.azure.com/",
            "azure_openai_api_key": "azure-secret",
            "azure_openai_model": "gpt-5.4-nano",
            "azure_openai_embedding_model": "text-embedding-3-small",
            "langchain_api_key": "ls-secret",
            "langchain_endpoint": "https://api.smith.langchain.com",
            "langchain_project": "maintainer-copilot",
        },
    )

    assert settings.azure_openai_endpoint == "https://example.openai.azure.com/"
    assert isinstance(settings.azure_openai_api_key, SecretStr)
    assert settings.azure_openai_api_key.get_secret_value() == "azure-secret"
    assert settings.azure_openai_model == "gpt-5.4-nano"
    assert settings.azure_openai_embedding_model == "text-embedding-3-small"
    assert isinstance(settings.langchain_api_key, SecretStr)
    assert settings.langchain_api_key.get_secret_value() == "ls-secret"
    assert settings.langsmith_endpoint == "https://api.smith.langchain.com"
    assert settings.langsmith_project == "maintainer-copilot"
