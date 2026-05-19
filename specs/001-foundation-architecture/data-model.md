# Data Model: Foundation and Architecture Skeleton

## Configuration Profile

**Purpose**: Typed local/runtime configuration required to start and validate the
foundation.

**Fields**:
- `environment`: local environment name.
- `log_level`: structured logging threshold.
- `database_url`: async database connection string.
- `redis_url`: cache connection string.
- `minio_endpoint`: object storage endpoint.
- `vault_addr`: secret-store endpoint.
- `vault_token`: local bootstrap token placeholder only.
- `request_id_header`: inbound/outbound request ID header name.

**Validation Rules**:
- Required values fail loudly when absent.
- Example values must be fake or local-only.
- Real credentials are invalid for committed example files.
- No module outside the configuration module may read environment variables
  directly.

## Health Status

**Purpose**: Represents process liveness and shallow dependency readiness.

**Fields**:
- `status`: `ok`, `degraded`, or `unavailable`.
- `service`: service name.
- `version`: optional application version string.
- `checks`: list of shallow dependency checks.
- `request_id`: request identifier when available.

**Validation Rules**:
- Liveness must not depend on external services.
- Readiness must be bounded and shallow.
- Readiness returns HTTP 503 when any default core dependency check is
  unavailable, while still returning safe per-check status details.
- Check details must not expose secrets.

## Readiness Check

**Purpose**: Describes the status of one dependency or subsystem.

**Fields**:
- `name`: dependency or subsystem name.
- `status`: `ok`, `degraded`, or `unavailable`.
- `message`: safe human-readable detail.

**Validation Rules**:
- Messages must be safe for API responses.
- Checks must avoid expensive operations.

## Request Context

**Purpose**: Carries request correlation metadata across routes, services, logs,
and error responses.

**Fields**:
- `request_id`: generated or inbound request identifier.
- `trace_id`: optional trace identifier for future tracing.
- `path`: request path when available.
- `method`: request method when available.

**Validation Rules**:
- Every request receives a request ID.
- Request and trace IDs must be safe to log.

## Domain Error

**Purpose**: Stable application failure that maps to a structured HTTP error.

**Fields**:
- `code`: stable machine-readable error code.
- `message`: safe user-facing message.
- `status_code`: HTTP status code selected at the boundary.
- `request_id`: request identifier when available.
- `details`: optional safe structured details.

**Validation Rules**:
- User-facing messages must not include stack traces.
- Details must not contain secrets or raw sensitive payloads.
- Unknown exceptions map to a generic server error.

## Migration Baseline

**Purpose**: Initial migration state for future persistence work.

**Fields**:
- `revision_id`: migration revision identifier.
- `description`: short migration description.
- `created_at`: creation date.

**Validation Rules**:
- Baseline must be reproducible from a clean checkout.
- Feature tables are not introduced in this phase unless required for the
  migration framework itself.

## Documentation Set

**Purpose**: Required project documents that future phases update.

**Fields**:
- `readme`: setup and project overview.
- `architecture`: layer ownership and boundaries.
- `decisions`: measured decisions and alternatives.
- `runbook`: operational commands and failure paths.
- `evals`: evaluation approach and future reports.
- `security`: secret and redaction policy.

**Validation Rules**:
- Each document must state its purpose.
- Future-phase sections must be clearly marked as pending, not complete.

## Service Definition

**Purpose**: Local-stack service entry for one runtime component or dependency.

**Fields**:
- `name`: service name.
- `role`: runtime role in the local stack.
- `health`: optional health or readiness expectation.
- `depends_on`: startup dependency names.

**Validation Rules**:
- Services for future phases may be skeletal only.
- Service definitions must not embed real secrets.
