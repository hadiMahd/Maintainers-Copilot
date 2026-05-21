# Quickstart: Foundation and Architecture Skeleton

## Prerequisites

- Python 3.11 or newer
- uv
- Docker Compose

## Validate The Local Stack

1. Copy the example environment file to a local environment file.
2. Keep only fake/local bootstrap values in the local environment file.
3. Run local stack configuration validation.

Expected result: configuration validation completes without errors and no real
secret values are required.

## Start The Foundation

1. Start the local infrastructure and backend services.
2. Wait for the backend process to start.
3. Call the liveness route.
4. Call the readiness route.

Expected result: liveness confirms the process is alive, and readiness reports
shallow dependency status without expensive work.

## Verify Critical Behavior

Run the test suite for Phase 1 critical behavior:

- configuration loading and missing-value failures
- health endpoint responses
- one structured domain error response
- no heavy work at import time
- no direct persistence or external-system calls in routes
- no real secrets in committed examples or documentation

Expected result: all Phase 1 checks pass without real external credentials.

## Inspect The Architecture

Review the repository structure and docs:

- `app/api` contains HTTP-only routing and dependency wiring.
- `app/services` owns workflow boundaries.
- `app/repositories` owns persistence only.
- `app/domain` owns domain models and domain errors.
- `app/infra` owns external adapters.
- `app/core` owns cross-cutting application setup.
- `docs/`, `DECISIONS.md`, `RUNBOOK.md`, `EVALS.md`, and `SECURITY.md` contain
  skeleton guidance for future phases.

Expected result: the foundation is ready for `/speckit.tasks` and later
implementation without adding future-phase behavior.
