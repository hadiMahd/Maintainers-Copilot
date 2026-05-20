# Quickstart: Authentication, Memory, and Audit Logging

## Prerequisites

- Phase 1 foundation exists with app factory, lifespan, dependency injection,
  PostgreSQL, Redis, Vault dev mode, structured errors, request IDs, and
  redaction infrastructure.
- Vault or a test fake can provide the JWT signing key during startup.
- PostgreSQL migrations for users, refresh sessions, admin invitations,
  long-term memory, pgvector embeddings, and audit logs are applied.
- Redis is available for short-term memory TTL tests.

## Validate Startup Secret Resolution

Start the app with a valid Vault/test signing key.

Expected result: token issuance is enabled.

Start the app without a resolvable signing key.

Expected result: token issuance fails safely and no weak fallback key is used.

## Bootstrap First Admin

Run the first-admin seed script:

```bash
uv run python scripts/seed_admin.py --email admin@example.com --password <password>
```

Expected result: one admin account is created when no admin exists; running
again reports that an admin already exists; the script fails loudly when the
Vault signing key is unavailable. After this step, further admin access is
granted through the `/admin/invitations` flow.

## Register And Log In

Call registration with a new email/password, then log in with the same
credentials.

Expected result: a regular user account is created, login returns an access
token and refresh token, and `/users/me` returns the authenticated user.

## Validate Refresh Flow

Use a valid refresh token to request a new token pair.

Expected result: refresh succeeds, token session state is updated, and replaying
an old, expired, revoked, or malformed refresh token fails safely.

## Validate Admin Guard

Call an admin-only endpoint as a regular user and as an admin.

Expected result: the regular user receives a structured authorization error; the
admin succeeds.

## Validate Admin Invitation

Create an admin invitation as an admin, then accept it as the invited user.

Expected result: the invited user receives the admin role, and invitation
creation plus role activation create audit rows.

## Validate Short-Term Memory

Write short-term memory for a user and read it before expiry.

Expected result: the same user can read the redacted value before TTL expiry, a
different user cannot read it, and the value is unavailable after the configured
TTL.

## Validate Explicit Long-Term Memory

Call the explicit write-memory capability with semantic memory content containing
fake secret values.

Expected result: redaction runs before persistence, long-term memory is written
with pgvector embedding metadata, exactly one audit row is created, and fake
secret values do not appear unredacted in memory, audit metadata, logs, or
traces.

## Validate Cross-Conversation Recall

Explicitly write long-term semantic memory in one conversation, then start a
separate conversation for the same user and query memory recall.

Expected result: only the explicitly written redacted memory is recallable for
the same user; another user cannot recall it, and normal requests that did not
call write-memory produce no recallable long-term memory.

## Validate Reserved Audit Actions

Inspect audit service constants or schema support for:

- `memory.write`
- `role.change`
- `admin_invitation.create`
- `widget_config.create`
- `widget_config.update`
- `widget_config.delete`
- `conversation.delete`

Expected result: Phase 6 workflows use the current action names, and later
widget/conversation workflows have reserved action names to reuse.

## Validate No Auto-Writes

Run normal authenticated requests that do not call write-memory.

Expected result: no long-term memory rows are created.

## Validate Async Embedding Safety

Call the explicit write-memory capability and verify the request path completes
without blocking the event loop. Inspect `memory_embedding_client.py` to confirm
any blocking embedding call is wrapped with `asyncio.to_thread` or uses an
async-safe provider.

Expected result: the write-memory request completes under the service timeout;
the test suite includes a unit test proving `asyncio.to_thread` wrapping.

## Validate Structured Observability

Trigger auth login failure, a role change, a memory write, and a memory recall.
Inspect JSON-formatted structured log output.

Expected result: every event carries `request_id` and `trace_id` in the log
context; no raw passwords, tokens, signing key material, invitation tokens, or
unredacted memory content appear in log payloads or trace metadata.

## Run Critical Tests

Run:

```bash
uv run pytest tests/unit/test_auth_service.py
uv run pytest tests/unit/test_authorization_service.py
uv run pytest tests/unit/test_admin_invitation_service.py
uv run pytest tests/unit/test_short_term_memory_service.py
uv run pytest tests/unit/test_long_term_memory_service.py
uv run pytest tests/unit/test_audit_service.py
uv run pytest tests/unit/test_audit_action_names.py
uv run pytest tests/unit/test_memory_redaction.py
uv run pytest tests/unit/test_repository_boundaries.py
uv run pytest tests/unit/test_observability_coverage.py
uv run pytest tests/contract/test_auth_memory_api_contract.py
uv run pytest tests/integration/test_auth_lifecycle_vault_key.py
uv run pytest tests/integration/test_refresh_token_flow.py
uv run pytest tests/integration/test_admin_invitation_flow.py
uv run pytest tests/integration/test_redis_memory_ttl.py
uv run pytest tests/integration/test_cross_conversation_recall.py
uv run pytest tests/integration/test_memory_audit_transaction.py
```

Expected result: auth, authorization, memory, audit, redaction, transaction,
observability, embedding safety, and repository boundary tests pass.

## Update Decisions

Update `docs/decisions.md` with:

- selected short-term memory TTL and rationale
- selected long-term memory type, expected to be semantic unless implementation
  records a better justified choice
- redaction-before-persistence policy
- audit policy for memory writes, role/admin changes, widget config changes, and
  conversation deletion
- cross-conversation recall behavior for explicit long-term memory
- FastAPI Users integration decision and any fallback if it does not fit service
  transaction boundaries

Expected result: reviewers can verify the security and memory choices before
the phase is considered complete.
