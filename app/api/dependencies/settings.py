"""FastAPI dependencies."""

from app.core.config import AppSettings


def get_settings() -> AppSettings:
    """Return the application settings.

    In tests this is typically overridden.
    """
    return AppSettings()
