# Implementation Plan: Authentication, Memory, and Audit Logging

**Branch**: `006-auth-memory-audit` | **Date**: 2026-05-18 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/006-auth-memory-audit/spec.md`

## Summary

Build Phase 6 authentication, authorization, explicit memory, and audit logging.
The work adds email/password registration, login with access and refresh tokens,
Vault-resolved JWT signing key loading at startup, user/admin roles, admin
invitation, `current_user` and `require_admin` dependencies, Redis-backed
short-term memory with configurable TTL, explicit long-term memory writes in
PostgreSQL with pgvector, redaction before memory persistence, and audit logs for
memory writes, role changes, admin invitations, future widget config changes,
and future conversation deletions. It also defines a cross-conversation recall
demo for explicitly written long-term memory. FastAPI Users may be used
selectively for core registration/login/current-user plumbing where it fits the
architecture, while project services keep transaction boundaries, authorization,
refresh sessions, memory, redaction, and audit behavior.

## Technical Context

**Language/Version**: Python 3.11 or newer  
**Primary Dependencies**: FastAPI, pydantic-settings, SQLAlchemy async, asyncpg,
Alembic, PostgreSQL 16 with pgvector, Redis async client, Vault adapter, pytest,
httpx, password hashing/token utilities, and optionally FastAPI Users with the
SQLAlchemy adapter where it fits cleanly behind project services  
**Storage**: PostgreSQL tables for users, roles, refresh token sessions, admin
invitations, long-term memory entries, long-term memory embeddings, and audit
logs; Redis for short-term user-scoped conversation memory with explicit TTL;
Vault for JWT signing key resolution at startup  
**Testing**: pytest unit/contract/integration tests for registration, login,
JWT signing-key startup behavior, refresh token expiry/revocation/rotation,
current-user dependency, `require_admin`, admin invitation, Redis TTL memory,
explicit long-term memory writes, no auto-writes, audit rows, service transaction
boundaries, repository no-commit behavior, reserved audit action names,
cross-conversation recall, redaction before persistence/logs, structured logging
with `request_id`/`trace_id` propagation, and async-safe embedding handling  
**Target Platform**: Local developer environment with Docker Compose PostgreSQL,
Redis, and Vault dev mode; future CI jobs with fakes for Vault/Redis where needed  
**Project Type**: Backend web-service feature with persistence, cache, secret,
and authorization boundaries  
**Performance Goals**: Auth and memory request paths use async database and
Redis clients; JWT signing key and shared clients are loaded during lifespan;
short-term memory reads/writes are bounded by configured TTL; long-term embedding
generation is not automatic and runs only during explicit write-memory flows;
embedding generation must use an async provider or `asyncio.to_thread` so that
write-memory request paths do not block the event loop  
**Constraints**: Phase 6 only; no full chatbot orchestration, automatic memory
extraction, RAG question answering, UI work, or widget behavior; no real secrets
in repository files, tests, logs, or docs; services own transaction boundaries;
repositories do not commit independently; redaction runs before memory
persistence and audit metadata  
**Scale/Scope**: Registration/login, refresh sessions, user/admin role model,
admin invitation, authorization dependencies, Redis short-term memory, explicit
long-term memory with one selected memory type, audit logs for memory writes and
role/admin changes, reserved audit actions for widget config changes and
conversation deletion, `docs/decisions.md` updates for memory TTL, memory type,
audit policy, and cross-conversation recall, and focused tests for critical
security/memory behavior

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Initial Gate

- **Phase Scope**: PASS. This is `PLAN.md` Phase 6 only. It implements auth,
  authorization, memory, and audit logging and excludes full chatbot
  orchestration, automatic memory writes, RAG question answering, UI, widget, and
  unrelated product behavior.
- **Layered Architecture**: PASS. Routes stay thin. Auth, role, invitation,
  memory, redaction, and audit workflows live in services. Repositories own SQL
  only and do not commit. Infra owns Vault, Redis, token/password helpers,
  pgvector embedding adapters, and redaction.
- **FastAPI Resource Management**: PASS. Vault signing key, Redis client,
  database engine/sessionmaker, and token/auth dependencies are initialized
  through app factory/lifespan/dependency injection, not at import time or per
  request.
- **Async Safety**: PASS. API request paths use async database and Redis clients.
  Blocking password hashing or embedding work must be bounded and moved to
  helpers or thread offload if needed with a documented reason.
- **Secrets And Redaction**: PASS. JWT signing keys resolve from Vault or test
  fakes. Passwords, tokens, memory content, and audit metadata are never logged
  raw. Redaction is required before short-term or long-term memory persistence
  and before audit metadata.
- **Observability And Errors**: PASS. Auth failures, role changes, memory writes,
  and audit failures return structured errors and log safe metadata with
  `request_id`/`trace_id` when available. All Phase 6 services propagate
  `request_id` from middleware context and generate per-operation `trace_id` for
  joined log/trace reconstruction. Redacted metadata coverage is verified before
  phase completion.
- **AI Evidence And Eval Gates**: PASS. No classifier/RAG eval is introduced.
  Memory TTL and selected long-term memory type must be documented in
  `docs/decisions.md` with rationale.
- **Critical Tests And CI**: PASS. Tests cover auth, refresh behavior, Vault key
  resolution, admin guard, invitation, Redis TTL, write-memory, no auto-writes,
  cross-conversation recall, reserved audit action names, audit rows, repository
  no-commit rule, and redaction leaks.
- **Simplicity**: PASS. The design uses the existing PostgreSQL, Redis, Vault,
  and pgvector stack, separates auth from authorization, and avoids chatbot or
  multi-agent behavior.

### Post-Design Recheck

- **Phase Scope**: PASS. Generated artifacts cover only Phase 6 auth,
  authorization, memory, audit, and required decisions.
- **Layered Architecture**: PASS. Data model and contracts separate API, domain,
  services, repositories, and infra adapters.
- **FastAPI Resource Management**: PASS. Contracts require lifespan-resolved
  signing key and injected clients/sessions.
- **Async Safety**: PASS. Redis and database paths are async; no long-running
  chatbot/RAG work is added. Long-term memory embedding work is offloaded via
  `asyncio.to_thread` to keep write-memory request paths non-blocking.
- **Secrets And Redaction**: PASS. Contracts and quickstart require redaction and
  no secret leakage in memory, audit, logs, or traces.
- **Observability And Errors**: PASS. API contract defines structured errors for
  auth, authorization, memory, cross-conversation recall, and audit failures.
  All services propagate `request_id` from middleware context and per-operation
  `trace_id` for joined log/trace reconstruction.
- **AI Evidence And Eval Gates**: PASS. `docs/decisions.md` updates for memory
  TTL and memory type are required.
- **Critical Tests And CI**: PASS. Quickstart lists critical tests for security,
  memory, audit, redaction, transaction boundaries, first-admin bootstrap,
  async-safe embedding, structured observability, and repository no-commit.
- **Simplicity**: PASS. No complexity exceptions were introduced.

## Project Structure

### Documentation (this feature)

```text
specs/006-auth-memory-audit/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── auth-memory.openapi.yaml
└── tasks.md              # Created by /speckit.tasks, not by /speckit.plan
```

### Source Code (repository root)

```text
app/
├── api/
│   ├── dependencies/
│   │   ├── auth.py
│   │   └── authorization.py
│   └── routes/
│       ├── auth.py
│       ├── admin.py
│       └── memory.py
├── services/
│   ├── auth_service.py
│   ├── authorization_service.py
│   ├── admin_invitation_service.py
│   ├── short_term_memory_service.py
│   ├── long_term_memory_service.py
│   └── audit_service.py
├── repositories/
│   ├── user_repository.py
│   ├── token_session_repository.py
│   ├── admin_invitation_repository.py
│   ├── memory_repository.py
│   └── audit_log_repository.py
├── domain/
│   ├── auth.py
│   ├── memory.py
│   └── audit.py
└── infra/
    ├── auth_provider.py
    ├── password_hasher.py
    ├── token_signer.py
    ├── vault_secrets.py
    ├── redis_memory.py
    ├── memory_embedding_client.py
    └── redaction.py

