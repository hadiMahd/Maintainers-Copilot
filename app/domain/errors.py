"""Domain error hierarchy."""


class DomainError(Exception):
    """Base domain error."""

    error_code: str = "DOMAIN_ERROR"
    status_code: int = 500

    def __init__(self, message: str, details: dict | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ConfigError(DomainError):
    """Configuration error."""

    error_code = "CONFIG_ERROR"
    status_code = 500


class DependencyError(DomainError):
    """Dependency unavailable error."""

    error_code = "DEPENDENCY_UNAVAILABLE"
    status_code = 503


class ValidationError(DomainError):
    """Validation error."""

    error_code = "VALIDATION_ERROR"
    status_code = 422


class ServerError(DomainError):
    """Server error."""

    error_code = "SERVER_ERROR"
    status_code = 500
