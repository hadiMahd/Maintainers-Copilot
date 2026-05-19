# Research: Authentication, Memory, and Audit Logging

## Decision: Use FastAPI Users selectively, not as the whole auth architecture

**Rationale**: FastAPI Users provides ready registration/login routes,
SQLAlchemy async support, JWT strategy support, and a `current_user` dependency
factory. Those are useful for the basic email/password path. However, the project
requires service-owned transactions, Vault-resolved signing keys, refresh token
rotation/revocation, admin invitations, audit logs, and memory redaction, so
project services must remain the source of business behavior.

**Alternatives considered**:
- Use FastAPI Users for everything auth-related: rejected because role changes,
  invitations, refresh sessions, audit, and transaction ownership are project
  requirements beyond the library boundary.
- Build every auth primitive from scratch: rejected unless integration proves
  incompatible, because the library can reduce boilerplate for registration,
  password hashing, JWT auth, and current-user dependency patterns.

## Decision: Keep authentication and authorization separate

**Rationale**: Authentication answers who the caller is; authorization answers
what they may do. Keeping `current_user` separate from `require_admin` keeps
admin guards auditable and testable.

**Alternatives considered**:
- Encode role checks inside auth token validation only: rejected because role
  changes and admin invitations need centralized audit and current database
  state.
- Duplicate role checks in each route: rejected because it is easy to miss and
  hard to test consistently.

## Decision: Resolve JWT signing key from Vault during lifespan startup

**Rationale**: The constitution requires secrets to resolve from Vault or test
fakes at startup. Loading the signing key during lifespan makes startup state
explicit and prevents token issuance with placeholder or missing secrets.

**Alternatives considered**:
- Read signing key directly from environment variables: rejected because real
  signing keys must not live in repository or local `.env` files.
- Fetch signing key per request: rejected because it adds latency and runtime
  failure points to every auth request.

## Decision: Implement project-owned refresh token sessions

**Rationale**: Refresh tokens need expiry, revocation, and replay-safe rotation.
Keeping refresh sessions in project services/repositories lets audit and
transaction behavior match the rest of the app.

**Alternatives considered**:
- Stateless refresh JWT only: rejected because revocation and replay detection
  are weaker.
- Rely entirely on access-token lifetime: rejected because the phase explicitly
  requires a JWT/refresh token mechanism.

## Decision: Use Redis async client for short-term memory with configurable TTL

**Rationale**: Short-term conversation memory should be fast, user-scoped, and
temporary. Redis TTL semantics fit the requirement, and async access keeps
request paths non-blocking.

**Alternatives considered**:
- Store short-term memory in PostgreSQL: rejected because the requirement states
  short-term memory belongs in Redis.
- No TTL: rejected because the TTL must be explicit, configurable, and
  documented in `DECISIONS.md`.

## Decision: Use semantic long-term memory for Phase 6

**Rationale**: Maintainer's Copilot later needs durable facts/preferences that
can be retrieved by meaning. Semantic memory best matches explicit long-term
write-memory use without pretending to store full episode histories or
procedural instructions. The decision must be recorded in `DECISIONS.md`.

**Alternatives considered**:
- Episodic memory: rejected for Phase 6 because full conversation episodes are
  more privacy-sensitive and overlap with future chatbot orchestration.
- Procedural memory: rejected because this phase is not teaching the assistant
  durable procedures or policies beyond explicit user-approved facts.

## Decision: No automatic long-term memory writes

**Rationale**: Long-term memory is persistent and sensitive. Requiring explicit
write-memory calls keeps consent and auditability clear before chatbot
orchestration exists.

**Alternatives considered**:
- Auto-write every chat or tool output: rejected because it violates the phase
  scope and increases privacy risk.
- Auto-write only high-confidence facts: rejected because no memory extraction
  evaluator exists in this phase.

## Decision: Redaction precedes memory persistence and audit metadata

**Rationale**: Memory content and audit metadata may contain tokens, credentials,
or private issue text. Redaction must happen before data reaches Redis,
PostgreSQL, audit logs, logs, or traces.

**Alternatives considered**:
- Redact only logs: rejected because persisted memory and audit metadata can
  leak sensitive content too.
- Redact after persistence: rejected because the unredacted value would already
  have crossed a storage boundary.

## Decision: Services own transaction boundaries and repositories never commit

**Rationale**: Memory writes and audit rows must succeed or fail together. Role
changes and audit rows also need atomicity. Services should coordinate
repositories and commit/rollback once per workflow.

**Alternatives considered**:
- Repository-level commits: rejected because multi-entity workflows can leave
  unaudited or partially persisted state.
- Route-level commits: rejected because routes must remain HTTP mapping only.

## Decision: Reserve audit action names for later widget and conversation flows

**Rationale**: The project brief requires audit logs for memory writes, role
changes, widget config changes, and conversation deletions. Defining stable
action names in Phase 6 prevents later phases from inventing incompatible audit
events and keeps audit rows queryable.

**Alternatives considered**:
- Let each later phase choose action names independently: rejected because audit
  reporting would become inconsistent.
- Use free-form action text only: rejected because tests and reviewers need
  stable action values.

## Decision: Demonstrate cross-conversation recall only for explicit memory

**Rationale**: Long-term memory must be useful, but it must not auto-write. The
demo proves explicit same-user semantic memory can be recalled in a later
conversation while preserving the no-auto-write rule.

**Alternatives considered**:
- Demo recall from short-term Redis memory: rejected because the brief asks for
  long-term cross-conversation recall.
- Auto-write facts for the demo: rejected because it violates explicit consent.

## Sources

- FastAPI Users overview: https://fastapi-users.github.io/fastapi-users/latest/configuration/overview/
- FastAPI Users full SQLAlchemy/JWT example: https://fastapi-users.github.io/fastapi-users/latest/configuration/full-example/
- FastAPI Users project status and features: https://fastapi-users.github.io/fastapi-users/latest/
