from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class StreamlitSettingsError(Exception):
    """Raised when required Streamlit configuration is missing or invalid."""


class StreamlitSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="MAINTAINER_COPILOT_UI_",
        extra="ignore",
    )

    base_url: str = ""
    rest_timeout_seconds: int = 30
    sse_timeout_seconds: int = 70
    connect_timeout_seconds: int = 10
    read_timeout_seconds: int = 30

    def validate_or_raise(self) -> None:
        if not self.base_url:
            raise StreamlitSettingsError(
                "MAINTAINER_COPILOT_UI_BASE_URL is required (e.g. http://localhost:8000). "
                "Set it as an environment variable or in a .env file."
            )
        for field_name in (
            "rest_timeout_seconds",
            "sse_timeout_seconds",
            "connect_timeout_seconds",
            "read_timeout_seconds",
        ):
            value = getattr(self, field_name)
            if value <= 0:
                raise StreamlitSettingsError(
                    f"MAINTAINER_COPILOT_UI_{field_name.upper()} must be positive, got {value}"
                )
