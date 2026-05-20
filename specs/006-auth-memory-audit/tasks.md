---

description: "Task list for Phase 6 authentication, memory, and audit logging"
---

# Tasks: Authentication, Memory, and Audit Logging

**Input**: Design documents from `/specs/006-auth-memory-audit/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Tests are REQUIRED for critical behavior in this phase. Auth, refresh,
authorization, Redis TTL, explicit memory writes, cross-conversation recall,
audit logging, redaction leak behavior, structured observability, repository
no-commit, and async-safe embedding must all be covered before the phase is
considered complete.

**Organization**: Tasks are grouped by user story to enable independent
implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no unresolved dependency)
- **[Story]**: User story label (`[US1]` ... `[US5]`)
- Include exact file paths in every task

## Path Conventions

- **Backend**: `app/api`, `app/services`, `app/repositories`, `app/domain`,
  `app/infra`, `app/core`
- **Project support**: `migrations/`, `tests/`, `scripts/`, `docs/`, `specs/`

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Prepare the repo for Phase 6 auth, memory, and audit work.

- [ ] T001 Add Phase 6 authentication, hashing, token, and optional FastAPI Users dependencies in `pyproject.toml`
- [ ] T002 Create Phase 6 route and service module skeletons in `app/api/routes/auth.py`, `app/api/routes/admin.py`, `app/api/routes/memory.py`, `app/api/dependencies/auth.py`, `app/api/dependencies/authorization.py`, `app/services/auth_service.py`, `app/services/authorization_service.py`, `app/services/admin_invitation_service.py`, `app/services/short_term_memory_service.py`, `app/services/long_term_memory_service.py`, and `app/services/audit_service.py`
- [ ] T003 [P] Create Phase 6 repository, infra, and test module skeletons in `app/repositories/user_repository.py`, `app/repositories/token_session_repository.py`, `app/repositories/admin_invitation_repository.py`, `app/repositories/memory_repository.py`, `app/repositories/audit_log_repository.py`, `app/infra/auth_provider.py`, `app/infra/password_hasher.py`, `app/infra/token_signer.py`, `app/infra/vault_secrets.py`, `app/infra/redis_memory.py`, `app/infra/memory_embedding_client.py`, `tests/contract/test_auth_memory_api_contract.py`, `tests/unit/test_auth_service.py`, `tests/unit/test_authorization_service.py`, `tests/unit/test_admin_invitation_service.py`, `tests/unit/test_short_term_memory_service.py`, `tests/unit/test_long_term_memory_service.py`, `tests/unit/test_audit_service.py`, `tests/unit/test_audit_action_names.py`, `tests/unit/test_memory_redaction.py`, `tests/unit/test_repository_boundaries.py`, `tests/unit/test_observability_coverage.py`, `tests/unit/test_long_term_memory_recall.py`, `tests/integration/test_auth_lifecycle_vault_key.py`, `tests/integration/test_refresh_token_flow.py`, `tests/integration/test_admin_invitation_flow.py`, `tests/integration/test_redis_memory_ttl.py`, `tests/integration/test_memory_audit_transaction.py`, and `tests/integration/test_cross_conversation_recall.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Build the shared auth, memory, audit, and observability foundation required by all stories.

**⚠️ CRITICAL**: No user story work should begin before this phase is complete.

