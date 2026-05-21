# Tasks: Embeddable React Widget

**Input**: Design documents from `/specs/009-embeddable-react-widget/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Tests are REQUIRED for critical behavior identified by the
constitution, PLAN.md, the feature specification, or the implementation plan.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Backend**: `app/api`, `app/services`, `app/repositories`, `app/domain`,
  `app/infra`, and `app/core` or `app/shared`
- **Widget**: `widget/` and loader or host demo code under `demo/host/`
- **Project support**: `scripts/`, `tests/`, `docs/`, `prompts/`, `evals/`,
  `data/raw/`, `data/processed/`, and `artifacts/`

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Phase 9 project initialization — Vite React TypeScript widget project,
package.json, tsconfig, and Vite config for one standalone initial bundle.

- [ ] T001 Create `widget/` directory structure: `src/`, `src/__tests__/`, `index.html`, `package.json`, `vite.config.ts`, `tsconfig.json`
- [ ] T002 [P] Create `demo/host/` directory with `allowed.html`, `blocked.html`, `README.md`
- [ ] T003 [P] Create `docs/widget-bundle-report.md` placeholder and `docs/widget-embed.md` placeholder

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Backend extensions that MUST be complete before ANY user story can be implemented.
Phase 8 already provides admin widget CRUD (`widget_configs.py`, `WidgetConfigService`,
`WidgetConfigRepository`, `WidgetConfig` ORM model). Phase 9 extends these.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T004 [P] [Foundational] Add `widget_id` (UUID4), `greeting`, `position`, `enabled_tools` fields to `WidgetConfig` ORM model in `app/infra/orm_models.py`
- [ ] T005 [P] [Foundational] Add `PublicWidgetConfigRead`, `WidgetSessionToken`, `WidgetConfigDelete` schemas to `app/domain/widget_config.py`
- [ ] T006 [Foundational] Create Alembic migration for new widget config fields in `migrations/versions/`
- [ ] T007 [P] [Foundational] Add `WidgetEmbedError` and `WidgetSessionError` to `app/domain/errors.py`
- [ ] T008 [P] [Foundational] Add `WidgetEmbedService` in `app/services/widget_embed_service.py` — origin validation, public config shaping, CSP frame-ancestors header generation
- [ ] T009 [P] [Foundational] Add `WidgetSessionService` in `app/services/widget_session_service.py` — anonymous session token issuance with widget ID + origin validation, token expiry
- [ ] T010 [Foundational] Add `WidgetChatService` in `app/services/widget_chat_service.py` — widget-scoped chat flow reusing Phase 7 `ChatbotService`, validates widget session token before dispatch
- [ ] T011 [P] [Foundational] Add `WidgetAssets` infra in `app/infra/widget_assets.py` — static asset serving from build output with cache headers
- [ ] T012 [Foundational] Extend `WidgetConfigService` in `app/services/widget_config_service.py` — add `delete_config()` with audit row, fix snippet to use `widget_id` and `data-widget-id` attribute
- [ ] T013 [Foundational] Wire widget audit integration — widget config create/update/delete create audit rows with `widget_config.create`, `widget_config.update`, `widget_config.delete` actions in `app/services/widget_config_service.py`
- [ ] T014 [Foundational] Add `GET /widget/loader.js`, `GET /widget/frame/{widget_id}`, `GET /widget/assets/{path}` routes in `app/api/routes/widget_loader.py`
- [ ] T015 [Foundational] Add `GET /widget/config/{widget_id}`, `POST /widget/session`, `POST /widget/chat` routes in `app/api/routes/widget_public.py`
- [ ] T016 [Foundational] Add `DELETE /admin/widget-configs/{config_id}` route to `app/api/routes/widget_configs.py`
- [ ] T017 [Foundational] Wire `widget_public_router` and `widget_loader_router` in `app/api/routes/__init__.py`
- [ ] T018 [Foundational] Add `npm test` (Vitest) and `npm run build` and `npm run size` scripts to `widget/package.json`

**Checkpoint**: Foundation ready — backend widget endpoints, services, domain models,
and widget project scaffolding are all in place.

---

## Phase 3: User Story 1 — Configure A Widget As Admin (Priority: P1) 🎯 MVP

**Goal**: Admin can create, view, update, delete widget configurations with allowed
origins, theme, greeting, position, enabled tools, enabled status, and view the
script snippet. Audit rows are created for all changes.

**Independent Test**: Log in as admin, create a widget config, verify the returned
`widget_id`, allowed origins, display settings, and script snippet. Verify audit
rows are created. Verify regular user cannot create/edit.

### Tests for User Story 1 (REQUIRED) ⚠️

- [ ] T019 [P] [US1] Unit test for `WidgetConfigService.delete_config()` with audit in `tests/unit/test_widget_config_service.py`
- [ ] T020 [P] [US1] Unit test for widget config audit row creation on create/update/delete in `tests/unit/test_widget_config_audit.py`
- [ ] T021 [P] [US1] Contract test for admin widget CRUD endpoints in `tests/contract/test_widget_api_contract.py`
- [ ] T022 [P] [US1] Integration test for admin create → view → update → delete → audit in `tests/integration/test_widget_admin_crud.py`
- [ ] T023 [P] [US1] Authorization test: regular user denied widget config create/edit/delete in `tests/integration/test_widget_admin_crud.py`

### Implementation for User Story 1

- [ ] T024 [US1] Implement `delete_config()` in `app/services/widget_config_service.py` with audit row and transaction (depends on T005, T013)
- [ ] T025 [US1] Fix `generate_embed_snippet()` to use `widget_id` and `<script src="{base}/widget/loader.js" data-widget-id="{widget_id}">` format (depends on T004)
- [ ] T026 [US1] Add `DELETE /admin/widget-configs/{config_id}` route in `app/api/routes/widget_configs.py` (depends on T016)
- [ ] T027 [US1] Wire audit service calls in create/update/delete workflows (depends on T013)
- [ ] T028 [US1] Add redaction test: audit metadata must not contain secrets or raw config payloads in `tests/unit/test_widget_config_audit.py`

**Checkpoint**: Admin can fully manage widget configurations with audit trail.
Script snippet is correctly shaped for host page installation.

---

## Phase 4: User Story 2 — Embed Widget On An Allowed Host (Priority: P2)

**Goal**: Host page can embed the widget using one script tag. The loader injects
an iframe, the iframe loads public config, requests an anonymous session token,
and blocks unallowed origins cleanly.

**Independent Test**: Open `demo/host/allowed.html` with a valid widget ID and
verify the widget iframe appears and loads config. Verify `demo/host/blocked.html`
is blocked with a clean error.

### Tests for User Story 2 (REQUIRED) ⚠️

- [ ] T029 [P] [US2] Unit test for `WidgetEmbedService.origin_allowed()` in `tests/unit/test_widget_origin_policy.py`
- [ ] T030 [P] [US2] Unit test for `WidgetSessionService.issue_token()` in `tests/unit/test_widget_session_service.py`
- [ ] T031 [P] [US2] Contract test for public config read, session issuance, and loader delivery in `tests/contract/test_widget_api_contract.py`
- [ ] T032 [P] [US2] Integration test for allowed-origin embed flow in `tests/integration/test_widget_allowed_origin.py`
- [ ] T033 [P] [US2] Integration test for blocked-origin embed flow in `tests/integration/test_widget_blocked_origin.py`
- [ ] T034 [P] [US2] Integration test for frame response headers (CSP frame-ancestors) in `tests/integration/test_widget_frame_headers.py`

### Implementation for User Story 2

- [ ] T035 [P] [US2] Create `loader.ts` — vanilla JS that reads `data-widget-id`, injects iframe, listens for resize messages in `widget/src/loader.ts`
- [ ] T036 [US2] Implement `GET /widget/loader.js` route in `app/api/routes/widget_loader.py` — serves built loader.js with `Cache-Control` and `Content-Type` headers (depends on T014)
- [ ] T037 [US2] Implement `GET /widget/frame/{widget_id}` route — validates widget enabled + origin, serves iframe HTML with CSP frame-ancestors header (depends on T014, T008)
- [ ] T038 [US2] Implement `GET /widget/config/{widget_id}` public config endpoint — returns `PublicWidgetConfigRead` with origin validation, no-store cache (depends on T008, T015)
- [ ] T039 [US2] Implement `POST /widget/session` anonymous session token endpoint — validates widget enabled + origin, issues scoped token (depends on T009, T015)
- [ ] T040 [US2] Create `demo/host/allowed.html` — demo page with one script tag embedding an allowed widget (depends on T035)
- [ ] T041 [US2] Create `demo/host/blocked.html` — demo page from unallowed origin demonstrating blocked embed (depends on T035)
- [ ] T042 [US2] Implement `GET /widget/assets/{path}` static asset serving with immutable cache headers for hashed assets (depends on T011, T014)

**Checkpoint**: Allowed host pages can embed the widget. Blocked origins are
rejected cleanly. Frame headers enforce origin restrictions.

---

## Phase 5: User Story 3 — Chat Through The Embedded Widget (Priority: P3)

**Goal**: End user can open the collapsed widget bubble, see the configured
greeting and theme, send messages, and receive streamed chat responses in the
expanded panel over native `EventSource`.

**Independent Test**: Load `demo/host/allowed.html`, open the widget, send a
message, and verify streamed response content appears progressively.

### Tests for User Story 3 (REQUIRED) ⚠️

- [ ] T043 [P] [US3] Vitest test for widget `App.tsx` component render (bubble + panel) in `widget/src/__tests__/App.test.tsx`
- [ ] T044 [P] [US3] Vitest test for widget `api.ts` SSE streaming with `EventSource` in `widget/src/__tests__/api.test.ts`
- [ ] T045 [P] [US3] Vitest test for resize message channel in `widget/src/__tests__/messages.test.ts`
- [ ] T046 [P] [US3] Integration test for widget chat stream over `EventSource` in `tests/integration/test_widget_chat_stream.py`

### Implementation for User Story 3

- [ ] T047 [P] [US3] Create `widget/src/styles.css` — vanilla CSS for collapsed bubble, expanded panel, message list, input form, theme variants
- [ ] T048 [P] [US3] Create `widget/src/api.ts` — typed backend API client: public config read, session token request, `EventSource` SSE chat stream
- [ ] T049 [P] [US3] Create `widget/src/messages.ts` — `postMessage` resize channel with origin validation, bounded dimensions
- [ ] T050 [US3] Create `widget/src/App.tsx` — React widget with collapsed bubble state, expanded panel state, greeting display, theme application, message list, input form, streaming renderer
- [ ] T051 [US3] Create `widget/src/main.tsx` — React entry point, reads bootstrap values from iframe shell, mounts `App.tsx`
- [ ] T052 [US3] Implement `POST /widget/chat` SSE endpoint — validates widget session token, reuses Phase 7 `ChatbotService`, streams events (depends on T010, T015)
- [ ] T053 [US3] Handle stream interruption in widget — visible partial state, retry option (depends on T050, T048)
- [ ] T054 [US3] Handle widget errors, disabled states, blocked origins with clean user-facing states (no stack traces) in `widget/src/App.tsx`

**Checkpoint**: Visitors can chat through the embedded widget with streamed
responses, configured theme, greeting, and clean error handling.

---

## Phase 6: User Story 4 — Review Production Embed Safety (Priority: P4)

**Goal**: Reviewer can verify widget isolation, origin rejection, shared backend
API usage, no Streamlit dependency, and documented bundle-size evidence.

**Independent Test**: Inspect bundle size report, run static checks for Streamlit
references, verify frame headers, test resize message validation, confirm zero
Streamlit coupling.

### Tests for User Story 4 (REQUIRED) ⚠️

- [ ] T055 [P] [US4] Static check: no `streamlit` or `streamlit_app` references in `widget/`, `demo/host/`, `app/api/routes/widget_public.py`, `app/api/routes/widget_loader.py` in `tests/unit/test_widget_no_streamlit.py`
- [ ] T056 [P] [US4] Build validation: one standalone initial widget JS bundle, loader < 5 KB gzip, bundle ≤ 150 KB gzip in `tests/unit/test_widget_bundle.py`
- [ ] T057 [P] [US4] Static check: `postMessage` usage limited to resize channel in `widget/` and `demo/host/` in `tests/unit/test_widget_no_streamlit.py`

### Implementation for User Story 4

- [ ] T058 [US4] Add `npm run size` script in `widget/package.json` — measures raw and gzip sizes of loader.js and initial bundle, outputs `docs/widget-bundle-report.md` (depends on T018)
- [ ] T059 [US4] Configure Vite `vite.config.ts` for one standalone initial JS bundle — `manualChunks`, `rollupOptions.output` (depends on T001)
- [ ] T060 [US4] Generate `docs/widget-bundle-report.md` after build with measured sizes and any exception rationale
- [ ] T061 [US4] Update `docs/runbook.md` with widget startup, demo host verification, and troubleshooting
- [ ] T062 [US4] Update `docs/decisions.md` with Phase 9 decisions (loader serving, iframe isolation, bundle strategy, origin enforcement)
- [ ] T063 [US4] Update `docs/security.md` with Phase 9 widget security boundaries (origin allowlisting, CSP frame-ancestors, anonymous session tokens, no Streamlit coupling)

**Checkpoint**: All user stories are independently functional. Bundle size is
documented. Security boundaries are verified and documented.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories.

- [ ] T064 [P] Validate `specs/009-embeddable-react-widget/quickstart.md` test list against actual test files
- [ ] T065 [P] Add `.gitignore` and `.dockerignore` entries for `widget/node_modules/`, `widget/dist/`
- [ ] T066 Run full regression test suite — all existing Phase 1–8 tests must pass
- [ ] T067 [P] Update `docker-compose.yml` to include widget build context and demo host serving if needed

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational phase completion
  - User stories can proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P2 → P3)
- **Polish (Phase 7)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) — extends Phase 8 admin CRUD with delete + audit
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) — public config, session, loader, iframe, demos
- **User Story 3 (P3)**: Can start after Foundational (Phase 2) — React widget chat UI, SSE streaming
- **User Story 4 (P4)**: Can start after US2 and US3 — bundle validation, security checks, docs

### Within Each User Story

- Required tests MUST be written and FAIL before implementation
- Domain models before services
- Services before endpoints
- Core implementation before integration
- Story complete before moving to next priority

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel
- All Foundational tasks marked [P] can run in parallel (within Phase 2)
- Once Foundational phase completes, all user stories can start in parallel
- All tests for a user story marked [P] can run in parallel
- Domain models within a story marked [P] can run in parallel

---

## Parallel Example: User Story 1

```bash
# Launch all required tests for User Story 1 together:
uv run pytest tests/unit/test_widget_config_service.py
uv run pytest tests/unit/test_widget_config_audit.py
uv run pytest tests/contract/test_widget_api_contract.py
uv run pytest tests/integration/test_widget_admin_crud.py

# Launch implementation tasks:
# T024: delete_config in service
# T025: fix embed snippet
# T026: DELETE route
# T027: audit wiring
# T028: redaction test
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Admin can create widget config, view snippet, delete with audit
5. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Admin widget config management with audit → Deploy/Demo (MVP!)
3. Add User Story 2 → Host page embed with origin enforcement → Deploy/Demo
4. Add User Story 3 → Visitor chat through widget → Deploy/Demo
5. Add User Story 4 → Safety review, bundle report, docs → Complete phase
6. Each story adds value without breaking previous stories

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story MUST be independently completable and testable
- Verify tests fail before implementing
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Phase 8 already provides admin widget CRUD — Phase 9 extends it with delete, audit, public config, session, loader, iframe, React widget, and demos
- Widget code must NOT reference Streamlit or internal-only endpoints
- `postMessage` is ONLY for controlled resize messages
- Bundle size target: ≤ 150 KB gzip for initial widget bundle; loader < 5 KB gzip
