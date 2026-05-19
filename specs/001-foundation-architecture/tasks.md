# Tasks: 001 — Foundation and Architecture Skeleton

## Format

```
- [ ] T### [P] [US#] Description — `path/to/file`
```

- `- [ ]` checkbox always first
- `T###` sequential task ID (T001, T002, …)
- `[P]` present only when the task is safely parallelizable (different files, no dependency on an incomplete task in the same phase)
- `[US1]` / `[US2]` / `[US3]` present only inside a user-story phase (Phases 3–5), never in Setup, Foundational, or Polish phases
- Exact file path always stated inside the description

## Path Conventions

All paths are relative to the project root (`maintainer-copilot/`).

| Prefix | Layer |
|---|---|
| `app/api/` | HTTP transport — route handlers only |
| `app/services/` | Business/orchestration logic |
| `app/repositories/` | Data access |
| `app/domain/` | Pure domain types and errors |
| `app/infra/` | Infrastructure adapters (DB, Redis, Vault, MinIO) |
| `app/core/` | Application factory, config, lifespan, logging, middleware |
| `migrations/` | Alembic migration scripts |
| `tests/` | Automated test suite |
| `scripts/` | Operational CLI helpers |
| `docs/` | Human-readable documentation |
| `model_server/`, `chatbot/`, `widget/`, `demo/host/` | Skeletal future services |

## Constitution-Driven Requirements

The project constitution mandates:

1. **Tests for ALL critical behavior** — no exceptions. Every route, service, config path, error handler, import side-effect constraint, and architecture guardrail must have a corresponding test.
2. **Tests before implementation** — within Phase 3 (US1), tests T018–T022 must be written and committed before implementation tasks T023–T028.
3. **No secrets in committed files** — `.env.example` and all `docs/` files must contain only fake/placeholder values.
4. **No import side-effects** — importing any module in `app/` must not open network connections, create DB engines, or contact Vault.
5. **Route layer isolation** — `app/api/` handlers must never import or call SQLAlchemy, Redis, hvac, or MinIO directly; they call services only.
6. **Loud startup failure** — if Vault is unreachable or AppRole auth fails at lifespan startup, the process must raise `ConfigError` and refuse to start.
7. **Structured logging** — all log output is JSON via structlog; `request_id` is bound to every log entry via contextvars.
8. **Error response shape** — every error response (including uncaught exceptions) must be `{error_code, message, request_id}` with no stack traces.

---

## Phase 1: Setup

**Purpose:** Project initialization, package management, directory scaffold, git configuration. These tasks have no inter-dependencies and can all run after T001 completes.

