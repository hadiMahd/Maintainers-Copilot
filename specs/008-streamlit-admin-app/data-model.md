# Data Model: Streamlit Internal Chatbot and Admin App

## Streamlit Session State

**Purpose**: Browser-session scoped state for authentication and page UI.

**Fields**:

- `is_authenticated`: boolean indicating whether the current session has valid
  backend auth state.
- `access_token`: short-lived bearer token used only by the backend API client.
- `refresh_token`: refresh token if the backend issues one and the UI supports
  refresh.
- `current_user`: safe user profile returned by the backend.
- `role`: current role from backend user profile, such as `user` or `admin`.
- `active_page`: selected Streamlit page.
- `conversation_id`: current chat conversation identifier.
- `ui_notices`: transient safe user-facing notices.

**Validation rules**:

- Token fields are cleared on logout, invalid credentials, `401`, refresh
  failure, or explicit session reset.
- Tokens are never printed, logged, displayed, or placed in URLs.
- Role state is advisory for UI visibility; backend authorization remains
  authoritative.

## Backend API Client Settings

**Purpose**: Non-secret configuration for the UI HTTP client.

**Fields**:

- `base_url`: FastAPI backend base URL.
- `connect_timeout_seconds`: bounded connect timeout.
- `read_timeout_seconds`: bounded read timeout.
- `write_timeout_seconds`: bounded write timeout.
- `pool_timeout_seconds`: bounded connection pool timeout.

**Validation rules**:

- `base_url` is required and is treated as non-secret configuration.
- Timeout values must be positive and finite.
- Missing or invalid configuration produces a clean startup/configuration
  message without printing secrets.

## Backend API Client

**Purpose**: The only Streamlit-side data access path.

**Fields**:

- `settings`: backend API client settings.
- `access_token_provider`: callable or state lookup for current access token.
- `on_auth_invalid`: callback that clears Streamlit auth state.

**Relationships**:

- Reads token state from Streamlit session state.
- Calls backend auth, users, chat, widget config, snippet, and memory endpoints.

**Validation rules**:

- Every request uses explicit `httpx.Timeout`.
- Protected requests include `Authorization: Bearer <token>`.
- `401` responses clear auth state and return a clean UI error.
- Client methods return typed view models or typed UI errors.

## Current User View

**Purpose**: Safe user identity and role information for UI display and gating.

**Fields**:

- `id`: backend user identifier.
- `email`: user email.
- `role`: `user` or `admin`.
- `is_active`: backend account status.

**Validation rules**:

- Missing or unknown role is treated as non-admin.
- Admin-only UI is hidden unless `role` is `admin`.

## Login Form State

**Purpose**: User-entered credentials submitted to the backend.

**Fields**:

- `email`: login email.
- `password`: login password.

**Validation rules**:

- Empty email or password is rejected before the backend call with a clean form
  error.
- Password is not persisted beyond the login submission.
- Invalid credentials do not create authenticated session state.

## Chat Page State

**Purpose**: UI state for authenticated chat through the backend.

**Fields**:

- `conversation_id`: active conversation identifier.
- `message_draft`: current unsent message.
- `displayed_messages`: safe display history for the current UI session.
- `pending`: whether a backend chat request is active.
- `last_trace_id`: trace identifier returned by backend when available.

**Validation rules**:

- Empty messages are not sent.
- Message content is sent only to backend chat endpoints.
- Chat errors render as clean UI errors and do not expose stack traces.

## Chat Event View

**Purpose**: UI representation of backend chat stream or response events.

**Fields**:

- `event_type`: `message_delta`, `tool_status`, `warning`, `error`, or `done`.
- `content`: safe display content when present.
- `sequence`: event order.
- `trace_id`: backend trace identifier when present.
- `error`: structured UI error when present.

**Validation rules**:

- Events are displayed in sequence.
- Error events do not include raw backend traces or tokens.

## Widget Configuration View

**Purpose**: Admin-editable widget settings submitted to the backend.

**Fields**:

- `id`: widget configuration identifier.
- `name`: admin-visible configuration name.
- `allowed_origins`: allowed host origins for the future widget.
- `theme`: display theme option if supported by backend contract.
- `welcome_message`: optional initial widget message.
- `is_enabled`: whether the configuration can be used.
- `updated_at`: backend update timestamp.

