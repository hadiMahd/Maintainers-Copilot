# Research: Dataset Pipeline

## Decision: Use script-based pipeline commands as the official reproducible path

**Rationale**: The feature exists to create reproducible data artifacts. Scripts
are easy to run locally and in CI, can be tested directly, and keep the pipeline
outside request paths. Notebooks may exist for exploration, but they are not the
source of truth.

**Alternatives considered**:
- Notebooks as the official pipeline: rejected because reruns and CI validation
  are harder to control.
- API endpoints for ingestion: rejected because this phase does not need runtime
  ingestion and must avoid request-path long-running work.

## Decision: Store raw and processed records as JSONL

**Rationale**: JSONL supports appendable and streamable records, is simple to
inspect, works well with tests, and is explicitly required by the Phase 2
acceptance criteria.

**Alternatives considered**:
- CSV: rejected because nested labels and comments become awkward.
- Database persistence: rejected because Phase 2 does not require it and file
  artifacts are easier to reproduce and review.

## Decision: Use a YAML label mapping file with a documented ambiguity policy

**Rationale**: YAML is readable for reviewers and avoids scattering label logic
across scripts. The mapping must include how to handle unmapped and multi-class
labels so preprocessing remains deterministic.

**Alternatives considered**:
- Hardcoded mappings in preprocessing: rejected because it is harder to audit and
  violates the spec.
- Inferring labels dynamically: rejected because it would make dataset contents
  less reproducible.

## Decision: Use typed settings for repository selection and optional GitHub token

**Rationale**: The chosen repository, fetch limits, output paths, and optional
token need one validated configuration surface. Tokens must remain local-only and
must not appear in artifacts.

**Alternatives considered**:
- Command flags only: rejected because repeated runs need stable configuration.
- Direct environment reads in scripts: rejected because scattered configuration
  is harder to audit and conflicts with the constitution.

## Decision: Use httpx with explicit timeouts and pagination for GitHub access

**Rationale**: Fetching issues and comments requires HTTP calls that can time out,
rate-limit, and paginate. A single async-capable HTTP library with explicit
timeouts and pagination handling gives predictable failures and clean tests.

**Alternatives considered**:
- Unbounded HTTP calls: rejected because hangs make the pipeline unreliable.
- Manual browser exports: rejected because the pipeline must be reproducible.

## Decision: Split deterministically by temporal ordering, then report balance

**Rationale**: The test set must be strictly newer than training data. Temporal
ordering prevents future information from leaking backward into model selection.
Class balance is attempted within that constraint and reported when imperfect.

**Alternatives considered**:
- Random stratified split: rejected because it can violate the strict newer test
  requirement.
- Perfect class balance first: rejected because it can introduce temporal leakage.

## Decision: Reserve a held-out RAG/evaluation slice outside classifier training

**Rationale**: Future RAG and eval phases need records that were not used for
classifier training. A distinct held-out slice protects against leakage and lets
later phases build golden sets from traceable source records.

**Alternatives considered**:
- Reusing classifier training records for RAG evals: rejected because it weakens
  later evaluation credibility.
- Deferring held-out selection entirely: rejected because the dataset phase is the
  right place to enforce leakage boundaries.

## Decision: Record repository, label mapping, split policy, and limitations in DECISIONS.md

**Rationale**: The data source and split policy directly affect future metrics.
Reviewers need a durable record of why the repository was selected, how labels
were mapped, what was excluded, and what limitations remain.

**Alternatives considered**:
- Keeping decisions only in comments or reports: rejected because key project
  decisions must be centralized and traceable.
