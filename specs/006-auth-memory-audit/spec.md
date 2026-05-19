# Feature Specification: Authentication, Memory, and Audit Logging

**Feature Branch**: `006-auth-memory-audit`  
**Created**: 2026-05-18  
**Status**: Draft  
**Input**: User description: "Phase 6, Build authentication, authorization, memory, and audit logging."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Register And Log In Securely (Priority: P1)

A new user can register with email and password, log in, and receive credentials
that let them access authenticated capabilities without exposing signing secrets.

**Why this priority**: Authentication is the foundation for every later
user-specific capability, including memory and audit trails.

**Independent Test**: Register a user, log in with the same credentials, verify
that authenticated access succeeds, and verify that token issuance depends on a
signing key resolved during startup.

**Acceptance Scenarios**:

1. **Given** a user has not registered before, **When** they submit a valid email
   and password, **Then** an account is created with the regular user role.
2. **Given** a registered user submits valid credentials, **When** they log in,
   **Then** they receive an access token and refresh token.
3. **Given** the signing key cannot be resolved at startup, **When** the system
   starts or token issuance is attempted, **Then** authentication fails safely
   without issuing unsigned or weakly signed tokens.

---

### User Story 2 - Enforce Admin Authorization (Priority: P2)

An admin can invite another admin and perform admin-only actions, while regular
users are rejected from admin-only capabilities.

**Why this priority**: Role enforcement protects privileged operations such as
role changes, admin invitation, and later operational controls.

**Independent Test**: Create a regular user and an admin user, attempt the same
admin-only action with both, and verify that only the admin succeeds and that
role changes, admin invitations, future widget configuration changes, and future
conversation deletions use stable audit action names.

**Acceptance Scenarios**:

1. **Given** an authenticated regular user, **When** they call an admin-only
   capability, **Then** access is rejected with a structured authorization error.
2. **Given** an authenticated admin, **When** they create an admin invitation,
   **Then** an invitation is created and the action is recorded in the audit log.
3. **Given** a valid admin invitation is accepted, **When** the invited person
   completes registration or role activation, **Then** they receive the admin
   role and the role change is audited.

---

### User Story 3 - Use Short-Term Conversation Memory (Priority: P3)

An authenticated user can write and read short-term conversation memory that
expires according to a documented, configurable TTL.

**Why this priority**: Later chatbot flows need short-lived context, but this
phase must prove memory isolation and expiry before chatbot orchestration exists.

**Independent Test**: Write a short-term memory value for one authenticated user,
read it back, verify another user cannot read it, and verify expiry behavior
using the configured TTL.

**Acceptance Scenarios**:

1. **Given** an authenticated user, **When** they write short-term memory,
   **Then** the memory is stored for that user with the configured TTL.
2. **Given** short-term memory exists for a user, **When** the same user reads
   memory before expiry, **Then** the stored value is returned.
3. **Given** the configured TTL has elapsed, **When** the user reads short-term
   memory, **Then** the expired value is not returned.

---

### User Story 4 - Explicitly Write Long-Term Memory With Audit Trail (Priority: P4)

An authenticated user or future tool can explicitly request a long-term memory
write, and the system redacts content before persistence and records an audit
entry.

**Why this priority**: Long-term memory is sensitive and persistent. The phase
must prove explicit consent, redaction, traceability, and no automatic long-term
writes before full chatbot behavior is added.

**Independent Test**: Call the explicit write-memory capability with content
containing fake secrets, verify persisted memory is redacted, verify no
auto-write occurs without the explicit request, and verify an audit row is
created for the write.

**Acceptance Scenarios**:

1. **Given** an authenticated user submits an explicit long-term memory write,
   **When** the content is accepted, **Then** redacted memory is persisted and an
   audit row is created.
2. **Given** user content contains secret-like values, **When** long-term memory
   is written, **Then** persisted memory and audit metadata do not include the
   unredacted secret-like values.
3. **Given** a normal authenticated request that does not explicitly call
   write-memory, **When** the request completes, **Then** no long-term memory is
   written.

---

### User Story 5 - Recall Explicit Memory Across Conversations (Priority: P5)

An authenticated user can explicitly write long-term memory in one conversation
and later retrieve that memory in a separate conversation, while normal requests
that do not call write-memory never create recallable long-term memory.

**Why this priority**: The project brief requires a cross-conversation recall
demo and a clear consent boundary for persistent memory.

**Independent Test**: Explicitly write semantic memory for a user, start a new
conversation, query memory recall, and verify the memory is available only for
that user and only because it was explicitly written.

**Acceptance Scenarios**:

1. **Given** a user explicitly writes long-term memory, **When** a later
   conversation queries relevant memory, **Then** the redacted memory can be
   recalled for that same user.