scripts/
├── seed_admin.py
└── ...

migrations/
tests/
├── unit/
│   ├── test_auth_service.py
│   ├── test_authorization_service.py
│   ├── test_admin_invitation_service.py
│   ├── test_short_term_memory_service.py
│   ├── test_long_term_memory_service.py
│   ├── test_audit_service.py
│   ├── test_memory_redaction.py
│   ├── test_repository_boundaries.py
│   └── test_observability_coverage.py
├── contract/
│   └── test_auth_memory_api_contract.py
└── integration/
    ├── test_auth_lifecycle_vault_key.py
    ├── test_refresh_token_flow.py
    ├── test_redis_memory_ttl.py
    ├── test_memory_audit_transaction.py
    ├── test_admin_invitation_flow.py
    └── test_cross_conversation_recall.py

docs/decisions.md
```

**Structure Decision**: Keep all Phase 6 behavior in the main backend `app/`.
Use FastAPI Users only as an auth adapter where it does not violate service-owned
transactions or repository boundaries. Keep authorization, admin invitation,
refresh sessions, memory, audit, and redaction as project-owned services. Redis
short-term memory belongs behind infra/service abstractions, PostgreSQL/pgvector
long-term memory belongs behind repositories/services, and `docs/decisions.md`
records the TTL, selected long-term memory type, cross-conversation recall
behavior, and reserved audit action policy. A controlled first-admin bootstrap
script (`scripts/seed_admin.py`) is required for the initial admin, after which
further admins are granted through the invitation flow. Repository boundaries
enforce that only services own `.commit()` calls and transaction coordination.

## Complexity Tracking

No constitution violations or complexity exceptions.