- [ ] T004 Create Phase 6 database migration for users, refresh sessions, admin invitations, long-term memory, and audit logs in `migrations/versions/0003_phase6_auth_memory_audit.py`
- [ ] T005 [P] Add Phase 6 typed settings for JWT key bootstrap, refresh expiry, invitation expiry, short-term memory TTL, and long-term memory configuration in `app/core/config.py`
- [ ] T006 [P] Implement lifespan bootstrap for Vault-resolved signing keys and shared auth/memory resources in `app/core/lifespan.py` and `app/core/application.py`
- [ ] T007 [P] Define shared auth, memory, and audit schemas/enums in `app/domain/auth.py`, `app/domain/memory.py`, and `app/domain/audit.py`
- [ ] T008 [P] Extend structured auth/memory/audit error mapping in `app/domain/errors.py` and `app/api/error_handlers.py`
- [ ] T009 [P] Propagate `request_id` from middleware context and generate per-operation `trace_id` in all Phase 6 services; add structured logging with redacted safe metadata for auth failures, role changes, memory writes, recall, and audit failures in `app/services/auth_service.py`, `app/services/authorization_service.py`, `app/services/short_term_memory_service.py`, `app/services/long_term_memory_service.py`, and `app/services/audit_service.py`
- [ ] T010 [P] Implement first-admin bootstrap: a controlled local seed path that creates the initial admin when no admin user exists, fails loudly when Vault signing key is unavailable, and is isolated from normal registration in `app/services/auth_service.py` and `scripts/seed_admin.py`
- [ ] T011 [P] Add repository no-commit verification tests proving repositories never call `.commit()` and services own all transaction boundaries in `tests/unit/test_repository_boundaries.py`
- [ ] T012 [P] Implement shared infra adapters for password hashing, token signing, Vault key loading, Redis short-term memory access, and semantic memory embedding in `app/infra/password_hasher.py`, `app/infra/token_signer.py`, `app/infra/vault_secrets.py`, `app/infra/redis_memory.py`, and `app/infra/memory_embedding_client.py`
- [ ] T013 Implement shared repository scaffolding for users, token sessions, admin invitations, memory, and audit persistence in `app/repositories/user_repository.py`, `app/repositories/token_session_repository.py`, `app/repositories/admin_invitation_repository.py`, `app/repositories/memory_repository.py`, and `app/repositories/audit_log_repository.py`

**Checkpoint**: Foundation ready. User story implementation can begin.

---

## Phase 3: User Story 1 - Register And Log In Securely (Priority: P1) 🎯 MVP

**Goal**: Let a user register, log in, refresh tokens, and access authenticated capabilities only when Vault-resolved signing keys are available.

**Independent Test**: Register a user, log in, refresh tokens, and call `/users/me`; verify startup-safe failure when signing keys are unavailable.

### Tests for User Story 1 (REQUIRED) ⚠️

- [ ] T014 [P] [US1] Add contract coverage for `/auth/register`, `/auth/login`, `/auth/refresh`, and `/users/me` in `tests/contract/test_auth_memory_api_contract.py`
- [ ] T015 [P] [US1] Add integration coverage for registration, login, signing-key startup failure, and refresh rotation in `tests/integration/test_auth_lifecycle_vault_key.py` and `tests/integration/test_refresh_token_flow.py`
- [ ] T016 [P] [US1] Add unit coverage for credential validation, token session rotation, and signing-key guards in `tests/unit/test_auth_service.py`

### Implementation for User Story 1

- [ ] T017 [P] [US1] Implement user and token-session persistence methods in `app/repositories/user_repository.py` and `app/repositories/token_session_repository.py`
- [ ] T018 [US1] Implement registration, login, refresh, and current-user workflows in `app/services/auth_service.py` and `app/infra/auth_provider.py`
- [ ] T019 [US1] Implement auth endpoints and current-user dependency wiring in `app/api/routes/auth.py` and `app/api/dependencies/auth.py`

**Checkpoint**: User Story 1 is independently functional and testable.

---

## Phase 4: User Story 2 - Enforce Admin Authorization (Priority: P2)

**Goal**: Restrict admin-only capabilities, support expiring admin invitations, and record stable audit action names for privileged workflows.

**Independent Test**: Verify only admins can create invitations and list audit logs; accepting a valid invitation grants admin role and records audit data.

### Tests for User Story 2 (REQUIRED) ⚠️

