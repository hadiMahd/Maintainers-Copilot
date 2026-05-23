# Research: Production Readiness

## Decision: Use GitHub Actions as the CI provider

**Rationale**: The project has no existing committed CI provider in scope, and
GitHub Actions is the expected default for a GitHub-hosted bootcamp repository.
It can run uv, flake8, black, isort, mypy, pytest, Docker build validation,
compact evals, and Docker Compose smoke checks on Linux runners.

**Alternatives considered**:

- Add another CI provider: rejected because it adds setup burden without a
  project-specific need.
- Only provide local scripts: rejected because the acceptance criteria require a
  CI gate that passes or fails on a clean repo.

## Decision: Use uv for dependency installation in CI and local validation

**Rationale**: The project stack already selected uv. Using the same installer
locally and in CI reduces drift and makes validation commands reproducible.

**Alternatives considered**:

- Use pip directly: rejected because it would create a second dependency path.
- Use poetry or pipenv: rejected because they are not part of the selected
  project stack.

## Decision: Use flake8, black, and isort for lint, format, and import-order checks

**Rationale**: The Phase 10 spec explicitly locks the Python quality toolchain
to flake8 for lint, black for format checks, and isort for import-order checks.
Keeping these tools explicit in CI and local validation makes the release gate
match the accepted spec instead of relying on a substitute tool.

**Alternatives considered**:

- Replace them with a substitute all-in-one linter/formatter: rejected because
  the Phase 10 spec already fixed the required tools and task generation should
  not drift from that contract.
- Skip format checks: rejected because format is an explicit Phase 10 gate.

## Decision: Use pytest for gate and integration tests

**Rationale**: Pytest is the project test runner. It can cover normal tests,
redaction leaks, threshold gates, model artifact hash checks, startup failure
gates, tracing validation, docs completeness, and smoke-test assertions.

**Alternatives considered**:

- Shell-only tests: rejected because structured failure assertions are easier in
  pytest.
- Add a new test framework: rejected because it adds unnecessary complexity.

## Decision: Use mypy for the type-check gate

**Rationale**: The Phase 10 spec explicitly locks type-checking to mypy.
Using mypy in CI and local validation keeps the gate aligned with the accepted
feature contract and avoids ambiguous fallback behavior during task generation.

**Alternatives considered**:

- Skip type-checking: rejected because the project brief explicitly requires it.
- Use another checker or choose later during implementation: rejected because CI
  gate behavior must already be decision-complete and spec-aligned.

## Decision: Use Makefile targets for local gate orchestration

**Rationale**: The Phase 10 spec requires GitHub Actions plus a Makefile so the
same validation gates are easy to run from a clean local checkout. The Makefile
should wrap the underlying `scripts/ci/` commands instead of duplicating gate
logic.

**Alternatives considered**:

- Only expose shell scripts: rejected because the accepted spec requires local
  `make` entry points.
- Put all gate logic directly in Makefile recipes: rejected because reusable
  scripts are easier to test and call from GitHub Actions.

## Decision: Keep CI independent of real paid APIs

**Rationale**: CI should be repeatable for reviewers and should not require
provider credentials. Fake providers, mocks, local fixtures, compact golden sets,
and local artifacts are enough to prove gate behavior for the bootcamp scope.

**Alternatives considered**:

- Run live provider evals in CI: rejected because it makes validation flaky,
  costly, and credential-dependent.
- Skip provider-related checks: rejected because model, RAG, chat, and redaction
  behavior still need regression gates through fakes.

## Decision: Use committed compact golden sets and local artifacts for eval gates

**Rationale**: The final CI must run classifier and RAG evals quickly and
deterministically. Small committed golden sets and local model/index artifacts
provide a stable release gate while larger experiments can remain outside the
main CI path.

**Alternatives considered**:

- Rebuild full datasets and indexes during CI: rejected because it is too slow
  and network-dependent for the final validation gate.
- Use no eval data in CI: rejected because the constitution requires evals as
  release gates.

## Decision: Generate one combined `eval_report.json`

**Rationale**: A single report gives reviewers one place to inspect classifier
metrics, RAG metrics, thresholds, pass/fail decisions, artifact metadata, and
storage details. It also supports final `docs/decisions.md` and
`docs/evals.md`.

**Alternatives considered**:

- Keep separate ad hoc eval outputs only: rejected because final review needs a
  stable combined artifact.
- Store report only in CI logs: rejected because the acceptance criteria require
  storing the report in MinIO or a compatible local path.

## Decision: Store CI eval reports in MinIO

**Rationale**: The project brief requires blob storage for every CI
`eval_report.json`. MinIO is the selected blob store, so CI stores reports there.
Local-compatible filesystem storage remains a dev/test adapter for offline
validation only.

**Alternatives considered**:

- Use a local path as the final CI target: rejected because it weakens the brief
  requirement that blob storage hold every CI report.
- Store reports only as GitHub Actions artifacts: rejected because it bypasses
  the selected MinIO blob store.

## Decision: Diff eval reports against the previous green build

**Rationale**: Thresholds catch absolute failures, while previous-green diffing
catches regressions that remain above minimum thresholds. The comparison uses
the latest successful MinIO-stored report when available and records safe metric
diff metadata in the current report.

**Alternatives considered**:

- Compare only to thresholds: rejected because regressions can slip through when
  thresholds are intentionally conservative.
- Require a previous report for the first run: rejected because bootstrapping CI
  needs one successful stored report.

## Decision: Keep local-compatible report storage only as a dev/test adapter

**Rationale**: Developers need to run validation offline. The same storage
script can target a filesystem adapter locally, but CI must use MinIO.

**Alternatives considered**:

- Require live MinIO for every local developer run: rejected because it makes
  local validation heavier than needed.
- Do not store reports: rejected by the acceptance criteria.

## Decision: Add static secret grep checks for `sk-` and `password`

**Rationale**: Redaction tests cover runtime outputs, but the brief also
requires static grep checks. The gate scans committed files and generated review
artifacts for unsafe `sk-` and password-like patterns with a narrow allowlist for
documented false positives.

**Alternatives considered**:

- Rely only on redaction leak tests: rejected because static files can leak
  secrets without passing through runtime redaction.
- Fail on every textual occurrence without allowlisting: rejected because docs
  may need safe pattern examples.

## Decision: Validate startup failure gates through controlled negative checks

**Rationale**: Vault-unreachable, missing or mismatched model artifacts, tracing
misconfiguration, and disabled/zero eval thresholds must fail closed. Dedicated
startup validation checks can run with controlled bad configuration and assert
that startup refuses to proceed with a clear reason.

**Alternatives considered**:

- Rely on manual review: rejected because startup safety is release-blocking.
- Allow degraded startup: rejected because required secrets and artifacts are
  prerequisites for safe production-shaped behavior.

## Decision: Validate documentation completeness as a gate

**Rationale**: Final README, architecture, decisions, evals, runbook, and
security docs are acceptance criteria. A doc completeness script prevents
missing sections from being overlooked during final polish.

**Alternatives considered**:

- Treat docs as manual only: rejected because documentation is part of
  release-readiness and can be partially machine-checked.
- Generate docs entirely from code: rejected because decisions and limitations
  need explicit human-written context.
