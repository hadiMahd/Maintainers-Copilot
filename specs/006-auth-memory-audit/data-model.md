# Data Model: Authentication, Memory, and Audit Logging

## User Account

**Purpose**: Registered identity allowed to authenticate and own memory.

**Fields**:
- `id`: stable user identifier.
- `email`: normalized unique email address.
- `hashed_password`: password credential hash.
- `role`: `user` or `admin`.
- `is_active`: whether the account can authenticate.
- `is_verified`: whether email/account verification is complete when enabled.
- `created_at`: creation timestamp.
- `updated_at`: last update timestamp.

**Validation Rules**:
- Email must be normalized and unique.
- Raw passwords are never persisted.
- New self-registered accounts default to `user`.
- Role changes require admin authorization and audit logging.

## Token Session

**Purpose**: Refresh token session state for login, refresh, revocation, and
replay protection.

**Fields**:
- `id`: token session identifier.
- `user_id`: owner user.
- `refresh_token_hash`: hash of the current refresh token.
- `issued_at`: issue timestamp.
- `expires_at`: expiry timestamp.
- `rotated_at`: timestamp of last rotation when applicable.
- `revoked_at`: revocation timestamp when applicable.
- `reuse_detected_at`: timestamp when replay is detected.
- `user_agent_hash`: optional bounded client metadata.
- `ip_hash`: optional bounded client metadata.

**Validation Rules**:
- Refresh tokens are stored hashed, not raw.
- Expired, revoked, malformed, or replayed refresh tokens are rejected.
- Refresh rotation updates the session atomically.

## JWT Signing Key

**Purpose**: Startup-resolved secret required to issue and validate JWT access
tokens.

**Fields**:
- `key_id`: safe key identifier.
- `algorithm`: signing algorithm.
- `resolved_at`: startup resolution timestamp.
- `source`: safe source label, such as Vault or test fake.

**Validation Rules**:
- Secret material is never stored in database rows, logs, traces, or docs.
- Token issuance is disabled when the key is unavailable or invalid.

## Admin Invitation

**Purpose**: Admin-created invitation for granting admin role.

**Fields**:
- `id`: invitation identifier.
- `invitee_email`: normalized invitee email.
- `created_by_user_id`: admin who created the invitation.
- `token_hash`: hash of invitation token.
- `status`: `pending`, `accepted`, `revoked`, or `expired`.
- `created_at`: creation timestamp.
- `expires_at`: expiry timestamp.
- `accepted_at`: acceptance timestamp when accepted.
- `accepted_by_user_id`: user who accepted the invitation when applicable.

**Validation Rules**:
- Only admins can create invitations.
- Invitation tokens are stored hashed, not raw.
- Expired, revoked, malformed, or already accepted invitations cannot grant role.
- Creation and acceptance are audited.

## Authorization Context

**Purpose**: Request-scoped identity and role information used by authorization
dependencies.

**Fields**:
- `user_id`: authenticated user identifier.
- `email`: authenticated user email.
- `role`: current role.
- `request_id`: request correlation identifier when available.
- `trace_id`: trace correlation identifier when available.

**Validation Rules**:
- Context requires a valid authenticated user.
- Admin-only dependencies must check current role, not only token claims.

## Short-Term Memory Entry

**Purpose**: Temporary user-scoped conversation context.

**Fields**:
- `user_id`: memory owner.
- `conversation_id`: conversation or session identifier.
- `key`: memory key.
- `redacted_value`: redacted memory value.
- `ttl_seconds`: configured TTL at write time.
- `created_at`: write timestamp.
- `expires_at`: expected expiry timestamp.

**Validation Rules**:
- Stored value must be redacted before persistence.
- TTL must be configured, positive, and documented in `docs/decisions.md`.
- Reads after expiry return no value.
- Users cannot read another user's short-term memory.

## Long-Term Memory Entry

**Purpose**: Explicit durable memory persisted for future retrieval.

**Fields**:
- `id`: memory identifier.
- `owner_user_id`: memory owner.
- `memory_type`: selected type, `semantic` for Phase 6 unless changed in
  `docs/decisions.md`.