- [ ] T020 [P] [US2] Add contract coverage for `/admin/invitations`, `/admin/invitations/accept`, and `/admin/audit-logs` in `tests/contract/test_auth_memory_api_contract.py`
- [ ] T021 [P] [US2] Add unit coverage for `require_admin`, invitation expiry handling, and reserved audit action names in `tests/unit/test_authorization_service.py`, `tests/unit/test_admin_invitation_service.py`, and `tests/unit/test_audit_action_names.py`
- [ ] T022 [P] [US2] Add integration coverage for admin invitation creation, acceptance, and audited role change in `tests/integration/test_admin_invitation_flow.py`

### Implementation for User Story 2

- [ ] T023 [P] [US2] Implement authorization context and admin guard dependencies in `app/services/authorization_service.py` and `app/api/dependencies/authorization.py`
- [ ] T024 [P] [US2] Implement admin invitation persistence and role-change hooks in `app/repositories/admin_invitation_repository.py` and `app/services/admin_invitation_service.py`
- [ ] T025 [US2] Implement admin invitation endpoints and admin audit-log route behavior in `app/api/routes/admin.py` and `app/services/audit_service.py`

**Checkpoint**: User Story 2 is independently functional and testable.

---

## Phase 5: User Story 3 - Use Short-Term Conversation Memory (Priority: P3)

**Goal**: Allow authenticated users to store and read redacted short-term memory in Redis with a configurable TTL.

**Independent Test**: One user can write/read short-term memory before expiry; another user cannot read it; expired values disappear.

### Tests for User Story 3 (REQUIRED) ⚠️

- [ ] T026 [P] [US3] Add contract coverage for `GET /memory/short-term` and `PUT /memory/short-term` in `tests/contract/test_auth_memory_api_contract.py`
- [ ] T027 [P] [US3] Add unit coverage for TTL handling, user isolation, and pre-persistence redaction in `tests/unit/test_short_term_memory_service.py` and `tests/unit/test_memory_redaction.py`
- [ ] T028 [P] [US3] Add integration coverage for Redis-backed short-term memory expiry in `tests/integration/test_redis_memory_ttl.py`

### Implementation for User Story 3

- [ ] T029 [P] [US3] Implement short-term memory request/response models and Redis adapter behavior in `app/domain/memory.py` and `app/infra/redis_memory.py`
- [ ] T030 [US3] Implement short-term memory redaction and TTL workflows in `app/services/short_term_memory_service.py`
- [ ] T031 [US3] Implement short-term memory routes in `app/api/routes/memory.py`

**Checkpoint**: User Story 3 is independently functional and testable.

---

## Phase 6: User Story 4 - Explicitly Write Long-Term Memory With Audit Trail (Priority: P4)

**Goal**: Persist only explicit semantic memory writes, redact content before persistence, create one atomic audit row per successful write, and ensure embedding generation does not block async request paths.

**Independent Test**: Calling write-memory persists only redacted semantic memory, creates exactly one audit row, normal requests create no long-term memory, and embedding work does not block the event loop.

### Tests for User Story 4 (REQUIRED) ⚠️

- [ ] T032 [P] [US4] Add contract coverage for `POST /memory/long-term` in `tests/contract/test_auth_memory_api_contract.py`
- [ ] T033 [P] [US4] Add unit coverage for explicit write-memory, semantic-only validation, audit row creation, and no-auto-write behavior in `tests/unit/test_long_term_memory_service.py` and `tests/unit/test_audit_service.py`
- [ ] T034 [P] [US4] Add integration coverage for redacted long-term memory persistence and atomic audit writes in `tests/integration/test_memory_audit_transaction.py`
- [ ] T035 [P] [US4] Add unit coverage proving embedding generation uses `asyncio.to_thread` or an async-safe provider and does not block the event loop in `tests/unit/test_long_term_memory_service.py`

### Implementation for User Story 4

