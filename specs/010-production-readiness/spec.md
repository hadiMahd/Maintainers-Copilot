# Feature Specification: Production Readiness

**Feature Branch**: `010-production-readiness`  
**Created**: 2026-05-18  
**Status**: Draft  
**Input**: User description: "Phase 10, Build production readiness, observability, security tests, CI gates, and final documentation."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Prove A Clean Repo Is Release-Ready (Priority: P1)

A reviewer can run the project validation workflow on a clean checkout and see a
single reliable result showing that linting, formatting, tests, builds, evals,
security checks, and smoke tests all pass.

**Why this priority**: This is the final release gate. The project is not
review-ready unless repeatable automation proves the core system still works.

**Independent Test**: Run the validation workflow from a clean repository state
and verify every required gate passes and produces inspectable output.

**Acceptance Scenarios**:

1. **Given** a clean repository with required local test fixtures and artifacts,
   **When** the validation workflow runs, **Then** lint, format check,
   type-check, tests,
   Docker build validation, eval gates, redaction leak tests, artifact integrity
   checks, tracing configuration checks, and stack smoke tests all pass.
2. **Given** the workflow finishes successfully, **When** a reviewer inspects
   outputs, **Then** they can find the combined evaluation report and all final
   documentation needed to review setup, architecture, operations, evals, and
   security.

---

### User Story 2 - Fail Fast On Eval Or Threshold Regression (Priority: P2)

A maintainer can trust that classification and retrieval quality cannot silently
regress because committed thresholds are non-zero and every validation run
compares current results against them and against the previous green build.

**Why this priority**: The project constitution treats evals as release gates,
not optional reports.

**Independent Test**: Temporarily set eval thresholds to zero or provide below-
threshold eval results and verify the workflow fails with a clear reason.

**Acceptance Scenarios**:

1. **Given** eval thresholds are set to zero, **When** the validation workflow
   runs, **Then** the workflow fails before treating evals as passing.
2. **Given** classifier results fall below configured threshold, **When** the
   classifier eval gate runs, **Then** the workflow fails and reports the failing
   metric.
3. **Given** RAG results fall below configured threshold, **When** the RAG eval
   gate runs, **Then** the workflow fails and reports the failing metric.
4. **Given** the current combined eval report regresses from the previous green
   build according to configured regression rules, **When** report diffing runs,
   **Then** the workflow fails with a safe comparison summary.

---

### User Story 3 - Prove Security And Startup Failure Gates (Priority: P3)

A reviewer can verify that fake secrets do not leak, model artifacts are
integrity-checked, and required external dependencies fail closed instead of
starting the app in an unsafe state.

**Why this priority**: Secret hygiene, redaction, Vault availability, and model
artifact integrity are constitution-level release blockers.

**Independent Test**: Run targeted security and startup failure checks that
   inject fake secrets, run static secret grep checks, break Vault connectivity,
   misconfigure tracing, disable thresholds, and remove or corrupt a required
   model artifact, then verify the workflow fails cleanly in each case.

**Acceptance Scenarios**:

1. **Given** a fake API key appears in test input, **When** logs, traces, memory,
   and audit outputs are inspected by the leak test, **Then** the raw fake key is
   not present.
2. **Given** Vault is unreachable during required startup validation, **When**
   the app attempts to start, **Then** startup fails with a structured,
   explainable failure.
3. **Given** a required model artifact is missing or its SHA-256 does not match
   the model card, **When** artifact validation runs, **Then** validation fails.
4. **Given** committed eval thresholds are zero or disabled, **When** app startup
   validation runs, **Then** startup refuses to proceed.
5. **Given** tracing is enabled but misconfigured, **When** app startup
   validation runs, **Then** startup refuses to proceed.
6. **Given** unsafe `sk-` or `password` patterns appear in committed or captured
   outputs, **When** static secret grep runs, **Then** the workflow fails.

---

### User Story 4 - Review Final Documentation And Runbook (Priority: P4)

A developer, reviewer, or future maintainer can read final documentation to
understand setup, architecture, commands, decisions, evals, security policy, and
common failure recovery steps.

**Why this priority**: The final project must be defensible and maintainable,
not merely passing automation.

**Independent Test**: Review the documentation set and verify each required
document answers its assigned operational or review question without relying on
unstated context.

**Acceptance Scenarios**:

1. **Given** a new developer reads the README, **When** they follow setup and
   demo instructions, **Then** they can identify the required commands and
   expected results.
2. **Given** a reviewer reads the decisions and eval documentation, **When**
   they check AI and architecture choices, **Then** they can find numeric support
   for classifier, embedding, chunking, retrieval weighting, reranking, memory
   type, and tracing backend choices.