- `redacted_content`: redacted memory content.
- `content_hash`: hash of redacted content.
- `embedding`: pgvector embedding.
- `source`: safe source label, such as `write_memory`.
- `created_by_user_id`: actor who requested the write.
- `created_at`: creation timestamp.
- `metadata`: safe bounded metadata.

**Validation Rules**:
- Memory writes must be explicit.
- No normal request may auto-create long-term memory.
- Content is redacted before embedding or persistence.
- Memory type must be one of `episodic`, `semantic`, or `procedural`.
- Successful writes require an audit log row in the same transaction.

## Write Memory Request

**Purpose**: Explicit request to create long-term memory.

**Fields**:
- `content`: memory content submitted by the actor.
- `memory_type`: requested memory type.
- `target_user_id`: memory owner, defaults to actor where allowed.
- `metadata`: optional safe bounded metadata.

**Validation Rules**:
- Content must be non-empty after redaction.
- Requested memory type must match the selected supported type for this phase.
- Requests must be authenticated.
- Redaction failures prevent persistence.

## Long-Term Memory Recall Query

**Purpose**: Explicit request to search a user's previously written long-term
memory across conversations.

**Fields**:
- `query`: recall prompt or search text.
- `conversation_id`: optional current conversation identifier for auditability.
- `limit`: optional bounded maximum number of recall hits.

**Validation Rules**:
- Requests must be authenticated.
- Recall is scoped to the requesting user's explicitly written long-term memory.
- Query text must be non-empty.
- Returned entries must not expose another user's memory.

## Redaction Result

**Purpose**: Output of redaction before persistence or telemetry.

**Fields**:
- `redacted_text`: sanitized content safe for memory storage.
- `redaction_count`: number of replacements.
- `redaction_types`: safe labels for detected sensitive patterns.
- `safe_metadata`: bounded metadata safe for audit/logging.

**Validation Rules**:
- Original secret-like values are never returned in metadata.
- Redaction runs before Redis, PostgreSQL, audit, logs, or traces.

## Audit Log Entry

**Purpose**: Immutable security and memory audit record.

**Fields**:
- `id`: audit identifier.
- `actor_user_id`: user who caused the action.
- `action`: stable action name.
- `target_type`: target entity type.
- `target_id`: target entity identifier.
- `timestamp`: action timestamp.
- `metadata`: safe bounded JSON metadata.

**Validation Rules**:
- Required fields are present for every audit row.
- `action` must be one of the reserved project action names for audited
  workflows: `memory.write`, `role.change`, `admin_invitation.create`,
  `widget_config.create`, `widget_config.update`, `widget_config.delete`, or
  `conversation.delete`.
- Metadata does not include raw memory content, passwords, tokens, signing keys,
  invitation tokens, or unredacted secrets.
- Memory write, role/admin invitation, widget config, and conversation deletion
  workflows create audit rows atomically with the state change when those
  workflows are implemented.

## Cross-Conversation Recall Check

**Purpose**: Demo/test record proving explicit long-term memory can be recalled
across conversations for the same user only.

**Fields**:
- `owner_user_id`: memory owner.
- `source_conversation_id`: conversation where explicit memory was written.
- `recall_conversation_id`: later conversation where recall was tested.
- `memory_id`: recalled long-term memory entry.
- `matched_content_hash`: hash of redacted recalled content.
- `authorized`: whether recall was allowed for the requester.
- `created_at`: check timestamp.

**Validation Rules**:
- Recall is allowed only for explicitly written long-term memory.
- Recall is scoped to the memory owner unless an explicit admin policy is added
  later.
- The check stores hashes and safe metadata, not raw memory content.

## Memory Decision Record

**Purpose**: `docs/decisions.md` section documenting memory choices.

**Fields**:
- `short_term_ttl_seconds`: selected Redis TTL and rationale.
- `long_term_memory_type`: selected type and rationale.
- `redaction_policy`: redaction-before-persistence summary.
- `audit_policy`: audited actions and limitations.
- `cross_conversation_recall_policy`: same-user explicit-memory recall behavior.
- `alternatives_considered`: rejected TTL/type/policy alternatives.

**Validation Rules**:
- Must be updated before Phase 6 is considered complete.
- Must defend the selected long-term memory type.
- Must mention no automatic long-term memory writes.
- Must list reserved audit actions for memory, role, admin invitation, widget
  config, and conversation deletion workflows.
