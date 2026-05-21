# API Contracts: Health Endpoints and Error Schema

**Phase**: 1 — Foundation and Architecture Skeleton
**Version**: 0.1.0
**Auth required**: None (all health endpoints are unauthenticated)

The machine-readable OpenAPI contract is in
[`health-and-errors.openapi.yaml`](health-and-errors.openapi.yaml).
This document provides the human-readable complement.

---

## X-Request-ID Header Contract

Applies to all endpoints.

| Direction | Behavior |
|---|---|
| **Incoming request** | If the `X-Request-ID` header is present and non-empty, the backend uses that value as the request identifier. |
| **Incoming request (absent)** | The backend generates a UUID4 string and uses it as the request identifier. |
| **Outgoing response** | The resolved `X-Request-ID` is always set on the response header, regardless of whether the request supplied one. |
| **Logs** | Every log entry emitted during the request automatically carries `request_id` via structlog context-vars binding. |
| **Error responses** | The `request_id` field in every `ErrorResponse` body equals the resolved `X-Request-ID` for that request. |

---

## GET /health/live

**Purpose**: Process liveness check. Confirms the backend process is running and
able to accept requests. Does not check any external dependencies.

| Property | Value |
|---|---|
| Method | `GET` |
| Path | `/health/live` |
| Auth required | No |
| Request body | None |
| Request parameters | None |

### Success Response — 200 OK

Returned whenever the process is alive, unconditionally.

**Headers**:
```
X-Request-ID: <uuid4>
Content-Type: application/json
```

**Body schema**:
```json
{
  "status": "ok",
  "service": "maintainer-copilot",
  "version": "0.1.0",
  "checks": [],
  "request_id": "<uuid4>"
}
```

**Field constraints**:
- `status` is always `"ok"` for `/health/live`.
- `checks` is always an empty array for `/health/live`.
- `version` is optional; may be omitted if not configured.
- `request_id` matches the value in the `X-Request-ID` response header.

**No error response**: This endpoint has no failure mode. If the process is dead,
no response is returned.

---

## GET /health/ready

**Purpose**: Shallow readiness check. Reports whether each default core dependency
is reachable. Used by Docker Compose health probes and orchestration tooling to
determine whether the backend is ready to receive traffic.

| Property | Value |
|---|---|
| Method | `GET` |
| Path | `/health/ready` |
| Auth required | No |
| Request body | None |
| Request parameters | None |

### Success Response — 200 OK

Returned only when **all** default core dependency checks pass.

**Headers**:
```
X-Request-ID: <uuid4>
Content-Type: application/json
```

**Body schema**:
```json
{
  "status": "ok",
  "service": "maintainer-copilot",
  "version": "0.1.0",
  "checks": [
    {"name": "postgres", "status": "ok", "message": "reachable"},
    {"name": "redis",    "status": "ok", "message": "reachable"},
    {"name": "minio",    "status": "ok", "message": "reachable"},
    {"name": "vault",    "status": "ok", "message": "authenticated"},
    {"name": "pgvector", "status": "ok", "message": "extension available"}
  ],
  "request_id": "<uuid4>"
}
```

### Error Response — 503 Service Unavailable

Returned when **any** default core dependency check fails or is degraded.
The response body still includes all per-check statuses so the caller can
identify which dependency is unavailable without inspecting logs.

**Headers**:
```
X-Request-ID: <uuid4>
Content-Type: application/json
```

**Body schema** (example — postgres unavailable):
```json
{
  "status": "unavailable",
  "service": "maintainer-copilot",
  "version": "0.1.0",
  "checks": [
    {"name": "postgres", "status": "unavailable", "message": "connection refused"},
    {"name": "redis",    "status": "ok",          "message": "reachable"},
    {"name": "minio",    "status": "ok",          "message": "reachable"},
    {"name": "vault",    "status": "ok",          "message": "authenticated"},
    {"name": "pgvector", "status": "unavailable", "message": "postgres unreachable"}
  ],
  "request_id": "<uuid4>"
}
```

**Aggregate status rules**:

| Condition | `status` | HTTP code |
|---|---|---|
| All checks `"ok"` | `"ok"` | 200 |
| Any check `"degraded"`, none `"unavailable"` | `"degraded"` | 503 |
| Any check `"unavailable"` | `"unavailable"` | 503 |

**Check message rules**:
- Messages are safe for external consumers: no connection strings, no credentials,
  no raw exception text.
- Messages are bounded and human-readable (e.g., `"connection refused"`,
  `"reachable"`, `"authenticated"`, `"extension available"`).

**Default core checks** (Phase 1):

| Check name | What is probed | Timeout |
|---|---|---|
| `postgres` | Async `SELECT 1` via SQLAlchemy session | 3 s |
| `redis` | `PING` via redis.asyncio | 2 s |
| `minio` | HTTP `GET /minio/health/live` via httpx | 3 s |
| `vault` | `client.is_authenticated()` (hvac) | 2 s |
| `pgvector` | `SELECT extname FROM pg_extension WHERE extname = 'vector'` | 3 s |

---

## Error Response Schema (all endpoints)

All application errors — whether from domain exceptions, validation failures, or
unhandled exceptions — return a response in this schema.

**HTTP status codes**: 422 (validation), 503 (dependency), 500 (server error), or
the status code associated with the raised `DomainError` subclass.

**Headers**:
```
X-Request-ID: <uuid4>
Content-Type: application/json
```

**Body schema**:
```json
{
  "error_code": "SERVER_ERROR",
  "message": "An unexpected error occurred.",
  "request_id": "<uuid4>"
}
```

**Field constraints**:

| Field | Type | Required | Constraints |
|---|---|---|---|
| `error_code` | `string` | yes | Stable uppercase identifier with underscores; e.g. `"CONFIG_ERROR"`, `"DEPENDENCY_UNAVAILABLE"`, `"VALIDATION_ERROR"`, `"SERVER_ERROR"` |
| `message` | `string` | yes | Safe human-readable description; never contains stack traces or secrets |
| `request_id` | `string` | yes | Correlates the error to the request log entry; always non-empty |

**Phase 1 error codes**:

| `error_code` | HTTP status | Trigger |
|---|---|---|
| `"CONFIG_ERROR"` | 500 | Missing or invalid required configuration detected at startup |
| `"DEPENDENCY_UNAVAILABLE"` | 503 | Core dependency unreachable during request handling |
| `"VALIDATION_ERROR"` | 422 | Invalid request payload |
| `"SERVER_ERROR"` | 500 | Unhandled exception caught by the global error handler |

**Invariants**:
- The `request_id` in the body always equals the value in the `X-Request-ID` response header for the same response.
- No stack trace text appears in `message`.
- No secret-like values (tokens, passwords, connection strings) appear in any field.
- The response body is always the top-level JSON object (not nested under an `"error"` key).