3. **Given** an operator reads the runbook and security docs, **When** they
   encounter common failures or need to review secret handling, **Then** they can
   find clear debugging steps, redaction patterns, and secret policy.

### Edge Cases

- Eval thresholds are missing, zero, negative, malformed, or not loaded.
- Classifier or RAG eval scripts fail to produce parseable results.
- `eval_report.json` is written locally but storage upload or MinIO-compatible
  persistence fails.
- Previous green eval report is unavailable, malformed, or cannot be compared.
- Fake secret values appear in logs, traces, memory, audit records, exception
  details, or test snapshots.
- Model card exists but artifact hash is missing, malformed, stale, or points to
  the wrong artifact.
- Vault is reachable but missing a required secret.
- Tracing is enabled but missing exporter, endpoint, or required identifiers.
- Docker build succeeds but stack smoke test cannot reach the health endpoint.
- A validation gate is skipped accidentally and still reports success.
- Documentation exists but omits required commands, numbers, or failure paths.
- CI environment has no real paid API credentials and must use fakes or mocked
  providers.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The project MUST provide a validation workflow that runs on a clean
  repository state.
- **FR-002**: The validation workflow MUST run lint checks.
- **FR-003**: The validation workflow MUST run format checks.
- **FR-004**: The validation workflow MUST run type-checking.
- **FR-005**: The validation workflow MUST run the test suite.
- **FR-006**: The validation workflow MUST run the classification evaluation.
- **FR-007**: The validation workflow MUST run the RAG evaluation.
- **FR-008**: The validation workflow MUST run a redaction leak test covering
  logs, traces, memory, and audit outputs.
- **FR-009**: The validation workflow MUST run static secret grep checks for
  unsafe `sk-` and `password` patterns.
- **FR-010**: The validation workflow MUST run Docker build validation.
- **FR-011**: The validation workflow MUST run a stack smoke test that starts
  the core stack and reaches a health endpoint.
- **FR-012**: The validation workflow MUST write a combined `eval_report.json`.
- **FR-013**: CI MUST store `eval_report.json` from every run in MinIO; a
  MinIO-compatible local path is allowed only as a dev/test adapter.
- **FR-014**: The validation workflow MUST diff the current `eval_report.json`
  against the previous green build and fail on configured regressions.
- **FR-015**: The validation workflow MUST fail if any eval threshold is zero,
  disabled, missing, negative, or malformed.
- **FR-016**: The validation workflow MUST fail if classifier eval results are
  below the configured threshold.
- **FR-017**: The validation workflow MUST fail if RAG eval results are below the
  configured threshold.
- **FR-018**: The validation workflow MUST fail if a fake API key appears
  unredacted in logs, traces, memory, audit records, or captured outputs.
- **FR-019**: The validation workflow MUST validate that model artifact SHA-256
  values match their model cards.
- **FR-020**: Startup validation MUST prove the app refuses to boot when Vault is
  unreachable or required Vault values cannot be resolved.
- **FR-021**: Startup validation MUST prove the app refuses to boot when a
  required model artifact is missing or hash mismatches.
- **FR-022**: Startup validation MUST prove the app refuses to boot when tracing
  backend configuration is invalid.
- **FR-023**: Startup validation MUST prove the app refuses to boot when
  committed eval thresholds are zero or disabled.
- **FR-024**: The validation workflow MUST validate tracing configuration and
  fail when required tracing settings are invalid.
- **FR-025**: Final documentation MUST include README, ARCH, DECISIONS, RUNBOOK,
  EVALS, and SECURITY documents.
- **FR-026**: README MUST explain setup, architecture overview, common commands,
  and demo flow.
- **FR-027**: DECISIONS MUST include numeric evidence for classifier, embedding,
  chunking, retrieval weighting, reranking, memory type, and tracing backend
  choices.
- **FR-028**: EVALS MUST explain previous-green report diffing and regression
  review.
- **FR-029**: SECURITY MUST explain redaction patterns, static secret grep
  checks, and secret policy.
- **FR-030**: RUNBOOK MUST explain common failure paths and debugging steps.
- **FR-031**: The workflow MUST be able to run without real paid API credentials
  by using fakes, local fixtures, or mocked providers.

### Constitution Alignment *(mandatory)*

- **Phase Scope**: This is `PLAN.md` Phase 10 only. It adds production
  readiness gates, observability validation, security tests, smoke tests, eval
  reporting, and final documentation. It must not add new product features,
  classifier behavior, RAG behavior, chatbot behavior, widget behavior, or new
  infrastructure beyond what is required to validate the completed project.
