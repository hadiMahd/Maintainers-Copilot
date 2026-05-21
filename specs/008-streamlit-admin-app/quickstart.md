# Quickstart: Streamlit Internal Chatbot and Admin App

## Prerequisites

- Phase 6 auth, authorization, and memory endpoints are implemented or available
  as compatible backend fakes.
- Phase 7 authenticated chat endpoint is implemented or available as a
  compatible backend fake.
- Phase 8 backend support for widget configuration and memory inspection is
  implemented or represented by a contract-compatible fake for UI tests.
- Backend base URL is configured as non-secret local configuration, such as
  `MAINTAINER_COPILOT_API_BASE_URL=http://localhost:8000`.

## Run The Internal UI

Start the FastAPI backend, then run:

```bash
streamlit run streamlit_app/app.py
```

Expected result: the Streamlit app opens to the login page and does not attempt
database, Redis, Vault, model, or direct persistence connections.

## Verify Backend Support

Call the internal UI backend support endpoints as an admin:

- `GET /admin/widget-configs`
- `POST /admin/widget-configs`
- `PATCH /admin/widget-configs/{config_id}`
- `GET /admin/widget-configs/{config_id}/embed-snippet`
- `GET /memory/long-term`

Expected result: widget configuration and snippet operations require admin role,
regular users receive clean access errors, and memory inspection returns only
backend-authorized redacted records.

## Verify Login

Log in with a regular backend user.

Expected result: the app calls backend auth, stores the auth token in a browser
cookie via `streamlit-cookies-manager`, keeps only safe non-secret profile/role
UI state in `st.session_state`, loads the current user profile, and navigates
to an authenticated page.

Invalid credentials should show a clean login error and leave the session
unauthenticated.

## Verify Chat

Open the chat page and send a short maintainer question.

Expected result: the app sends the message to `POST /chat`, renders the SSE
response with `st.write_stream()` from an `httpx` generator adapter, does not
buffer the full chat response before display, and shows a clean error if the
backend times out or rejects the request. REST calls use a 30-second timeout;
the SSE chat stream uses a 70-second timeout.

## Verify Admin Widget Configuration

Log in as an admin user and open the widget configuration page.

Expected result: the app lists, creates, or edits widget configurations through
backend API calls and displays the backend-generated embed snippet.

Log in as a regular user and attempt to open the admin page.

Expected result: programmatic `st.navigation()` excludes admin pages from the
regular-user page list, the admin UI is hidden or denied, and no admin mutation
request is sent.

## Verify Memory Inspector

Open the memory inspector as a regular user and as an admin.

Expected result: both roles see only memory records returned by backend
authorization. Backend `403` responses render a clean access message.

## Run Tests

```bash
uv run pytest tests/unit/test_streamlit_backend_client.py
uv run pytest tests/unit/test_widget_config_service.py
uv run pytest tests/unit/test_memory_inspector_service.py
uv run pytest tests/unit/test_streamlit_session_auth.py
uv run pytest tests/unit/test_streamlit_admin_guard.py
uv run pytest tests/unit/test_streamlit_error_display.py
uv run pytest tests/unit/test_streamlit_no_direct_db_or_secrets.py
uv run pytest tests/contract/test_internal_ui_backend_contract.py
uv run pytest tests/contract/test_streamlit_backend_contract.py
uv run pytest tests/integration/test_streamlit_backend_flow.py
```

Expected result: tests use `streamlit.testing.v1.AppTest` with mocked backend
API calls and prove backend-only data access, cookie-backed token handling,
`st.navigation()` admin guard behavior, `st.write_stream()` chat rendering,
memory authorization handling, snippet display, timeout handling, clean errors,
and absence of direct persistence or secret usage in Streamlit code.

## Static Review Checks

Use source search during review:

```bash
rg -n "sqlalchemy|asyncpg|psycopg|redis|vault|boto3|minio|Repository|Session" streamlit_app
rg -n "password\\s*=|token\\s*=|secret\\s*=|api[_-]?key\\s*=|BEGIN PRIVATE KEY" streamlit_app
```

Expected result: no direct persistence, infra-client, provider-client, or
hardcoded secret usage appears in Streamlit code.