- [X] T001 Initialize Python project with uv — create `pyproject.toml` with `name = "maintainer-copilot"`, `requires-python = ">=3.11"`, and dependency groups: `[project.dependencies]` empty (populated in later phases), `[dependency-groups] dev` includes `pytest`, `pytest-asyncio`, `httpx`, `mypy`, `ruff`, `isort`; add `[tool.ruff]`, `[tool.mypy]`, `[tool.pytest.ini_options]` sections with sane defaults (`asyncio_mode = "auto"` for pytest-asyncio)
- [X] T002 [P] Create `.gitignore` — exclude: `.env`, `.env.local`, `.venv`, `__pycache__/`, `data/raw/`, `data/processed/`, `artifacts/`, `*.pyc`, `.mypy_cache/`, `.pytest_cache/`, `*.egg-info/`, `dist/`, `*.so`, `*.pyd`, `.DS_Store`
- [X] T003 [P] Create `.env.example` with bootstrap-only placeholder values — `VAULT_ADDR=http://localhost:8200`, `VAULT_ROLE_ID=fake-role-id`, `VAULT_SECRET_ID=fake-secret-id`, `ENVIRONMENT=local`, `SERVICE_NAME=maintainer-copilot`; add a comment at the top: `# Copy to .env — all real secrets are resolved from Vault at startup`; no real credentials, no real UUIDs, no real passwords
- [X] T004 [P] Create placeholder directories with `.gitkeep` — `prompts/.gitkeep`, `evals/.gitkeep`, `data/raw/.gitkeep`, `data/processed/.gitkeep`, `artifacts/.gitkeep`; also ensure `migrations/versions/` directory exists with a `.gitkeep` until the first migration file is created
- [X] T005 [P] Create all Python package `__init__.py` files — empty files at: `app/__init__.py`, `app/api/__init__.py`, `app/api/routes/__init__.py`, `app/services/__init__.py`, `app/repositories/__init__.py`, `app/domain/__init__.py`, `app/infra/__init__.py`, `app/core/__init__.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose:** Core infrastructure that MUST be complete before any user story can be implemented. All route handlers, services, and tests depend on these modules. Within this phase some tasks are independent ([P]) and can run in parallel.

- [X] T006 Create `AppSettings` in `app/core/config.py` — `pydantic_settings.BaseSettings` subclass; required fields (no defaults): `environment: str`, `vault_addr: str`, `vault_role_id: str`, `vault_secret_id: str`; optional fields with defaults: `log_level: str = "INFO"`, `service_name: str = "maintainer-copilot"`, `vault_secret_mount: str = "secret"`, `vault_secret_path: str = "maintainer-copilot/app"`, `request_id_header: str = "X-Request-ID"`; Vault-resolved fields (populated by lifespan, not at construction): `database_url: str | None = None`, `redis_url: str | None = None`, `minio_endpoint: str | None = None`, `minio_access_key: str | None = None`, `minio_secret_key: str | None = None`; `model_config = SettingsConfigDict(env_file=".env", extra="ignore")`; no network calls, no Vault calls at class construction or module import
- [X] T007 [P] Create `DomainError` hierarchy in `app/domain/errors.py` — base `DomainError(Exception)` with `__init__(self, message: str, details: dict | None = None)`; class-level defaults: `error_code: str = "DOMAIN_ERROR"`, `status_code: int = 500`; subclasses: `ConfigError(DomainError)` with `error_code = "CONFIG_ERROR"`, `status_code = 500`; `DependencyError(DomainError)` with `error_code = "DEPENDENCY_UNAVAILABLE"`, `status_code = 503`; `ValidationError(DomainError)` with `error_code = "VALIDATION_ERROR"`, `status_code = 422`; `ServerError(DomainError)` with `error_code = "SERVER_ERROR"`, `status_code = 500`; no imports from `app/infra/` or `app/core/`
- [X] T008 [P] Create domain models in `app/domain/models.py` — all are `pydantic.BaseModel` subclasses; `RequestContext`: fields `request_id: str`, `trace_id: str | None = None`, `path: str | None = None`, `method: str | None = None`; `ReadinessCheck`: fields `name: str`, `status: Literal["ok", "degraded", "unavailable"]`, `message: str | None = None`; `HealthStatus`: fields `status: Literal["ok", "degraded", "unavailable"]`, `service: str`, `version: str | None = None`, `checks: list[ReadinessCheck] = []`, `request_id: str | None = None`; `ErrorResponse`: fields `error_code: str`, `message: str`, `request_id: str`; no imports from `app/infra/` or `app/core/`
- [X] T009 [P] Configure structlog JSON logging in `app/core/logging.py` — processors chain: `structlog.contextvars.merge_contextvars`, `structlog.stdlib.add_log_level`, `structlog.stdlib.add_logger_name`, `structlog.processors.TimeStamper(fmt="iso")`, `structlog.processors.JSONRenderer()`; also configure `logging.basicConfig` to route stdlib logs through structlog using `structlog.stdlib.ProcessorFormatter`; expose `configure_logging(settings: AppSettings) -> None` function; this function sets root logger level from `settings.log_level`; function is idempotent (safe to call multiple times); no network calls; no side effects at module import time
- [X] T010 Create X-Request-ID middleware in `app/core/middleware.py` — `RequestIDMiddleware(BaseHTTPMiddleware)`; on each request: read `settings.request_id_header` header value; if absent, generate `str(uuid.uuid4())`; call `structlog.contextvars.bind_contextvars(request_id=request_id)`; set `request.state.request_id = request_id`; call `await call_next(request)`; set the same header on the response; call `structlog.contextvars.clear_contextvars()` after response; depends on T006 (`AppSettings`) and T009 (`configure_logging`)
- [X] T011 [P] Create Vault AppRole client in `app/infra/vault_client.py` — `init_vault_client(settings: AppSettings) -> hvac.Client`; creates `hvac.Client(url=settings.vault_addr)`; calls `client.auth.approle.login(role_id=settings.vault_role_id, secret_id=settings.vault_secret_id)`; raises `ConfigError("Vault AppRole authentication failed", details={"vault_addr": settings.vault_addr})` if login fails or client is not authenticated after login; `fetch_secrets(client: hvac.Client, mount: str, path: str) -> dict`; reads KV-v2 secret at mount/path; raises `ConfigError` if path missing or required keys absent; MUST NOT log `secret_id`, `role_id` values, token values, or any returned secret values; depends on T006 and T007
- [X] T012 [P] Create async database client in `app/infra/database.py` — `create_engine(database_url: str) -> AsyncEngine` using `sqlalchemy.ext.asyncio.create_async_engine` with `asyncpg` driver (URL prefix `postgresql+asyncpg://`); `async_session_factory` via `async_sessionmaker(engine, expire_on_commit=False)`; `async def get_session() -> AsyncGenerator[AsyncSession, None]` FastAPI dependency; `async def probe_database(engine: AsyncEngine, timeout: float = 3.0) -> ReadinessCheck` — executes `SELECT 1`, returns `ReadinessCheck(name="postgres", status="ok")` on success or `ReadinessCheck(name="postgres", status="unavailable", message="<safe description>")` on any exception (never include raw exception text); no module-level engine creation; depends on T007 and T008
- [X] T013 [P] Create async Redis client in `app/infra/redis_client.py` — `create_redis_client(redis_url: str) -> redis.asyncio.Redis` using `redis.asyncio.from_url(redis_url, decode_responses=True)`; `async def get_redis(request: Request) -> redis.asyncio.Redis` FastAPI dependency that reads from `request.app.state.redis`; `async def probe_redis(client: redis.asyncio.Redis, timeout: float = 2.0) -> ReadinessCheck` — sends `PING`, returns `ReadinessCheck(name="redis", status="ok")` on `PONG` or `ReadinessCheck(name="redis", status="unavailable", message="<safe description>")` on failure; no module-level client creation; depends on T007 and T008
- [X] T014 [P] Create MinIO client placeholder in `app/infra/minio_client.py` — `create_minio_client(endpoint: str, access_key: str, secret_key: str) -> minio.Minio`; `async def probe_minio(endpoint: str, timeout: float = 3.0) -> ReadinessCheck` — sends HTTP GET to `http://{endpoint}/minio/health/live` via `httpx.AsyncClient` with `timeout=timeout`; returns `ReadinessCheck(name="minio", status="ok")` if status 200, `ReadinessCheck(name="minio", status="unavailable", message="<safe description>")` otherwise; no module-level client creation; depends on T007 and T008
- [X] T015 Create FastAPI lifespan in `app/core/lifespan.py` — `@asynccontextmanager async def lifespan(app: FastAPI)`; startup sequence: (1) call `configure_logging(settings)`, (2) call `init_vault_client(settings)` — raises `ConfigError` on failure causing loud crash, (3) call `fetch_secrets(vault_client, settings.vault_secret_mount, settings.vault_secret_path)` and populate `settings.database_url`, `settings.redis_url`, `settings.minio_endpoint`, `settings.minio_access_key`, `settings.minio_secret_key` from returned dict, (4) create DB engine via `create_engine(settings.database_url)`, (5) create Redis client via `create_redis_client(settings.redis_url)`, (6) create MinIO client via `create_minio_client(...)`, (7) store all clients in `app.state` (`app.state.db_engine`, `app.state.redis`, `app.state.minio`, `app.state.vault_client`, `app.state.settings`), (8) log `"startup complete"` at INFO level; shutdown: close `app.state.redis`, dispose `app.state.db_engine`; depends on T006, T009, T011, T012, T013, T014
- [X] T016 Create app factory in `app/core/application.py` — `def create_app() -> FastAPI`; instantiates `AppSettings()` (reads env vars, no Vault); creates `FastAPI(title="Maintainer Copilot", lifespan=lifespan)`; calls `app.add_middleware(RequestIDMiddleware, settings=settings)`; calls `register_error_handlers(app)`; returns `app` WITHOUT registering any routers (router registration is done in each route module's setup, keeping the factory free of Phase 3 forward dependencies); the module-level statement `app = create_app()` is the ASGI entrypoint; no DB/Redis/Vault calls at module import or at `create_app()` call time; depends on T006, T010, T015, T017
- [X] T017 [P] Create global error handlers in `app/api/error_handlers.py` — `def register_error_handlers(app: FastAPI) -> None`; handler for `DomainError`: extract `error_code`, `message`, `status_code` from exception; read `request_id` from `request.state.request_id` (fallback `"unknown"`); return `JSONResponse(status_code=exc.status_code, content=ErrorResponse(error_code=..., message=..., request_id=...).model_dump(), headers={"X-Request-ID": request_id})`; handler for bare `Exception`: log at ERROR level with `request_id` in context; return `JSONResponse(status_code=500, content=ErrorResponse(error_code="SERVER_ERROR", message="An unexpected error occurred", request_id=request_id).model_dump())`; MUST NOT include stack traces, raw exception text, or internal paths in any response body; depends on T007, T008

---

## Phase 3: User Story 1 — Start and Validate the Local Foundation (P1)

**Goal:** Developer completes clean-checkout setup, starts all 6 default services via `docker compose up --wait`, and confirms `/health/live` returns 200 and `/health/ready` returns 200 (all checks "ok") or 503 (per-check statuses reflect actual dependency health).

**Independent Test:**
```bash
docker compose up --wait && \
  curl -sf localhost:8000/health/live | python3 -m json.tool && \
  curl -s localhost:8000/health/ready | python3 -m json.tool
```
Expected: `/health/live` → 200 `{"status":"ok","service":"maintainer-copilot","checks":[]}`; `/health/ready` → 200 with 5 checks all `"ok"`.

**Tests first, then implementation.**

### Tests

- [X] T018 [P] [US1] Write `tests/conftest.py` — pytest fixtures: `settings` returns `AppSettings(environment="test", vault_addr="http://fake-vault:8200", vault_role_id="fake-role", vault_secret_id="fake-secret", database_url="postgresql+asyncpg://fake/fake", redis_url="redis://fake:6379/0", minio_endpoint="fake-minio:9000", minio_access_key="fake", minio_secret_key="fake")`; `mock_vault` fixture patches `app.infra.vault_client.init_vault_client` and `app.infra.vault_client.fetch_secrets` to return a pre-populated dict; `mock_db` patches `app.infra.database.probe_database` to return `ReadinessCheck(name="postgres", status="ok")`; `mock_redis` patches `app.infra.redis_client.probe_redis` to return `ReadinessCheck(name="redis", status="ok")`; `mock_minio` patches `app.infra.minio_client.probe_minio` to return `ReadinessCheck(name="minio", status="ok")`; `app` fixture: override lifespan with `AsyncExitStack` that skips real Vault/DB/Redis init and populates `app.state` from `settings`; returns `httpx.AsyncClient(app=fastapi_app, base_url="http://test")`; all fixtures scoped to `function`
- [X] T019 [P] [US1] Write `tests/test_config.py` — `test_valid_settings_construction`: construct `AppSettings` with all required fields and assert no exception; `test_missing_vault_addr_raises`: omit `VAULT_ADDR` and assert `pydantic_settings.ValidationError` (or `pydantic.ValidationError`) is raised; `test_missing_vault_role_id_raises`: same for `VAULT_ROLE_ID`; `test_missing_vault_secret_id_raises`: same for `VAULT_SECRET_ID`; `test_missing_environment_raises`: same for `ENVIRONMENT`; `test_vault_resolved_fields_default_none`: construct valid `AppSettings` and assert `database_url is None` (not yet populated); all tests use `monkeypatch.setenv` to inject env vars rather than real `.env` file
- [X] T020 [P] [US1] Write `tests/test_health.py` — `test_live_returns_200`: GET `/health/live` returns 200, body `status == "ok"`, `service == "maintainer-copilot"`, `checks == []`; `test_ready_all_ok_returns_200`: GET `/health/ready` with all deps healthy returns 200 and exactly 5 `ReadinessCheck` items all with `status == "ok"`, names: `postgres`, `redis`, `minio`, `vault`, `pgvector`; `test_ready_postgres_fail_returns_503`: mock `probe_database` to return `status="unavailable"` → assert 503; `test_request_id_header_present_on_live`: assert `X-Request-ID` header exists in response; `test_request_id_header_present_on_ready`: same for ready; `test_request_id_echoed_from_request`: send `X-Request-ID: my-custom-id-123` in request, assert response has same value; `test_request_id_generated_when_absent`: send no `X-Request-ID`, assert response header is a valid UUID4 string
- [X] T021 [P] [US1] Write `tests/test_errors.py` — `test_domain_error_returns_correct_code_and_status`: create a test route that raises `DependencyError("service down")`; call it; assert 503 and `error_code == "DEPENDENCY_UNAVAILABLE"`; `test_unhandled_exception_returns_server_error`: create a test route that raises bare `Exception("boom")`; assert 500, `error_code == "SERVER_ERROR"`; `test_error_response_contains_request_id`: assert `request_id` field is present in error response body and non-empty; `test_no_stack_trace_in_message`: assert response body `message` does not contain "Traceback", "File ", or "line "; `test_error_response_shape`: assert response body has exactly the keys `error_code`, `message`, `request_id` and no others
- [X] T022 [P] [US1] Write `tests/test_import_side_effects.py` — each test imports the target module in a subprocess (via `subprocess.run(["python3", "-c", "import <module>"], capture_output=True)`) with all network interfaces blocked (or with `VAULT_ADDR=http://127.0.0.1:1` to guarantee connection refused) and asserts returncode == 0; modules to check: `app.core.application`, `app.core.config`, `app.core.lifespan`, `app.api.routes.health`, `app.infra.database`, `app.infra.redis_client`, `app.infra.vault_client`, `app.infra.minio_client`; test names: `test_import_application_no_network`, `test_import_config_no_network`, etc.; asserts that no `ConnectionRefusedError`, `hvac` auth exception, or SQLAlchemy connection error appears in stderr

### Implementation

- [X] T023 [US1] Create `HealthService` in `app/services/health_service.py` — `async def check_liveness(settings: AppSettings) -> HealthStatus`: returns `HealthStatus(status="ok", service=settings.service_name, checks=[])`; `async def check_readiness(db_engine, redis_client, minio_endpoint: str, vault_client, settings: AppSettings) -> HealthStatus`: runs all 5 probes concurrently with `asyncio.gather(*probes, return_exceptions=True)`; probes: (1) `probe_database(db_engine, timeout=3.0)` → `ReadinessCheck(name="postgres", ...)`, (2) `probe_redis(redis_client, timeout=2.0)` → `ReadinessCheck(name="redis", ...)`, (3) `probe_minio(minio_endpoint, timeout=3.0)` → `ReadinessCheck(name="minio", ...)`, (4) **Vault probe MUST use `asyncio.to_thread`** because hvac is synchronous: `await asyncio.wait_for(asyncio.to_thread(vault_client.is_authenticated), timeout=2.0)` — returns `ReadinessCheck(name="vault", status="ok")` on `True`, `ReadinessCheck(name="vault", status="unavailable", message="not authenticated")` on `False` or any exception, (5) probe pgvector by executing `SELECT extname FROM pg_extension WHERE extname='vector'` via `AsyncSession` with 3s timeout → `ReadinessCheck(name="pgvector", ...)`; aggregates: if all checks `"ok"` → `status="ok"`, else `status="unavailable"`; never includes raw exception text in `message` fields; depends on T008, T012, T013, T014
- [X] T024 [US1] Create health router in `app/api/routes/health.py` and register it — `router = APIRouter(tags=["health"])`; `GET /live`: dependency-inject `settings: AppSettings = Depends(get_settings)` and call `check_liveness(settings)`, return `HealthStatus` with 200; `GET /ready`: dependency-inject `db_engine` from `request.app.state.db_engine`, `redis_client` from `request.app.state.redis`, `minio_endpoint` from `request.app.state.settings.minio_endpoint`, `vault_client` from `request.app.state.vault_client`, `settings`; call `check_readiness(...)`; return `HealthStatus` with status 200 if `status=="ok"` else 503; route handlers MUST NOT import or directly call `sqlalchemy`, `redis`, `hvac`, or `minio` — they call `health_service` functions only; at the bottom of this module import `app` from `app.core.application` and call `app.include_router(router, prefix="/health")` so the factory (T016) remains free of forward dependencies on Phase 3 modules; depends on T008, T016, T023
- [X] T025 [US1] Set up Alembic — create `alembic.ini` at project root with `script_location = migrations`, `sqlalchemy.url` left blank (overridden in `env.py`); create `migrations/env.py` as async-compatible: import `asyncio`, `AsyncEngine`, `create_async_engine`; `DATABASE_URL = os.environ["DATABASE_URL"]`; `target_metadata = None` (no ORM models in Phase 1); `run_migrations_online()` creates `AsyncEngine`, calls `async_engine_from_config` or constructs engine directly, uses `connectable.connect()` with `context.configure(connection=conn, target_metadata=target_metadata)` and `context.run_migrations()`; create `migrations/script.py.mako` with standard Alembic template content
- [X] T026 [US1] Create baseline migration in `migrations/versions/0001_baseline.py` — `revision = "0001_baseline"`, `down_revision = None`, `branch_labels = None`, `depends_on = None`; `upgrade()`: `op.execute("CREATE EXTENSION IF NOT EXISTS vector")`; `downgrade()`: `op.execute("DROP EXTENSION IF EXISTS vector")`; no table DDL in this migration — Phase 1 schema is empty beyond the extension
- [X] T027 [US1] Create root `Dockerfile` and `docker-compose.yml` — **Step 1: create `Dockerfile`** at project root: `FROM python:3.11-slim`, `WORKDIR /app`, `RUN pip install uv`, `COPY pyproject.toml .`, `RUN uv sync --no-dev` (or `uv sync` if dev deps needed for migrations runner), `COPY . .`, `EXPOSE 8000`, `CMD ["uvicorn", "app.core.application:app", "--host", "0.0.0.0", "--port", "8000"]`; this single `Dockerfile` is reused by both the `backend` and `migrations` services in Compose (the migrations service overrides `command` to run Alembic instead). **Step 2: create `docker-compose.yml`** — default profile (no `--profile` flag needed) starts exactly 6 services: (1) `postgres`: image `pgvector/pgvector:pg16`, env `POSTGRES_DB=maintainer`, `POSTGRES_USER=maintainer`, `POSTGRES_PASSWORD=maintainer`, healthcheck `pg_isready -U maintainer`, expose 5432; (2) `redis`: image `redis:7-alpine`, healthcheck `redis-cli ping`, expose 6379; (3) `minio`: image `minio/minio:latest`, command `server /data`, env `MINIO_ROOT_USER=minioadmin`, `MINIO_ROOT_PASSWORD=minioadmin`, healthcheck `curl -sf http://localhost:9000/minio/health/live`, expose 9000; (4) `vault`: image `hashicorp/vault:1.15`, env `VAULT_DEV_ROOT_TOKEN_ID=dev-root-token`, `VAULT_DEV_LISTEN_ADDRESS=0.0.0.0:8200`, cap_add `IPC_LOCK`, healthcheck `vault status`, expose 8200; (5) `migrations`: build context `./`, dockerfile inline or separate, `depends_on: {postgres: {condition: service_healthy}}`, command `alembic upgrade head`, `restart: no`; (6) `backend`: build context `./`, `depends_on: {postgres: service_healthy, redis: service_healthy, minio: service_healthy, vault: service_healthy, migrations: service_completed_successfully}`, env_file `.env`, expose 8000; skeletal services (`model_server`, `chatbot`, `widget`, `demo_host`) NOT present yet (added in T041); NO hardcoded real secrets — compose uses only dev/fake credentials that match `.env.example`
- [X] T028 [US1] Create `scripts/validate_stack.py` — CLI script using only stdlib; checks in order: (1) `VAULT_ADDR` env var set and non-empty — print OK or error and `sys.exit(1)`; (2) `VAULT_ROLE_ID` non-empty; (3) `VAULT_SECRET_ID` non-empty; (4) `subprocess.run(["docker", "compose", "config"], capture_output=True)` exits 0 — print OK or print stderr and exit 1; (5) attempt HTTP GET to `VAULT_ADDR + "/v1/sys/health"` with 3s timeout using `urllib.request`; print PASS/FAIL summary for each check; exit 0 only if all checks pass; add `if __name__ == "__main__": main()` guard

**Checkpoint:** `docker compose up --wait` starts exactly 6 default services; `GET /health/live` returns 200; `GET /health/ready` returns 200 with 5 checks; `pytest tests/test_config.py tests/test_health.py tests/test_errors.py tests/test_import_side_effects.py -v` → 0 failures.

---

## Phase 4: User Story 2 — Review the Architecture Boundaries (P2)

**Goal:** Reviewer can inspect the repository and identify all layer boundaries, architecture docs, and guardrails preventing route violations in under 5 minutes.

**Independent Test:**
```bash
pytest tests/test_route_boundaries.py tests/test_no_secrets.py -v && ls docs/
```
Expected: both test files pass; `docs/` lists `architecture.md`, `decisions.md`, `runbook.md`, `evals.md`, `security.md`.

### Tests

- [X] T029 [P] [US2] Write `tests/test_route_boundaries.py` — use `ast.parse` on every `.py` file under `app/api/` to inspect import statements; `test_no_sqlalchemy_in_api`: assert no `from sqlalchemy` or `import sqlalchemy` in any `app/api/` file; `test_no_redis_in_api`: assert no `from redis` or `import redis` in any `app/api/` file; `test_no_hvac_in_api`: assert no `from hvac` or `import hvac`; `test_no_minio_in_api`: assert no `from minio` or `import minio`; `test_no_httpx_direct_in_api`: assert no `import httpx` or `from httpx` in any `app/api/` file (httpx calls go through service layer); helper: `collect_python_files(directory: Path) -> list[Path]` that walks the directory; helper: `ast_imports(source: str) -> list[str]` that returns all imported module names; each test must produce a clear failure message listing the offending file if the assertion fails
- [X] T030 [P] [US2] Write `tests/test_no_secrets.py` — `test_env_example_no_real_credentials`: read `.env.example` and assert no matches for patterns: `sk-[A-Za-z0-9]{20,}`, actual UUIDs matching `[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}` except `fake-`, passwords longer than 12 chars that aren't the word "fake" or "example" or "placeholder"; `test_docs_no_secrets`: for each `.md` file in `docs/`, scan for same secret patterns; `test_no_env_file_committed`: assert `.env` does not exist at project root (would mean a real secrets file was committed); use `re` module for pattern matching; each assertion includes the file path and matched text in the error message

### Implementation

- [X] T031 [P] [US2] Write `docs/architecture.md` — sections: (1) **Layer Ownership Table** with columns Layer, Directory, Owns, Forbidden From — fill in all 6 layers (`api`, `services`, `repositories`, `domain`, `infra`, `core`); (2) **Dependency Flow** — narrative description of allowed call directions (api → services → repositories → domain; infra → domain; core → all); (3) **Guardrails** — explicit rules: "Routes may not import sqlalchemy, redis, hvac, minio, or httpx directly; they call app/services/ functions only"; "app/domain/ has no imports from app/infra/ or app/core/"; "No module may make network connections at import time"; (4) **Extension Points** — where to add new routes, services, repositories, infra adapters in later phases
- [X] T032 [P] [US2] Write `docs/decisions.md` — three Phase 1 ADRs: **ADR-001 structlog for structured logging**: decision: use structlog with JSON renderer; rationale: machine-parseable logs, contextvars support, request_id binding; alternatives rejected: standard `logging` (no structured output), loguru (less contextvars integration); **ADR-002 Vault AppRole for secret resolution**: decision: all secrets read from Vault at lifespan startup; rationale: no secrets in env vars or image; alternatives rejected: env-file secrets (committed risk), AWS Secrets Manager (vendor lock-in for local dev); **ADR-003 X-Request-ID header strategy**: decision: middleware generates UUID4 if header absent, echoes it on response; rationale: end-to-end traceability; alternatives rejected: trace headers only (not HTTP-visible to clients); add placeholder section `## Phase 2+ Decisions` with note "To be added as phases progress"
- [X] T033 [P] [US2] Write `docs/runbook.md` — sections: **Start Stack**: `cp .env.example .env && docker compose up --wait`; **Stop Stack**: `docker compose down -v`; **Run Tests**: `uv run pytest tests/ -v`; **Run Migrations**: `DATABASE_URL=<url> uv run alembic upgrade head`; **Check Health**: `curl -s localhost:8000/health/live | jq .` and `curl -s localhost:8000/health/ready | jq .`; **Common Failures**: Vault unreachable (check VAULT_ADDR, run `docker compose ps vault`); postgres unhealthy (check `docker compose logs postgres`); pgvector not installed (run `docker compose restart migrations`); backend crash on startup (Vault auth failure — check VAULT_ROLE_ID / VAULT_SECRET_ID)
- [X] T034 [P] [US2] Write `docs/evals.md` — Phase 1 skeleton: opening paragraph explaining this document will record eval methodology, golden sets, and threshold decisions when AI/model components are introduced in later phases; note: "Phase 1 contains no AI inference, no embeddings, no LLM calls, and therefore no eval decisions"; add placeholder sections: **Eval Strategy** (TBD Phase 4+), **Golden Datasets** (TBD), **Threshold Decisions** (TBD), **Regression Criteria** (TBD)
- [X] T035 [P] [US2] Write `docs/security.md` — sections: **Secret Handling Policy**: no secrets committed to git; `.env.example` contains only fake values; all real secrets resolved from Vault AppRole at startup; **Vault AppRole Policy**: role must have read-only access to `secret/data/maintainer-copilot/app`; role_id and secret_id sourced from environment at container start, never hardcoded; **Redaction Policy**: placeholder — "Will be activated in Phase 4+ when PII or sensitive data flows through the system; all AI inference logs must redact user content by default"; **`.gitignore` Rules**: list the secret-related entries (`.env`, `.env.local`, `data/raw/`, `data/processed/`, `artifacts/`)
- [X] T036 [US2] Write `README.md` — sections: **Maintainer's Copilot** (1-paragraph project purpose); **Prerequisites**: Docker Desktop / Docker Engine, `uv` (Python package manager), Vault CLI (optional for local secret management); **Quick Start**: (1) `git clone <repo> && cd maintainer-copilot`, (2) `uv sync`, (3) `cp .env.example .env`, (4) `docker compose up --wait`, (5) `curl -s localhost:8000/health/live`, (6) `curl -s localhost:8000/health/ready`; **Architecture Overview**: one paragraph + link to `docs/architecture.md`; **Available Commands**: table of `uv run pytest`, `uv run alembic upgrade head`, `python scripts/validate_stack.py`, `docker compose --profile skeletal up`; **Demo Flow** (placeholder for Phase 7+); **Docs**: links to all 5 docs files

**Checkpoint:** `pytest tests/test_route_boundaries.py tests/test_no_secrets.py -v` → 0 failures; `ls docs/` → 5 files; reviewer can identify all project areas in < 5 min.

---

## Phase 5: User Story 3 — Extend the Foundation in Later Phases (P3)

**Goal:** Future implementer can identify correct locations for new routes, services, repositories, infra adapters, scripts, tests, prompts, eval artifacts, data artifacts, and docs updates using the existing structure.

**Independent Test:**
```bash
docker compose --profile skeletal up --wait --exit-code-from model_server
```
Expected: all skeletal services start and exit cleanly (exit code 0); `docker compose up` (no profile) still starts exactly 6 services.

No new tests required for this phase — the directory structure and clean-exit containers ARE the deliverable.

- [X] T037 [P] [US3] Create `model_server/Dockerfile` and `model_server/main.py` — `Dockerfile`: `FROM python:3.11-slim`, `WORKDIR /app`, `COPY main.py .`, `CMD ["python", "main.py"]`; `main.py`: `import logging`, `logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")`, `logging.getLogger(__name__).info("model_server: not implemented")`, `raise SystemExit(0)` — the process must exit with code 0
- [X] T038 [P] [US3] Create `chatbot/Dockerfile` and `chatbot/main.py` — same pattern as T037: `FROM python:3.11-slim`, `WORKDIR /app`, `COPY main.py .`, `CMD ["python", "main.py"]`; `main.py` logs `"chatbot: not implemented"` then `raise SystemExit(0)`
- [X] T039 [P] [US3] Create `widget/Dockerfile` and `widget/main.py` — same pattern: logs `"widget: not implemented"` then exits 0
- [X] T040 [P] [US3] Create `demo/host/Dockerfile` and `demo/host/main.py` — same pattern: logs `"demo_host: not implemented"` then exits 0; note the nested directory `demo/host/` must be created; add `demo/__init__.py` only if needed for Python imports (not needed for a standalone container)
- [X] T041 [US3] Add skeletal services to `docker-compose.yml` — append to the existing `docker-compose.yml` created in T027: add `model_server`, `chatbot`, `widget`, `demo_host` services each with `build: context: ./model_server` (etc.), `profiles: [skeletal]`; verify `docker compose config` shows skeletal services under profiles; verify `docker compose up` (no flag) still resolves to exactly the 6 default services; depends on T027, T037, T038, T039, T040

**Checkpoint:** `docker compose --profile skeletal up` starts 10 services total; skeletal services exit cleanly; `docker compose up` still starts exactly 6; directory tree matches the plan.md source tree.

---

## Phase 6: Polish and Cross-Cutting Concerns

**Purpose:** Final validation that the full foundation passes all tests, the quickstart is runnable end-to-end, and the migration is verified against a fresh database.

- [X] T042 [P] Run full test suite — execute `uv run pytest tests/ -v` and confirm 0 failures across all 6 test files: `test_config.py`, `test_health.py`, `test_errors.py`, `test_import_side_effects.py`, `test_route_boundaries.py`, `test_no_secrets.py`; if any test fails, fix the underlying implementation (do not skip or xfail); record test count and pass/fail summary in a commit message
- [X] T043 [P] Validate default docker compose service count — run `docker compose up --wait -d` followed by `docker compose ps --format json` and assert exactly 6 services appear with status `running` or `exited` (migrations is one-shot); services expected: `backend`, `postgres`, `redis`, `minio`, `vault`, `migrations`; no skeletal services should appear; if count is wrong, fix `docker-compose.yml`
- [X] T044 [P] Validate baseline migration against fresh postgres — spin up `docker compose up postgres --wait -d`, export `DATABASE_URL=postgresql+asyncpg://maintainer:maintainer@localhost:5432/maintainer`, run `uv run alembic upgrade head`, then connect and assert `SELECT count(*) FROM pg_extension WHERE extname='vector'` returns 1; tear down with `docker compose down -v`; if pgvector extension is missing, check that the `pgvector/pgvector:pg16` image is used in `docker-compose.yml`
- [X] T045 Walk through `docs/runbook.md` and verify every command — execute each command in the runbook in order; if any command produces an error or unexpected output, update the runbook to reflect the correct command; ensure the quick-start sequence in `README.md` also works end-to-end; this is the final human-verification gate before Phase 1 is declared complete

---

## Dependencies and Execution Order

```
Phase 1 (Setup: T001–T005)
    No dependencies — start immediately.
    T002–T005 can all run in parallel after T001.

Phase 2 (Foundational: T006–T017)
    Depends on Phase 1 — BLOCKS all user story phases.
    Within Phase 2:
        T006 must complete before T010, T011, T015.
        T007 must complete before T011, T012, T013, T014, T017.
        T008 must complete before T012, T013, T014, T023.
        T009 must complete before T010, T015.
        T010 depends on T006, T009.
        T011–T014 [P] can run in parallel (different files, share only T006–T008 deps).
        T015 depends on T006, T009, T011, T012, T013, T014.
        T016 depends on T006, T010, T015, T017 — no forward dependency on T024. Router registration moved to T024 itself.
        T017 depends on T007, T008.

Phase 3 (US1: T018–T028)
    Depends on Phase 2.
    Tests T018–T022 [P] must be written BEFORE implementation starts.
    T023 depends on T008, T012, T013, T014.
    T024 depends on T008, T023.
    T025–T026 are independent of each other.
    T027 has no code dependencies but is easiest to write last in the phase.
    T028 has no code dependencies.
    T025 must complete before T026.
    T041 (Phase 5) depends on T027.

Phase 4 (US2: T029–T036)
    Depends on Phase 2.
    Can start in PARALLEL with Phase 3 (different files).
    All tasks within Phase 4 are independent of each other [P] except T036.
    T036 (README.md) should be written last to reference accurate commands.

Phase 5 (US3: T037–T041)
    Depends on Phase 2.
    Can start in PARALLEL with Phase 3 and Phase 4.
    T037–T040 are fully parallel.
    T041 depends on T027 (from Phase 3) and T037–T040.

Phase 6 (Polish: T042–T045)
    Depends on ALL story phases (3, 4, 5) being complete.
    T042–T044 [P] can run in parallel.
    T045 runs last (human verification gate).
```

---

## Parallel Execution Examples

**Maximum parallel execution for Phase 2 (after Phase 1 complete):**
```
Worker A: T006 → T010 → T015 → T016
Worker B: T007 (no deps in phase)
Worker C: T008 (no deps in phase)
Worker D: T009 → (unblocks T010 on Worker A)
Worker E: T011 [P] (after T006, T007)
Worker F: T012 [P] (after T007, T008)
Worker G: T013 [P] (after T007, T008)
Worker H: T014 [P] (after T007, T008)
Worker I: T017 [P] (after T007, T008)
```

**Maximum parallel execution across story phases (after Phase 2 complete):**
```
Worker A: T018, T019, T020, T021, T022 (Phase 3 tests) → T023 → T024 → T025 → T026 → T027 → T028
Worker B: T029, T030 (Phase 4 tests) → T031, T032, T033, T034, T035 → T036
Worker C: T037, T038, T039, T040 (Phase 5) → T041 (after T027)
```

---

## Implementation Strategy

1. **Do not skip tests.** The constitution requires tests for all critical behavior. If a task has `[US1]` and appears before its implementation counterpart, write the test first.

2. **Import-time side effects are a hard failure.** Every infra module must follow the pattern: define factory functions (`create_engine(url)`, `create_redis_client(url)`, etc.) at module level but never call them at import time. The lifespan function is the only place that calls these factories.

3. **Vault-resolved fields.** `AppSettings` fields `database_url`, `redis_url`, and MinIO credentials start as `None`. The lifespan function populates them by mutating the settings object after Vault auth succeeds. Any code that accesses these fields outside of lifespan (e.g., during `create_app()`) will get `None` and should not attempt to use them.

4. **Router registration is self-contained.** `app/core/application.py` (T016) does NOT call `app.include_router(...)`. Each route module (e.g., `app/api/routes/health.py`, T024) imports `app` and registers its own router at the bottom of the file. This pattern keeps the app factory free of cross-phase forward dependencies and makes it clear which module owns each route prefix. The `app` singleton is imported from `app.core.application`; Python module caching ensures the same object is mutated everywhere.

4. **Error responses never expose internals.** When writing error handlers and service probes, always catch exceptions and return a safe string message. Never propagate raw exception `str()` output into HTTP responses.

5. **Route handlers are thin.** If a route handler contains more than one `await` call that isn't a dependency injection or a single service call, that logic belongs in `app/services/`.

6. **The `[P]` marker is a signal, not a requirement.** Parallelizable tasks can always be run sequentially. Use `[P]` to identify safe parallelism opportunities when multiple workers are available.

7. **Checkpoint validation.** At the end of each phase's checkpoint, all prior tests must still pass. Do not proceed to Phase 6 if any test file has failures.
