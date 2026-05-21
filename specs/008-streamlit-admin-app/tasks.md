# Tasks: Streamlit Internal Chatbot and Admin App

**Input**: Design documents from `/specs/008-streamlit-admin-app/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Tests are REQUIRED per spec.md FR-018. All tests use `streamlit.testing.v1.AppTest` with mocked backend API calls. Backend service/contract tests use pytest.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Streamlit project initialization and basic package structure.

- [X] T001 Create streamlit_app/ directory structure: app.py, config.py, models.py, clients/, components/, pages/ with __init__.py files
- [X] T002 Add streamlit and streamlit-cookies-manager dependencies to pyproject.toml
- [X] T003 [P] Create streamlit_app/config.py with typed StreamlitSettings (base_url: str, rest_timeout_seconds: int, sse_timeout_seconds: int, connect_timeout_seconds: int, read_timeout_seconds: int) loaded from env vars prefixed MAINTAINER_COPILOT_UI_; validate base_url is non-empty at startup and raise a clear StreamlitSettingsError with actionable message if missing or invalid
- [X] T004 [P] Create streamlit_app/models.py with UI/client models: CurrentUserView, LoginCredentials, ChatMessage, ChatEventView, WidgetConfigView, WidgetConfigForm, EmbedSnippetView, MemoryInspectionQuery, MemoryRecordView, MemoryInspectionResult, UIErrorMessage

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Backend endpoint support for missing widget-config and memory-inspection operations, plus Streamlit API client, shared components, and app entry point. All user stories depend on this phase.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

### Backend Domain Models

- [X] T005 [P] Create app/domain/widget_config.py with WidgetConfigCreate, WidgetConfigUpdate, WidgetConfigRead, EmbedSnippetRead Pydantic schemas per contracts/internal-ui-backend.openapi.yaml
- [X] T006 [P] Create app/domain/memory_inspector.py with MemoryInspectionQuery, MemoryRecordRead, MemoryInspectionResult Pydantic schemas per contracts/internal-ui-backend.openapi.yaml

### Backend Repositories

- [X] T007 [P] Create app/repositories/widget_config_repository.py with SQLAlchemy async CRUD for widget_configs table (list_all, get_by_id, create, update) — no commit/rollback
- [X] T008 [P] Create app/repositories/memory_inspector_repository.py with list_by_user (paginated listing filtered by owner_user_id, memory_type, cursor/limit) and list_all (admin-only unfiltered listing) — queries are distinct from existing MemoryRepository semantic-search methods; this repo adds inspection-specific list/filter/paginate operations only — no commit/rollback

### Backend Services

- [X] T009 Create app/services/widget_config_service.py (create/edit/list/get configs, generate embed snippet as placeholder string referencing widget_config_id for now — Phase 9 will replace with actual embed <script> generation, admin-only gating, field validation, transactional commit/rollback) — depends on T005, T007
- [X] T010 Create app/services/memory_inspector_service.py (authorized listing with user-scope vs admin-scope gating, pagination, redacted-content-only responses) — depends on T006, T008

### Backend Routes

- [X] T011 Create app/api/routes/widget_configs.py with thin routes (GET /, POST /, PATCH /{config_id}, GET /{config_id}/embed-snippet) using require_admin dependency per contracts/internal-ui-backend.openapi.yaml — depends on T009
- [X] T012 Create app/api/routes/memory_inspector.py with thin route (GET /long-term with query params: owner_user_id, memory_type, limit, cursor) using get_current_user dependency per contracts/internal-ui-backend.openapi.yaml — depends on T010
- [X] T013 Wire new routes into app/api/routes/__init__.py (include widget_configs_router under prefix="/admin/widget-configs", include memory_inspector_router under prefix="/memory" alongside existing memory_router — note: two routers share the /memory prefix; memory.py owns POST /long-term and POST /long-term/recall; memory_inspector.py owns GET /long-term; document the split with a comment in __init__.py) — depends on T011, T012

### Backend Config and ORM

- [X] T014 Add widget_configs SQLAlchemy ORM model to app/infra/orm_models.py (table: widget_configs, columns: id, name, allowed_origins JSON, theme, welcome_message, is_enabled, created_by_user_id, updated_by_user_id, created_at, updated_at); generate migration with `alembic revision --autogenerate -m "add widget_configs table"`; review the generated migration file; apply with `alembic upgrade head` via Docker Compose — depends on T007

### Streamlit Backend API Client

- [X] T015 Implement streamlit_app/clients/backend_api.py: BackendAPIClient class with typed httpx client (login, get_current_user, chat_stream SSE generator via httpx.stream, list_widget_configs, create_widget_config, update_widget_config, get_embed_snippet, inspect_memory); all calls use explicit httpx.Timeout from StreamlitSettings (30s REST, 70s SSE); Authorization header from token provider; 401 triggers on_auth_invalid callback; all errors mapped to UIErrorMessage — depends on T003, T004

### Streamlit Shared Components

- [X] T016 [P] Create streamlit_app/components/auth.py: login_form(email, password, client) that calls backend login, stores token in cookie via streamlit-cookies-manager, populates st.session_state with non-secret user/role state; restore_session() that reads token from cookie on page refresh; logout() that clears cookie and st.session_state
- [X] T017 [P] Create streamlit_app/components/errors.py: display_error(error: UIErrorMessage) rendering with appropriate st.error/st.warning severity per error code; backend_timeout → retryable warning; authentication_required → redirect to login
- [X] T018 [P] Create streamlit_app/components/snippets.py: display_embed_snippet(snippet: EmbedSnippetView) rendering snippet in copyable st.code block

### Streamlit App Entry Point

- [X] T019 Create streamlit_app/app.py: entry point with st.navigation() building runtime page list from role (authenticated pages: chat, memory_inspector; admin-only pages: admin_widget_config added only when role=="admin"); cookie restore on startup; unauthenticated → login page; authenticated → chat default page — depends on T015, T016, T017

**Checkpoint**: Foundation ready — all backend endpoints (widget configs + memory inspection) are functional, Streamlit client can call them, and the app shell with auth cookie, navigation guard, and shared components is wired. User story implementation can now begin.

---

## Phase 3: User Story 1 - Log In And Chat Internally (Priority: P1)

**Goal**: An authenticated user can log in through the Streamlit app and use the full chatbot through `POST /chat` SSE streaming.

**Independent Test**: Log in through the Streamlit UI, send a chat message, verify the message and response flow through backend API calls (mocked in tests).

### Tests for User Story 1

- [X] T020 [P] [US1] Contract test: verify login POST /auth/login and GET /users/me response shapes in tests/contract/test_streamlit_backend_contract.py (mocked httpx transport)
- [X] T021 [P] [US1] Unit test: verify BackendAPIClient.login() and .chat_stream() methods in tests/unit/test_streamlit_backend_client.py (mocked httpx transport)
- [X] T022 [P] [US1] Unit test: verify Streamlit login/logout cookie lifecycle (store, restore on refresh, clear on logout, clear on 401) in tests/unit/test_streamlit_session_auth.py (AppTest with mocked backend)
- [X] T023 [P] [US1] Unit test: verify chat page renders SSE stream events via st.write_stream() without full-response buffering in tests/unit/test_streamlit_chat_streaming.py (AppTest with mocked SSE generator)

### Implementation for User Story 1

- [X] T024 [US1] Implement login page in streamlit_app/app.py (unauthenticated view: email/password form → client.login() → cookie store → st.rerun)
- [X] T025 [US1] Create streamlit_app/pages/chat.py: message input, conversation display using st.chat_message, SSE streaming via st.write_stream(BackendAPIClient.chat_stream(...)), event-type rendering (message_delta, tool_status, error, done), pending/error/empty states, trace_id display when present — depends on T015, T017, T019
- [X] T026 [US1] Wire cookie-backed session restore in streamlit_app/app.py: read token from cookie on each page load, validate via GET /users/me, clear and redirect to login on invalid/missing token

**Checkpoint**: User Story 1 is fully functional — login with cookie persistence across page refreshes, SSE chat streaming with clean error handling. Independently testable.

---

## Phase 4: User Story 2 - Manage Widget Configuration As Admin (Priority: P2)

**Goal**: An admin can create, edit, list widget configurations and view generated embed snippets through backend API calls. Regular users are blocked by `st.navigation()` role exclusion.

**Independent Test**: Log in as admin, create/edit a widget configuration, verify embed snippet display and that regular users cannot access admin UI.

### Tests for User Story 2

- [X] T027 [P] [US2] Contract test: verify widget config CRUD endpoints (GET/POST/PATCH /admin/widget-configs, GET embed-snippet) response shapes in tests/contract/test_internal_ui_backend_contract.py (mock transport or test client)
- [X] T028 [P] [US2] Unit test: verify WidgetConfigService CRUD and admin gating in tests/unit/test_widget_config_service.py
- [X] T029 [P] [US2] Unit test: verify admin widget config page calls BackendAPIClient methods with correct auth in tests/unit/test_streamlit_admin_guard.py (AppTest)
- [X] T030 [P] [US2] Unit test: verify st.navigation() excludes admin_widget_config page for regular users and no admin API calls are made for non-admin sessions in tests/unit/test_streamlit_admin_guard.py (AppTest)
- [X] T031 [P] [US2] Unit test: verify embed snippet renders in copyable code block and is not mutated in tests/unit/test_streamlit_chat_streaming.py (AppTest)

### Implementation for User Story 2

- [X] T032 [US2] Create streamlit_app/pages/admin_widget_config.py: list widget configs table, create/edit form (name, allowed_origins, theme, welcome_message, is_enabled), call BackendAPIClient methods, display backend validation errors via display_error(), delete stub (backend not required by contract) — depends on T015, T017, T019
- [X] T033 [US2] Wire embed snippet display: after create or on config selection, call client.get_embed_snippet(config_id) and render via display_embed_snippet() in streamlit_app/pages/admin_widget_config.py — depends on T018, T032
- [X] T034 [US2] Verify admin guard in streamlit_app/app.py: st.navigation() builds admin_widget_config page entry only when st.session_state.role == "admin"; regular users never see it

**Checkpoint**: Admin widget configuration management works end-to-end with proper role gating. Independently testable alongside US1.

---

## Phase 5: User Story 3 - Inspect Allowed Memory (Priority: P3)

**Goal**: Users and admins can inspect long-term memory records through backend-authorized views. Each role sees only records allowed by backend authorization.

**Independent Test**: Log in as regular user and admin, inspect memory, verify each role sees only backend-authorized records.

### Tests for User Story 3

- [X] T035 [P] [US3] Unit test: verify MemoryInspectorService authorization (user sees own records, admin sees all allowed) in tests/unit/test_memory_inspector_service.py
- [X] T036 [P] [US3] Contract test: verify GET /memory/long-term response shape, 401/403 error codes in tests/contract/test_internal_ui_backend_contract.py (mock transport or test client)

### Implementation for User Story 3

- [X] T037 [US3] Create streamlit_app/pages/memory_inspector.py: filter form (memory_type dropdown, search_text, limit), paginated memory records table, call BackendAPIClient.inspect_memory(), display records with redacted_content/source/created_at, handle 403 with clean access-denied message, handle empty results — depends on T015, T017, T019
- [X] T038 [US3] Verify memory inspector authorization: admin sees all users' records (owner_user_id column shown), regular user sees only own records — confirm backend scope gating is enforced

**Checkpoint**: Memory inspector works for both roles with proper authorization boundaries. Independently testable alongside US1 and US2.

---

## Phase 6: User Story 4 - Use A Safe Backend API Client (Priority: P4)

**Goal**: Verify all backend calls use explicit timeouts from typed settings, handle errors cleanly, and Streamlit code contains no direct DB access or hardcoded secrets.

**Independent Test**: Review Streamlit code and run tests to verify backend-only data access with timeouts and no direct DB/secret usage.

### Tests for User Story 4

- [X] T039 [P] [US4] Unit test: verify all BackendAPIClient methods pass explicit httpx.Timeout with correct values from StreamlitSettings (30s REST, 70s SSE) in tests/unit/test_streamlit_backend_client.py
- [X] T040 [P] [US4] Unit test: verify clean error display for each error category (timeout, auth failure, validation, backend unavailable, unknown) in tests/unit/test_streamlit_error_display.py (AppTest with mocked backend responses)
- [X] T041 [P] [US4] Static check test: verify no sqlalchemy, asyncpg, psycopg, redis, hvac, minio, Repository, Session imports from streamlit_app/ in tests/unit/test_streamlit_no_direct_db_or_secrets.py
- [X] T042 [P] [US4] Static check test: verify no hardcoded secrets (password=, token=, secret=, api_key=, PRIVATE KEY) in streamlit_app/ in tests/unit/test_streamlit_no_direct_db_or_secrets.py
- [ ] T043 [P] [US4] Integration test: full login → chat → widget config → memory inspector flow with mocked backend in tests/integration/test_streamlit_backend_flow.py (AppTest)

### Implementation for User Story 4

- [X] T044 [US4] Audit streamlit_app/ for redaction compliance: ensure no raw chat messages, memory contents, tokens, embed snippets, or backend error traces are logged via st.write or Python logging
- [X] T045 [US4] Audit streamlit_app/ for architecture boundary compliance: confirm no direct imports of app/repositories/, app/infra/orm_models, app/infra/database, app/infra/redis, app/infra/vault, app/infra/minio, app/infra/llm_adapter, or model_server/

**Checkpoint**: All safety properties verified — timeouts enforced, errors clean, no direct DB access, no secrets. Full integration flow works.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Documentation updates, ignore files, quickstart validation, full regression.

- [ ] T046 [P] Update docs/architecture.md with streamlit_app/ layer description and Phase 8 backend additions
- [ ] T047 [P] Update docs/decisions.md with Phase 8 Streamlit decisions (cookie-backed auth, st.navigation admin guard, SSE streaming, httpx timeouts)
- [ ] T048 [P] Update docs/security.md with Streamlit security boundaries (no direct DB, no secrets, cookie token lifecycle, redaction rules)
- [ ] T049 [P] Update docs/runbook.md with Streamlit startup commands and troubleshooting (backend URL config, cookie clearing, admin guard behavior)
- [ ] T050 [P] Update .gitignore and .dockerignore with streamlit_app/ patterns (streamlit secrets, cache, node_modules from widget)
- [ ] T051 Validate quickstart.md: run each command (streamlit run, backend endpoint curl, login test, chat test, admin guard test, memory inspector test, static checks)
- [ ] T052 Run full test suite regression (pytest, ruff, mypy) and fix any failures

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories
- **US1 Login & Chat (Phase 3)**: Depends on Foundational — uses existing backend auth/chat endpoints + new Streamlit client/components
- **US2 Widget Config (Phase 4)**: Depends on Foundational — uses new backend widget-config endpoints + Streamlit client
- **US3 Memory Inspector (Phase 5)**: Depends on Foundational — uses new backend memory-inspection endpoint + Streamlit client
- **US4 Safe Client (Phase 6)**: Depends on US1, US2, US3 completion — verifies cross-cutting safety
- **Polish (Phase 7)**: Depends on all user stories complete

### User Story Dependencies

- **US1 (P1)**: Can start after Foundational — no dependencies on US2 or US3. Uses existing backend auth/chat endpoints.
- **US2 (P2)**: Can start after Foundational — depends on new backend widget-config routes (T005–T013). Independent of US1 and US3.
- **US3 (P3)**: Can start after Foundational — depends on new backend memory-inspection route (T005–T013). Independent of US1 and US2.
- **US4 (P4)**: Must run after US1+US2+US3 — verifies safety across all completed stories.

### Within Each User Story

- Tests MUST be written and FAIL before implementation tasks
- Backend domain → repository → service → route (within Foundational)
- Streamlit client → components → pages → app integration
- Story complete before moving to next priority

### Parallel Opportunities

- T003, T004 can run in parallel (different files)
- T005, T006 can run in parallel (different domain files)
- T007, T008 can run in parallel (different repository files)
- T016, T017, T018 can run in parallel (different component files)
- Backend foundational (T005–T014) and Streamlit foundational (T015–T019) are partially parallelizable — backend routes (T011, T012) depend on services, but Streamlit client (T015) only needs config/models
- Within Phase 2 Streamlit: T015 is sequential, then T016/T017/T018 parallel, then T019
- Once Foundational is complete, US1, US2, US3 can be developed in parallel (if team capacity allows)
- All tests within a user story marked [P] can run in parallel
- All Polish tasks (T046–T050) can run in parallel

---

## Parallel Example: Foundational Phase

```bash
# Launch backend domain models together:
Task: "Create app/domain/widget_config.py ..."
Task: "Create app/domain/memory_inspector.py ..."