2. **Given** another user starts a conversation, **When** they query memory,
   **Then** the first user's long-term memory is unavailable.
3. **Given** a normal request does not call write-memory, **When** a later
   conversation queries memory, **Then** no memory from that request is recalled.

### Edge Cases

- Registration uses an already registered email: the request is rejected without
  revealing more account details than necessary.
- Password is missing, weak, or malformed: registration fails with a structured
  validation error.
- Login credentials are invalid: login fails without issuing tokens.
- Refresh token is expired, revoked, malformed, or reused after rotation:
  refresh fails safely.
- JWT signing key is missing or unavailable at startup: token issuance is
  disabled and startup behavior is safe.
- Admin invitation is expired, already accepted, malformed, or revoked: role
  activation is rejected and the failure is auditable where appropriate.
- A regular user attempts an admin-only operation: access is rejected and no role
  or memory state changes.
- Short-term memory TTL is missing or invalid: startup or configuration
  validation fails safely.
- Short-term memory has expired: reads return no value rather than stale context.
- Long-term memory type is not the chosen supported type: the write is rejected.
- Redaction detects secret-like content: unredacted content is not persisted to
  memory, audit metadata, logs, or traces.
- Long-term memory persistence succeeds but audit logging fails: the operation
  does not leave an unaudited memory write.
- Audit metadata is too large or contains sensitive text: metadata is bounded and
  redacted.
- A later phase changes widget configuration: the service must use reserved
  widget audit action names instead of inventing incompatible events.
- A conversation is deleted: the deletion must create an audit row with safe
  metadata and no raw conversation content.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST support email/password registration for regular
  users.
- **FR-002**: The system MUST support login that issues an access token and a
  refresh token.
- **FR-003**: The system MUST load the JWT signing key from Vault at startup
  before issuing tokens.
- **FR-004**: The system MUST reject token issuance when the signing key is
  unavailable or invalid.
- **FR-005**: The system MUST support user and admin roles.
- **FR-006**: The system MUST provide authorization dependencies or guards for
  authenticated users and admins.
- **FR-007**: Admin-only capabilities MUST reject regular users.
- **FR-008**: The system MUST support an admin invitation flow for granting admin
  access.
- **FR-009**: Role changes and admin invitation actions MUST be recorded in audit
  logs.
- **FR-009a**: The audit service MUST define stable action names for
  `memory.write`, `role.change`, `admin_invitation.create`,
  `widget_config.create`, `widget_config.update`, `widget_config.delete`, and
  `conversation.delete`.
- **FR-009b**: Later widget configuration and conversation deletion workflows
  MUST use the reserved audit action names and service transaction boundaries.
- **FR-010**: The system MUST support short-term conversation memory in Redis.
- **FR-011**: Short-term memory MUST have an explicit configurable TTL.
- **FR-012**: The selected short-term memory TTL MUST be documented in
  `DECISIONS.md`.
- **FR-013**: The system MUST support long-term memory in Postgres with pgvector.
- **FR-014**: The long-term memory type MUST be exactly one of episodic,
  semantic, or procedural.
- **FR-015**: The selected long-term memory type and rationale MUST be defended
  in `DECISIONS.md`.
- **FR-016**: The system MUST provide an explicit write-memory service or tool
  for long-term memory writes.
- **FR-017**: The system MUST NOT automatically write to long-term memory from
  normal requests.
- **FR-018**: Redaction MUST run before any short-term or long-term memory
  persistence.
- **FR-019**: Long-term memory writes MUST create an audit log row.
- **FR-020**: Audit logs MUST include `id`, `actor_user_id`, `action`,
  `target_type`, `target_id`, `timestamp`, and `metadata`.
- **FR-021**: Audit metadata MUST be safe, bounded, and free of unredacted
  memory content or secrets.
- **FR-022**: Structured errors MUST be returned for registration, login,
  authorization, memory, redaction, and audit failures.
- **FR-023**: This phase MUST NOT implement full chatbot orchestration, automatic
  memory extraction, RAG question answering, UI work, or widget behavior.
- **FR-024**: Cross-conversation recall MUST retrieve only explicitly written
  long-term memory for the same user.
- **FR-025**: Tests MUST cover registration, login, token signing-key behavior,
  refresh behavior, admin guard, admin invitation, short-term memory read/write,
  long-term write-memory, cross-conversation recall, reserved audit action names,
  audit logging, and redaction before persistence.

### Constitution Alignment *(mandatory)*

- **Phase Scope**: This is `PLAN.md` Phase 6 only. It adds authentication,
  authorization, explicit memory, and audit logging. Full chatbot orchestration,
  automatic memory writes, RAG question answering, UI work, widget behavior, and
  unrelated product features are out of scope.
