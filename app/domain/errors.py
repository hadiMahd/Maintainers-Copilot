"""Domain error hierarchy."""


class DomainError(Exception):
    """Base domain error."""

    error_code: str = "DOMAIN_ERROR"
    status_code: int = 500

    def __init__(
        self,
        message: str,
        details: dict | None = None,
        trace_id: str | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}
        self.trace_id = trace_id


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


class ChatValidationError(DomainError):
    """Chat request validation failure."""

    error_code = "invalid_chat_input"
    status_code = 422


class RequestTooLargeError(DomainError):
    """Chat request exceeds configured size limit."""

    error_code = "request_too_large"
    status_code = 413


class ContextLimitExceededError(DomainError):
    """Chat context exceeds configured size limit."""

    error_code = "context_limit_exceeded"
    status_code = 422


class MaxToolCallsExceededError(DomainError):
    """Chat tool-call budget exceeded."""

    error_code = "max_tool_calls_exceeded"
    status_code = 422


class RecursionLimitExceededError(DomainError):
    """Chat graph recursion budget exceeded."""

    error_code = "recursion_limit_exceeded"
    status_code = 422


class ChatbotTimeoutError(DomainError):
    """Full chat execution timeout."""

    error_code = "chatbot_timeout"
    status_code = 504


class LLMUnavailableError(DomainError):
    """Tool-calling LLM unavailable or misconfigured."""

    error_code = "llm_unavailable"
    status_code = 503


class ToolExecutionFailedError(DomainError):
    """Tool execution failed before safe recovery."""

    error_code = "tool_execution_failed"
    status_code = 503


class TracingFailedError(DomainError):
    """Tracing infrastructure unavailable or failed."""

    error_code = "tracing_failed"
    status_code = 503


class WidgetConfigNotFoundError(DomainError):
    """Widget configuration not found."""

    error_code = "widget_config_not_found"
    status_code = 404


class WidgetConfigError(DomainError):
    """Widget configuration operation failure."""

    error_code = "invalid_widget_config"
    status_code = 422


class MemoryInspectorError(DomainError):
    """Memory inspection authorization or operation failure."""

    error_code = "invalid_memory_scope"
    status_code = 403


class WidgetEmbedError(DomainError):
    """Widget embed or origin validation failure."""

    error_code = "widget_embed_error"
    status_code = 403


class WidgetSessionError(DomainError):
    """Widget anonymous session token issuance failure."""

    error_code = "widget_session_error"
    status_code = 403
