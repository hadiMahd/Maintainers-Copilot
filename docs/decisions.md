# Decisions

## ADR-001: structlog for Structured Logging

**Decision**: Use structlog with JSON renderer for all application logging.

**Rationale**: Machine-parseable logs, contextvars support for automatic `request_id` binding, and explicit processor chains.

**Alternatives Rejected**:
- Standard `logging` module: no structured JSON output by default.
- loguru: less contextvars integration and custom binding support.

## ADR-002: Vault AppRole for Secret Resolution

**Decision**: All secrets are read from Vault at lifespan startup using AppRole authentication.

**Rationale**: No secrets in env vars or Docker images. Centralized secret management with audit trails.

**Alternatives Rejected**:
- Env-file secrets: risk of committing credentials.
- AWS Secrets Manager: vendor lock-in for local development.

## ADR-003: X-Request-ID Header Strategy

**Decision**: Middleware generates UUID4 if header absent, echoes it on response, binds it to structlog contextvars.

**Rationale**: End-to-end traceability visible to HTTP clients.

**Alternatives Rejected**:
- Trace headers only (not HTTP-visible to clients).

## Phase 2+ Decisions

To be added as phases progress.
