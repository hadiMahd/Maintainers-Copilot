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


class AuthenticationError(DomainError):
    """Authentication failure."""

    error_code = "invalid_credentials"
    status_code = 401


class AuthorizationError(DomainError):
    """Authorization failure."""

    error_code = "admin_required"
    status_code = 403


class TokenError(DomainError):
    """Token validation or refresh failure."""

    error_code = "authentication_required"
    status_code = 401


class InvitationError(DomainError):
    """Invitation validation failure."""

    error_code = "invalid_invitation"
    status_code = 400


class MemoryError(DomainError):
    """Memory operation failure."""

    error_code = "invalid_memory_input"
    status_code = 422


class AuditError(DomainError):
    """Audit logging failure."""

    error_code = "audit_write_failed"
    status_code = 500


class SigningKeyError(DomainError):
    """JWT signing key unavailable."""

    error_code = "signing_key_unavailable"
    status_code = 503


class EmailAlreadyRegisteredError(DomainError):
    """Registration with an already registered email."""

    error_code = "email_already_registered"
    status_code = 409


class RegistrationError(DomainError):
    """Invalid registration input."""

    error_code = "invalid_registration"
    status_code = 422


class UnsupportedMemoryTypeError(DomainError):
    """Unsupported memory type requested."""

    error_code = "unsupported_memory_type"
    status_code = 422


class RedactionError(DomainError):
    """Redaction failure."""

    error_code = "redaction_failed"
    status_code = 500