# Launch backend repositories together:
Task: "Create app/repositories/widget_config_repository.py ..."
Task: "Create app/repositories/memory_inspector_repository.py ..."

# Launch Streamlit components together (after T015):
Task: "Create streamlit_app/components/auth.py ..."
Task: "Create streamlit_app/components/errors.py ..."
Task: "Create streamlit_app/components/snippets.py ..."
```

## Parallel Example: User Story 1

```bash
# Launch all US1 tests together:
Task: "Contract test for auth/chat endpoints"
Task: "Unit test for BackendAPIClient auth/chat"
Task: "Unit test for login/logout cookie lifecycle"
Task: "Unit test for chat SSE streaming"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Test login + chat independently
5. Demo if ready — internal chatbot works end-to-end

### Incremental Delivery

1. Setup + Foundational → Foundation ready (backend endpoints + Streamlit shell)
2. Add US1 → Login + Chat works → First demo milestone
3. Add US2 → Admin widget config works → Admin features available
4. Add US3 → Memory inspector works → Full internal tool
5. Add US4 → Safety verified → Production-ready internal app
6. Polish → Docs and regression → Final delivery

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1 (login + chat)
   - Developer B: User Story 2 (widget config — needs backend T005–T013 first)
   - Developer C: User Story 3 (memory inspector — needs backend T005–T013 first)
3. After US1–US3: all developers on US4 verification + Polish

---

## Notes

- [P] tasks cover different files with no dependencies on incomplete tasks
- [Story] label maps each task to a specific user story for traceability
- Each user story MUST be independently completable and testable
- Verify tests fail before implementing
- Commit after each task or logical task group
- Stop at any checkpoint to validate story independently
- Backend additions are minimal — only widget config CRUD, embed snippet retrieval, and memory inspection listing that do not already exist in Phase 6/7
- Auth token is stored in browser cookie via streamlit-cookies-manager; st.session_state only holds non-secret UI state
- Admin guard is runtime st.navigation() role exclusion, not manual if/else blocks
- Chat SSE uses httpx streaming with st.write_stream(); full response is never buffered
- All httpx calls use explicit timeouts from StreamlitSettings (30s REST, 70s SSE)
- Tests use streamlit.testing.v1.AppTest with mocked backend API calls via httpx.MockTransport or pytest monkeypatch
