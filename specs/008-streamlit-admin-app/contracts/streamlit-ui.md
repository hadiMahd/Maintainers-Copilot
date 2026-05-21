# Contract: Streamlit Internal UI

## Scope

This contract defines the Phase 8 internal Streamlit UI behavior. The UI is not
the public embedded widget. It calls the same FastAPI backend that the widget
will use and does not access persistence, infra clients, or model clients
directly.

## Global UI Contract

- The app starts from `streamlit_app/app.py`.
- The backend base URL is configured through non-secret environment or Streamlit
  configuration.
- All backend calls go through `streamlit_app/clients/backend_api.py`.
- All backend calls use `httpx` with explicit connect, read, write, and pool
  timeouts.
- Protected calls use the access token from `st.session_state`.
- Auth state is cleared on logout, `401`, refresh failure, or invalid session.
- UI errors are rendered through a shared clean-error component.
- Streamlit code must not import database, repository, ORM, Redis, Vault, MinIO,
  model, RAG, or LLM provider modules.
- Streamlit code must not contain real secrets, hardcoded privileged
  credentials, or admin email allowlists.
- Streamlit code must not log raw chat messages, memory contents, access tokens,
  refresh tokens, embed snippets, or backend stack traces.

## Page Contract: Login

**Path**: login view in `streamlit_app/app.py` or an auth component.

**Behavior**:

- Accept email and password.
- Submit credentials to backend `POST /auth/login`.
- Store issued token state and current user profile in `st.session_state`.
- Navigate to the authenticated chat page after successful login.
- Display clean errors for invalid credentials, backend unavailable, timeout, or
  invalid response schema.

**Backend dependencies**:

- `POST /auth/login`
- `GET /users/me` after login when token response does not include role details.

**Failure behavior**:

- Invalid credentials leave the app unauthenticated.
- Backend timeout shows a retryable service message.
- Raw backend tracebacks are never displayed.

## Page Contract: Chat

**Path**: `streamlit_app/pages/chat.py`

**Behavior**:

- Requires authenticated session state.
- Accepts a user message and conversation identifier.
- Sends chat requests to backend `POST /chat`.
- Displays backend streamed events or equivalent response events in order.
- Displays backend trace/request identifiers only when returned as safe metadata.
- Keeps transient display history in Streamlit session state only.

**Backend dependencies**:

- `POST /chat`

**Failure behavior**:

- `401` clears auth state and prompts for login.
- `413` or context-limit errors show clean request-size guidance.
- Timeout or service-unavailable errors do not hang the UI.
- Chat error events are rendered as safe partial or failure messages.

## Page Contract: Admin Widget Configuration

**Path**: `streamlit_app/pages/admin_widget_config.py`

**Behavior**:

- Requires authenticated session state and backend-provided `admin` role.
- Regular users cannot see admin controls and no admin mutation call is made for
  them.
- Lists, creates, and edits widget configurations only through backend API
  methods.
- Displays validation feedback from backend without raw internals.
- Displays generated embed snippets returned by the backend.

**Backend dependencies**:

- `GET /users/me`
- `GET /admin/widget-configs`
- `POST /admin/widget-configs`
- `PATCH /admin/widget-configs/{config_id}`
- `GET /admin/widget-configs/{config_id}/embed-snippet`

**Failure behavior**:

- `403` shows an access-denied message.
- Validation errors attach to fields when possible.
- Snippet generation failures do not corrupt saved widget configuration state.

## Page Contract: Memory Inspector

**Path**: `streamlit_app/pages/memory_inspector.py`

**Behavior**:

- Requires authenticated session state.
- Reads memory records only through backend memory-inspection endpoints.
- Shows only backend-authorized, backend-redacted fields.
- Supports simple filters when the backend contract supports them.
- Does not store returned memory records outside transient Streamlit state.

**Backend dependencies**:

- `GET /memory/long-term`
- Optional admin-supported memory endpoints if provided by backend contract.

**Failure behavior**:

- `401` clears auth state and prompts for login.
- `403` shows a clean access-denied message.
- Timeout or backend unavailable errors are bounded and retryable.

## Backend API Client Contract

The backend client provides narrow typed methods:

- `login(email, password) -> AuthSession`
- `get_current_user() -> CurrentUserView`
- `chat(conversation_id, message) -> Iterable[ChatEventView]`
- `list_widget_configs() -> list[WidgetConfigurationView]`
- `save_widget_config(config) -> WidgetConfigurationView`
- `get_embed_snippet(config_id) -> EmbedSnippetView`
- `inspect_memory(query) -> list[MemoryRecordView]`

The client maps backend failures into `UIErrorMessage`:

- Authentication failures: `authentication_required` or `invalid_credentials`
- Authorization failures: `access_denied`
- Validation failures: `validation_error`
- Request-size failures: `request_too_large`
- Timeouts: `backend_timeout`
- Unavailable backend: `backend_unavailable`
- Unknown schema or unexpected failures: `backend_error`

## Test Contract

Tests must prove:

- Login calls backend auth and populates session state.
- Chat calls backend chat and renders response or stream events.
- Regular users cannot access admin UI and do not trigger admin mutation calls.
- Admin widget config create/edit calls the backend client.
- Embed snippet is displayed exactly as backend returns it.
- Memory inspector shows backend-authorized records and handles `403`.
- Timeout and backend-unavailable errors render clean messages.
- A `401` response clears auth state.
- Static checks find no direct DB, Redis, Vault, repository, ORM, model, RAG, or
  provider imports from `streamlit_app/`.
- Static checks find no hardcoded secret-like values or privileged credentials
  in `streamlit_app/`.
