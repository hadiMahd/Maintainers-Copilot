# Research: Foundation and Architecture Skeleton

## Decision: Use an explicit app factory with lifespan-owned resources

**Rationale**: A single app creation path makes imports side-effect-light and
keeps startup/shutdown behavior auditable. Lifespan is the right ownership point
for shared resources that future phases will need, such as database engines,
Redis clients, Vault clients, model clients, and LLM clients.

**Alternatives considered**:
- Module-level application instance with import-time setup: rejected because it
  hides side effects and makes tests fragile.
- Creating clients per request: rejected because it wastes resources and violates
  the constitution.

## Decision: Use dependency injection for settings, request context, sessions,
repositories, and services

**Rationale**: Dependency injection keeps routes HTTP-only and makes test fakes
straightforward. It also preserves the service/repository boundary required by
the constitution.

**Alternatives considered**:
- Direct imports of settings or repositories in routes: rejected because it
  couples routes to implementation details.
- Global singletons for all dependencies: rejected because they obscure resource
  ownership and complicate tests.

## Decision: Use pydantic-settings for typed configuration

**Rationale**: Typed configuration gives loud startup failures for missing
required values and supports a safe `.env.example` with fake local bootstrap
values.

**Alternatives considered**:
- Scattered `os.getenv` calls: rejected because they are hard to audit and are
  prohibited by the Phase 1 acceptance criteria.
- Untyped configuration dictionaries: rejected because missing or malformed
  values fail too late.

## Decision: Use SQLAlchemy async with asyncpg and Alembic baseline

**Rationale**: The project requires an async database path and a controlled
migration baseline for future phases. Phase 1 only wires the session and baseline;
it does not add feature persistence.

**Alternatives considered**:
- Synchronous SQLAlchemy sessions: rejected because they can block async request
  paths.
- Skipping migrations until a later phase: rejected because future persistence
  work needs a controlled migration path from the start.

## Decision: Represent required infrastructure in Docker Compose

**Rationale**: Docker Compose gives reviewers and developers one local stack
shape for API, model server, chatbot, widget, host demo, migrations, Postgres
with pgvector, Redis, MinIO, and Vault dev mode. Phase 1 validates service
configuration without implementing future application behavior.

**Alternatives considered**:
- Running only the API locally: rejected because later phases depend on a shared
  stack contract.
- Adding heavier orchestration such as Kubernetes: rejected as unnecessary for a
  solo bootcamp project.

## Decision: Use structured logging with request IDs and domain exception mapping

**Rationale**: Request IDs and structured errors make failures reviewable without
exposing stack traces to users. The foundation needs one clean error mapping path
before feature-specific errors are added.

**Alternatives considered**:
- Plain text logging and ad hoc exceptions: rejected because logs become hard to
  correlate and errors become inconsistent.
- Returning raw exceptions: rejected because users must never see stack traces.

## Decision: Keep model server, chatbot, widget, and host demo as skeleton areas

**Rationale**: The repository must show future ownership locations without
claiming future behavior. Empty or minimal skeletons are acceptable only when
they are clearly not production-complete.

**Alternatives considered**:
- Implementing placeholder chatbot/widget behavior now: rejected as future-phase
  scope creep.
- Omitting future directories entirely: rejected because the Phase 1 spec
  requires a phase-ready structure.