- **Architecture Boundaries**: API routes remain request/response mapping and
  dependency wiring only. Auth, role, invitation, memory, redaction, and audit
  workflows belong in services. Persistence belongs in repositories. Vault,
  Redis, pgvector, token, password, and redaction adapters belong in infra.
- **Security And Redaction**: Passwords, tokens, signing keys, user content,
  memory content, and audit metadata are sensitive. Signing keys resolve from
  Vault at startup. Redaction must run before memory persistence, audit metadata,
  logs, traces, or memory writes can expose user content.
- **Observability And Errors**: Auth failures, authorization failures, memory
  writes, role changes, and audit failures must produce structured logs/errors
  with request identifiers where available and without stack traces or raw
  sensitive payloads.
- **Evidence And Evals**: Memory decisions require `DECISIONS.md` updates for
  short-term TTL, selected long-term memory type, cross-conversation recall
  behavior, and audit action policy. No classifier, RAG, or model evaluation is
  part of this phase.
- **Critical Tests**: Critical tests must cover auth, refresh behavior, Vault key
  resolution, admin guard, admin invitation, Redis short-term memory TTL,
  explicit long-term memory writes, cross-conversation recall, no auto-writes,
  reserved audit action names, audit rows, and redaction before
  persistence/logging.

### Key Entities *(include if feature involves data)*

- **User Account**: Registered user identity with email, password credential
  state, role, timestamps, and active/disabled status.
- **Role**: Authorization category, either regular user or admin.
- **Token Session**: Access and refresh token state associated with a user,
  including expiry, rotation, and revocation status.
- **JWT Signing Key**: Secret signing material resolved from Vault at startup and
  required for token issuance and validation.
- **Admin Invitation**: Admin-created invitation used to grant admin role,
  including inviter, invitee email, status, expiry, and acceptance metadata.
- **Authorization Context**: Authenticated user identity, role, request
  correlation data, and permissions used by guarded capabilities.
- **Short-Term Memory Entry**: User-scoped conversation memory stored with a
  configurable expiry time.
- **Long-Term Memory Entry**: Explicitly written redacted memory with selected
  memory type, owner, content, vector metadata, and source traceability.
- **Memory Type**: Supported long-term memory category: episodic, semantic, or
  procedural.
- **Write Memory Request**: Explicit request to persist long-term memory,
  including actor, target user or scope, memory type, content, and safe metadata.
- **Redaction Result**: Sanitized content plus safe metadata describing what was
  redacted without exposing the original secret-like values.
- **Audit Log Entry**: Immutable record with `id`, `actor_user_id`, `action`,
  `target_type`, `target_id`, `timestamp`, and safe `metadata`.
- **Audit Action Name**: Reserved stable action string used by current and later
  services for memory, role, admin invitation, widget configuration, and
  conversation deletion events.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A new user can complete registration and then log in successfully
  with the registered credentials.
- **SC-002**: Token issuance succeeds only when a startup-resolved signing key is
  available, and fails safely in 100% of tested missing-key cases.
- **SC-003**: Regular users are rejected from admin-only capabilities in 100% of
  admin-guard tests.
- **SC-004**: Admin invitation acceptance grants admin role only for valid,
  unexpired, unused invitations.
- **SC-005**: Short-term memory write/read returns the stored value for the same
  user before expiry and returns no value after the configured TTL.
- **SC-006**: Long-term memory is written only through the explicit write-memory
  capability in 100% of tested flows.
- **SC-007**: Every successful long-term memory write creates exactly one audit
  log row with the required fields.
- **SC-008**: Every tested role change or admin invitation action creates an
  audit log row with the required fields.
- **SC-009**: Fake secret values included in memory input do not appear
  unredacted in persisted memory, audit metadata, logs, or traces.
- **SC-010**: `DECISIONS.md` documents the short-term memory TTL and selected
  long-term memory type before the phase is considered complete.
- **SC-011**: Reserved audit action names are present and tested for memory,
  role, admin invitation, widget config, and conversation deletion workflows.
- **SC-012**: A cross-conversation recall test proves only explicitly written
  same-user long-term memory is recallable.

## Assumptions

- The first admin is created through a controlled local bootstrap or seed path;
  after that, admin access is granted through the admin invitation flow.
- Email verification and password reset are outside this phase unless required
  later; registration and login are sufficient for Phase 6 acceptance.
- Refresh tokens are stored or tracked server-side enough to support expiry,
  revocation, and replay-safe behavior.
- Long-term memory defaults to explicit user-approved writes only; no background
  extraction or chatbot-driven memory persistence is included.
- Audit logs are append-only for application behavior, with corrections handled
  through additional audit entries rather than mutation.
- Widget config and conversation deletion workflows are implemented in later
  phases, but their audit action names and audit service contract are reserved
  in this phase.