- [ ] T036 [P] [US4] Implement semantic memory and audit persistence methods in `app/repositories/memory_repository.py` and `app/repositories/audit_log_repository.py`
- [ ] T037 [P] [US4] Implement audit action constants and safe metadata shaping in `app/services/audit_service.py` and `app/infra/redaction.py`
- [ ] T038 [US4] Implement explicit semantic write-memory workflow with pgvector embedding support, using `asyncio.to_thread` to wrap any blocking embedding calls so the request path remains non-blocking, in `app/services/long_term_memory_service.py` and `app/infra/memory_embedding_client.py`
- [ ] T039 [US4] Implement explicit write-memory endpoint and structured failure responses in `app/api/routes/memory.py` and `app/api/error_handlers.py`

**Checkpoint**: User Story 4 is independently functional and testable.

---

## Phase 7: User Story 5 - Recall Explicit Memory Across Conversations (Priority: P5)

**Goal**: Allow a user to recall only their own explicitly written long-term memory in a later conversation.

**Independent Test**: Memory written in one conversation can be recalled in another conversation only for the same user; no recall exists for normal requests that never called write-memory.

### Tests for User Story 5 (REQUIRED) ⚠️

- [ ] T040 [P] [US5] Add contract coverage for `POST /memory/long-term/recall` in `tests/contract/test_auth_memory_api_contract.py`
- [ ] T041 [P] [US5] Add unit coverage for same-user recall scoping and cross-user leakage prevention in `tests/unit/test_long_term_memory_recall.py`
- [ ] T042 [P] [US5] Add integration coverage for cross-conversation recall and no recall from normal requests in `tests/integration/test_cross_conversation_recall.py`

### Implementation for User Story 5

- [ ] T043 [P] [US5] Implement recall query models and same-user semantic search methods in `app/domain/memory.py` and `app/repositories/memory_repository.py`
- [ ] T044 [US5] Implement cross-conversation recall workflow in `app/services/long_term_memory_service.py`
- [ ] T045 [US5] Implement recall route and safe response shaping in `app/api/routes/memory.py`

**Checkpoint**: User Story 5 is independently functional and testable.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Finish the phase with documentation, leak checks, observability coverage, and quickstart validation.

- [ ] T046 [P] Update Phase 6 memory/auth decision records in `docs/decisions.md` and keep command guidance aligned in `specs/006-auth-memory-audit/quickstart.md`
- [ ] T047 [P] Update architecture, security, and runbook docs for auth, Vault-backed signing keys, Redis memory, audit operations, and first-admin bootstrap in `docs/architecture.md`, `docs/security.md`, and `docs/runbook.md`
- [ ] T048 [P] Add Phase 6 cross-cutting leak and route-boundary coverage in `tests/test_no_secrets.py` and `tests/test_route_boundaries.py`
- [ ] T049 [P] Verify structured observability coverage: confirm `request_id`/`trace_id` appear on structured logs for auth failures, role changes, memory writes, recall, and audit failures; confirm no raw secrets, passwords, or unredacted memory content appear in log or trace metadata in `tests/unit/test_observability_coverage.py`
- [ ] T050 Run Phase 6 quickstart validation and record any command or path corrections in `specs/006-auth-memory-audit/quickstart.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1: Setup**: No dependencies.
- **Phase 2: Foundational**: Depends on Phase 1 and blocks all user stories.
- **Phase 3: US1**: Depends on Phase 2.
- **Phase 4: US2**: Depends on Phase 2 and authenticated flows from US1.
- **Phase 5: US3**: Depends on Phase 2 and authenticated flows from US1.
- **Phase 6: US4**: Depends on Phase 2 and authenticated flows from US1.
- **Phase 7: US5**: Depends on Phase 6 because recall requires explicit long-term memory writes.
- **Phase 8: Polish**: Depends on the desired user stories being complete.

### User Story Dependencies

- **US1 (P1)**: Independent after Phase 2. MVP foundation for the rest of the phase.
- **US2 (P2)**: Requires authenticated user and admin role flows from US1 plus first-admin bootstrap (T010) from Phase 2.
- **US3 (P3)**: Requires authenticated user context from US1.
- **US4 (P4)**: Requires authenticated user context from US1 and shared redaction/audit/observability foundation from Phase 2.
- **US5 (P5)**: Requires US4 because recall only applies to explicitly written long-term memory.

### Within Each User Story

- Write tests first and make sure they fail before implementation.
- Repositories and infra adapters come before service workflows.
- Services come before routes and dependency wiring.
- Route handlers stay thin and call dependencies/services only.

## Parallel Opportunities

- **Setup**: `T003`
- **Foundational**: `T005`, `T006`, `T007`, `T008`, `T009`, `T010`, `T011`, `T012`
- **US1**: `T014`, `T015`, `T016`, `T017`
- **US2**: `T020`, `T021`, `T022`, `T023`, `T024`
- **US3**: `T026`, `T027`, `T028`, `T029`
- **US4**: `T032`, `T033`, `T034`, `T035`, `T036`, `T037`
- **US5**: `T040`, `T041`, `T042`, `T043`
- **Polish**: `T046`, `T047`, `T048`, `T049`

## Parallel Example: User Story 1

```bash
# Launch User Story 1 test work together:
Task: "Add contract coverage for /auth/register, /auth/login, /auth/refresh, and /users/me in tests/contract/test_auth_memory_api_contract.py"
Task: "Add integration coverage for registration, login, signing-key startup failure, and refresh rotation in tests/integration/test_auth_lifecycle_vault_key.py and tests/integration/test_refresh_token_flow.py"
Task: "Add unit coverage for credential validation, token session rotation, and signing-key guards in tests/unit/test_auth_service.py"