- **Architecture Boundaries**: Validation and smoke-test code may exercise all
  app layers, but it must not bypass service/repository ownership or introduce
  route-level persistence shortcuts. CI and scripts orchestrate checks; app
  routes remain HTTP-only, services own workflows, repositories own persistence,
  and infra owns external adapters.
- **Security And Redaction**: Fake secrets, startup secrets, logs, traces,
  memory, audit records, model artifacts, and eval reports are security-
  relevant. Redaction leak tests must prove fake secrets do not appear
  unredacted, and startup checks must fail closed when Vault or model artifacts
  are unavailable.
- **Observability And Errors**: The phase must validate tracing configuration,
  request/trace identifiers where relevant, structured errors for startup and
  health failures, and enough smoke-test output to debug a failed run without
  exposing sensitive payloads.
- **Evidence And Evals**: Classification and RAG evals are release gates.
  Thresholds must be non-zero, eval results must be compared to thresholds, and
  the combined report must include enough numbers to support final decisions.
- **Critical Tests**: Critical tests must cover CI gate behavior, threshold
  zeroing failure, below-threshold classifier and RAG failure, fake secret leak
  failure, static grep failure, previous-green report regression, Docker build
  validation, stack smoke health check, Vault failure, missing model artifact
  failure, model hash mismatch, tracing config failure, eval-threshold startup
  refusal, eval report MinIO storage, and required documentation completeness.

### Key Entities *(include if feature involves data)*

- **Validation Workflow**: The full release-readiness run that combines quality,
  test, eval, security, build, smoke, artifact, tracing, and documentation gates.
- **Quality Gate**: A pass/fail check such as lint, format, type-check, tests,
  Docker build, smoke test, redaction leak test, static secret grep, or
  documentation completeness.
- **Evaluation Thresholds**: Non-zero committed limits used to decide whether
  classifier and RAG eval results are acceptable.
- **Evaluation Report**: Combined `eval_report.json` containing classifier and
  RAG results, threshold comparisons, timestamps, and storage metadata.
- **Previous Green Eval Report**: Most recent passing CI eval report used for
  regression diffing.
- **Redaction Leak Probe**: A test input containing fake secret-like values used
  to prove logs, traces, memory, audit records, and captured outputs are safe.
- **Model Artifact Integrity Check**: Verification that required model artifacts
  exist and match SHA-256 values recorded in model cards.
- **Startup Failure Check**: Validation that required Vault access and model
  artifacts, tracing configuration, and eval thresholds fail closed when unsafe.
- **Documentation Set**: README, ARCH, DECISIONS, RUNBOOK, EVALS, and SECURITY
  files required for review and operation.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The validation workflow passes from a clean repository state.
- **SC-002**: The validation workflow fails in 100% of tests where any eval
  threshold is set to zero.
- **SC-003**: The validation workflow fails in 100% of tests where fake API keys
  appear unredacted in logs, traces, memory, audit records, or captured outputs.
- **SC-004**: The validation workflow fails in 100% of tests where classifier
  eval results are below threshold.
- **SC-005**: The validation workflow fails in 100% of tests where RAG eval
  results are below threshold.
- **SC-006**: The smoke test starts the core stack and reaches a health endpoint
  in a documented repeatable command.
- **SC-007**: `eval_report.json` is generated and stored in the configured
  MinIO target for every successful CI validation run.
- **SC-008**: Model artifact hash validation detects missing or mismatched
  artifacts in 100% of targeted failure tests.
- **SC-009**: Startup validation detects Vault-unreachable, missing-artifact,
  hash-mismatch, tracing-misconfiguration, and disabled/zero-threshold failures
  in 100% of targeted failure tests.
- **SC-010**: Final documentation contains all required sections for setup,
  architecture, commands, demo, decisions with numbers, eval methodology,
  security policy, redaction patterns, and runbook failure paths.
- **SC-011**: Previous-green report diffing fails in 100% of targeted regression
  tests.
- **SC-012**: Static secret grep detects unsafe `sk-` and `password` patterns in
  100% of targeted leak fixtures.

## Assumptions

- Previous phases have produced or stubbed the classifier eval, RAG eval,
  redaction, tracing, model artifact, Docker Compose, and smoke-test surfaces
  needed for final validation.
- CI should not require real paid provider credentials; tests use fakes, local
  fixtures, or mocked provider calls.
- MinIO is the required CI eval report storage target. A MinIO-compatible
  filesystem path is acceptable only for local dev/test adapter runs.
- Documentation can reference bootcamp-scope limitations as long as limitations
  are explicit and do not claim unfinished behavior is complete.
- Final CI may run a compact committed golden-set eval rather than a large
  production evaluation dataset.