**Validation rules**:

- Only admins can view or submit this form.
- Validation failures from backend are shown as clean field-level or general
  errors.
- Streamlit does not persist widget configuration directly.

## Widget Configuration

**Purpose**: Backend-owned widget configuration persisted for the internal admin
UI and future widget delivery.

**Fields**:

- `id`: widget configuration identifier.
- `name`: admin-visible unique name.
- `allowed_origins`: allowed host origins.
- `theme`: backend-supported theme option.
- `welcome_message`: optional first message for the widget.
- `is_enabled`: whether the config is active.
- `created_by_user_id`: admin user who created the config.
- `updated_by_user_id`: admin user who last updated the config.
- `created_at`: creation timestamp.
- `updated_at`: update timestamp.

**Validation rules**:

- Create and update operations require an admin user.
- `allowed_origins` must contain valid origins, not wildcard-all production
  defaults.
- Backend service validates fields before repository writes.
- Repositories do not commit independently; services own transactions.
- Streamlit never writes this entity outside the backend API.

## Embed Snippet View

**Purpose**: Copyable snippet returned by the backend for a widget configuration.

**Fields**:

- `widget_config_id`: related widget configuration identifier.
- `snippet`: generated embed snippet text.
- `generated_at`: backend generation timestamp when available.

**Validation rules**:

- Snippet text is displayed in a code block or copyable text area without
  mutation.
- Snippet content is not logged.
- Streamlit does not invent widget URLs or secret-like values.

## Memory Inspector Query

**Purpose**: UI filters for backend-authorized memory inspection.

**Fields**:

- `scope`: user or admin-supported scope from backend contract.
- `memory_type`: optional filter such as `semantic`.
- `search_text`: optional search term.
- `limit`: maximum number of records requested.

**Validation rules**:

- Regular users can request only user-allowed scopes.
- Backend authorization failures render as clean access errors.
- Search text and returned memory content are not logged.

## Memory Record View

**Purpose**: Safe memory record returned by backend for display.

**Fields**:

- `id`: memory identifier.
- `owner_user_id`: owner identifier when allowed by backend.
- `memory_type`: memory type.
- `redacted_content`: backend-redacted display content.
- `source`: safe source label.
- `created_at`: timestamp.

**Validation rules**:

- Only backend-returned, backend-authorized fields are displayed.
- Raw unredacted memory content is never reconstructed or stored in Streamlit.

## Memory Inspection Result

**Purpose**: Backend response for listing authorized long-term memory records.

**Fields**:

- `items`: list of `Memory Record View` objects.
- `next_cursor`: optional cursor for pagination.
- `scope`: resolved backend authorization scope.

**Validation rules**:

- Regular users can inspect only their own allowed records.
- Admins can inspect only scopes explicitly allowed by backend authorization.
- Records contain redacted content only.
- Query metadata and response payloads are not logged raw.

## UI Error Message

**Purpose**: Clean error state shown to users.

**Fields**:

- `code`: stable local or backend error code.
- `message`: user-facing message.
- `retryable`: whether retry is appropriate.
- `request_id`: backend request identifier when safe.
- `trace_id`: backend trace identifier when safe.

**Validation rules**:

- Stack traces, tokens, raw chat payloads, memory payloads, snippets, and secret
  values are never included.
- Timeout and service-unavailable errors are distinct from validation and
  authorization errors.

## State Transitions

```text
Unauthenticated -> Login Submitted -> Authenticated
Login Submitted -> Login Error -> Unauthenticated
Authenticated -> Logout -> Unauthenticated
Authenticated -> Backend 401 -> Unauthenticated

Authenticated User -> Chat Request Pending -> Chat Response Displayed
Chat Request Pending -> Chat Error Displayed -> Authenticated User

Authenticated Admin -> Widget Form Submitted -> Widget Config Saved
Widget Form Submitted -> Validation Error Displayed -> Authenticated Admin

Authenticated User/Admin -> Memory Query Submitted -> Memory Records Displayed
Memory Query Submitted -> Access Error Displayed -> Authenticated User/Admin
```