# Launch User Story 1 persistence work together:
Task: "Implement user and token-session persistence methods in app/repositories/user_repository.py and app/repositories/token_session_repository.py"
Task: "Implement registration, login, refresh, and current-user workflows in app/services/auth_service.py and app/infra/auth_provider.py"
```

## Parallel Example: User Story 4

```bash
# Launch User Story 4 test work together:
Task: "Add contract coverage for POST /memory/long-term in tests/contract/test_auth_memory_api_contract.py"
Task: "Add unit coverage for explicit write-memory, semantic-only validation, audit row creation, and no-auto-write behavior in tests/unit/test_long_term_memory_service.py and tests/unit/test_audit_service.py"
Task: "Add integration coverage for redacted long-term memory persistence and atomic audit writes in tests/integration/test_memory_audit_transaction.py"
Task: "Add unit coverage proving embedding generation uses asyncio.to_thread in tests/unit/test_long_term_memory_service.py"

# Launch User Story 4 persistence and audit work together:
Task: "Implement semantic memory and audit persistence methods in app/repositories/memory_repository.py and app/repositories/audit_log_repository.py"
Task: "Implement audit action constants and safe metadata shaping in app/services/audit_service.py and app/infra/redaction.py"
```

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (including observability, first-admin bootstrap, repo no-commit tests)
3. Complete Phase 3: US1
4. Validate registration, login, refresh, and `/users/me`
5. Stop and verify the authenticated foundation before expanding scope

### Incremental Delivery

1. Complete Setup + Foundational
2. Deliver **US1** as the MVP authentication slice
3. Add **US2** and **US3** once authenticated user flows are stable
4. Add **US4** for explicit durable memory with audit guarantees and async-safe embedding
5. Add **US5** for cross-conversation recall after explicit memory writes exist
6. Finish with docs, leak checks, observability coverage verification, and quickstart validation

### Parallel Team Strategy

With multiple contributors:

1. One contributor completes Setup + Foundational
2. After Phase 2, one contributor takes **US1**, another can prepare **US2** tests, and another can prepare **US3** tests
3. **US4** can begin after **US1** and foundational audit/redaction/observability pieces are stable
4. **US5** follows **US4** because recall depends on explicit long-term writes
