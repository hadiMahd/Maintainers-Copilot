# Feature Specification: Dataset Pipeline

**Feature Branch**: `002-dataset-pipeline`  
**Created**: 2026-05-18  
**Status**: Draft  
**Input**: User description: "Build the dataset pipeline for Maintainer's Copilot."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Fetch Reproducible Raw Issue Data (Priority: P1)

A developer preparing the machine-learning dataset can choose one open-source
repository through configuration, fetch closed issues, enrich them with comments,
and produce a raw dataset file that can be safely regenerated.

**Why this priority**: The later preprocessing, classifier, and RAG phases depend
on a reliable raw source dataset. Without reproducible raw data, no downstream
model or retrieval decision can be defended.

**Independent Test**: Configure a public repository, run the raw issue fetch and
comment enrichment commands, and verify that the raw dataset exists, contains
closed issues from the configured repository, includes required raw fields, and
does not require a committed secret.

**Acceptance Scenarios**:

1. **Given** a configured public repository, **When** the developer fetches closed
   issues, **Then** `data/raw/issues.jsonl` contains closed issue records with
   the required raw fields.
2. **Given** raw issue records with comment references, **When** the developer
   enriches comments, **Then** the raw data includes fetched comments or a safe
   record of unavailable comments.
3. **Given** no optional GitHub token is provided, **When** the developer runs the
   fetch commands, **Then** the pipeline still works within unauthenticated rate
   limits or reports a clear rate-limit failure without exposing secrets.

---

### User Story 2 - Produce Labeled Processed Records (Priority: P2)

A developer or reviewer can transform raw issue data into clean records labeled
as `bug`, `feature`, `docs`, or `question` using a single auditable label mapping
configuration.

**Why this priority**: The classifier phase requires consistent labels and clean
text fields. Label choices must be reviewable and documented before training
begins.

**Independent Test**: Run preprocessing on raw data, inspect the labeled output,
and verify that every processed record contains the required fields, mapped labels
come from configuration, unmapped or ambiguous records are handled consistently,
and the selected repository and mapping decisions are documented.

**Acceptance Scenarios**:

1. **Given** raw issue records and a label mapping configuration, **When** the
   developer preprocesses the data, **Then** `data/processed/issues_labeled.jsonl`
   contains records with the required processed fields.
2. **Given** raw labels that map to project classes, **When** preprocessing runs,
   **Then** labels are mapped only through the configuration file.
3. **Given** raw labels that do not map cleanly, **When** preprocessing runs,
   **Then** the pipeline excludes or reports those records according to the
   documented mapping policy.

---

### User Story 3 - Create Auditable Dataset Splits and Statistics (Priority: P3)

A reviewer and future model/RAG phase can use deterministic train, validation,
test, and held-out evaluation data with statistics that demonstrate split order,
class balance, and leakage controls.

**Why this priority**: Dataset splits become production gates for later model and
RAG decisions. The split policy must be reproducible and defensible before model
training starts.

**Independent Test**: Run the split and reporting commands twice on the same
processed data and verify that outputs are identical, the test set is newer than
training data, class distribution is reported, and held-out evaluation data does
not leak into classifier training.

**Acceptance Scenarios**:

1. **Given** processed labeled records, **When** the developer creates splits,
   **Then** train, validation, and test files are produced deterministically.
2. **Given** split files, **When** the reviewer checks temporal ordering, **Then**
   the test set is strictly newer than the training set.
3. **Given** split files and statistics, **When** the reviewer checks leakage
   controls, **Then** classifier training data is separated from held-out RAG or
   evaluation data.

### Edge Cases

- The configured repository has too few closed issues or too few mapped labels:
  the pipeline reports insufficient data and records the limitation.
- The remote service rate-limits requests: the pipeline fails clearly or resumes
  safely without corrupting existing output.
- Issues have empty titles, empty bodies, deleted comments, missing timestamps, or
  unavailable authors: records are normalized or rejected according to documented
  validation rules.
- An issue has labels from multiple project classes: the mapping policy resolves
  or rejects the record deterministically.
- Comments are paginated, unavailable, or duplicated: enrichment remains
  idempotent and avoids duplicate comment text.
- The pipeline is rerun after partial output exists: outputs are overwritten,
  resumed, or skipped according to a documented safe-rerun policy.
- The optional token is present locally: it is loaded through typed settings and
  never written to data artifacts, logs, reports, or docs.
- Temporal split boundaries create class imbalance: statistics expose the tradeoff
  instead of silently hiding it.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The pipeline MUST select the source repository through
  configuration, not hardcoded script constants.
- **FR-002**: The selected repository MUST be a public open-source repository with
  closed issues suitable for the four project labels.
- **FR-003**: The pipeline MUST fetch closed issue records into
  `data/raw/issues.jsonl`.
- **FR-004**: Raw issue records MUST include repository owner/name, issue number,
  title, body, labels, state, created time, closed time, updated time, author
  association when available, comment count, comment URL or fetched comments, and
  HTML URL.
- **FR-005**: The pipeline MUST enrich or create raw issue data with issue
  comments while preserving a safe record when comments are unavailable.
- **FR-006**: The pipeline MUST preprocess raw issues into
  `data/processed/issues_labeled.jsonl`.
- **FR-007**: Processed records MUST include id, repository, issue number, title,
  body, comments, original labels, mapped label, created time, closed time,
  classifier text, RAG text, and source URL.
- **FR-008**: The only valid mapped labels are `bug`, `feature`, `docs`, and
  `question`.
- **FR-009**: Label mapping MUST live in a configuration file and MUST NOT be
  duplicated as unrelated hardcoded mappings across scripts.
- **FR-010**: The pipeline MUST create deterministic train, validation, and test
  split files from processed records.
- **FR-011**: The test split MUST be strictly newer in time than the training
  split.
- **FR-012**: The split policy MUST attempt to preserve class balance as much as
  practical while honoring temporal ordering.
- **FR-013**: The split policy MUST avoid leakage between classifier training data
  and held-out RAG or evaluation data.
- **FR-014**: The pipeline MUST write dataset statistics to
  `data/processed/dataset_report.json` or a Markdown report.
- **FR-015**: The pipeline MUST record the chosen repository, label mapping
  policy, split policy, limitations, and known data risks in `DECISIONS.md`.
- **FR-016**: The fetch, enrichment, preprocessing, split, and reporting commands
  MUST be idempotent or safe to rerun.
- **FR-017**: Pipeline scripts MUST use typed settings for configuration.
- **FR-018**: A GitHub token MAY be used when present, but it MUST be optional and
  loaded through settings.
- **FR-019**: Scripts, reports, configuration examples, tests, and data artifacts
  MUST NOT contain real secrets.
- **FR-020**: Tests MUST cover label mapping behavior, split determinism, temporal
  split invariants, leakage controls, and required record schemas.
- **FR-021**: This phase MUST NOT train models, build embeddings, implement RAG
  retrieval, or require database persistence beyond any simple foundation already
  available from Phase 1.

### Constitution Alignment *(mandatory)*

- **Phase Scope**: This is `PLAN.md` Phase 2 only. It produces reproducible data
  artifacts and scripts. Model training, embeddings, RAG retrieval, auth, memory,
  chatbot behavior, UI work, and widget work are explicitly out of scope.
- **Architecture Boundaries**: Pipeline scripts may use shared configuration and
  domain validation patterns from the foundation. They must not put workflow logic
  into API routes and must not require database persistence unless the existing
  foundation already makes it simple and clearly scoped.
- **Security And Redaction**: The optional GitHub token is local-only and loaded
  through typed settings. Scripts, logs, reports, docs, and artifacts must not
  emit tokens or other real secrets. Raw public issue text is not secret, but logs
  should avoid dumping full issue bodies or comments unnecessarily.
- **Observability And Errors**: Commands must produce clear progress and failure
  messages, distinguish rate limits from malformed data, and exit non-zero when
  required outputs cannot be produced.
- **Evidence And Evals**: This phase does not evaluate model quality, but it must
  generate dataset statistics and record data decisions in `DECISIONS.md` so later
  classifier and RAG evaluations have traceable inputs.
- **Critical Tests**: Critical tests must cover label mapping, required schemas,
  deterministic splits, temporal ordering, held-out leakage prevention, safe
  reruns where practical, and no committed real secrets.

### Key Entities *(include if feature involves data)*

- **Repository Selection**: Configured public repository owner/name, fetch limits,
  and optional local authentication setting used by the raw data commands.
- **Label Mapping**: Configured mapping from repository labels to the project
  classes `bug`, `feature`, `docs`, and `question`, including the policy for
  unmapped or ambiguous labels.
- **Raw Issue Record**: Source issue data captured before normalization,
  including repository, issue identity, content, labels, timestamps, comments
  metadata, and source URL.
- **Issue Comment**: Comment content and metadata associated with a raw issue,
  used to enrich classifier and RAG text fields.
- **Processed Issue Record**: Clean normalized issue record with mapped label,
  original labels, text prepared for classifier use, text prepared for RAG use,
  and source traceability.
- **Dataset Split**: Deterministic assignment of processed records into train,
  validation, test, and held-out evaluation groups.
- **Dataset Report**: Statistics for record counts, class distribution, split
  distribution, excluded records, split date boundaries, and known limitations.
- **Dataset Decision Record**: Documentation entry describing the chosen
  repository, mapping policy, split policy, limitations, and risks.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A developer can run the raw fetch, comment enrichment,
  preprocessing, split, and reporting commands from a clean local setup and
  produce all required dataset artifacts.
- **SC-002**: 100% of emitted raw and processed records contain the required
  fields for their artifact type.
- **SC-003**: 100% of processed records have exactly one mapped label from `bug`,
  `feature`, `docs`, or `question`.
- **SC-004**: Running the split command twice on unchanged processed input
  produces identical split assignments.
- **SC-005**: The test split has zero records older than or equal to records in
  the training split according to the selected temporal ordering field.
- **SC-006**: The dataset report includes record counts, class counts, split
  counts, excluded-record counts, split date boundaries, and limitations.
- **SC-007**: Automated checks detect zero overlap between classifier training
  records and held-out RAG or evaluation records.
- **SC-008**: Tests for label mapping and split invariants pass without requiring
  a real GitHub token.
- **SC-009**: A repository secret scan or equivalent check finds zero real tokens
  in scripts, configuration examples, reports, docs, and committed test fixtures.

## Assumptions

- The actual repository choice will be made during planning or implementation
  using criteria recorded in `DECISIONS.md`: public repository, enough closed
  issues, useful labels, and acceptable rate-limit behavior.
- JSONL files are the canonical dataset artifacts for this phase because the
  provided PLAN.md acceptance criteria require them.
- The official pipeline is command/script based. Notebooks may be used only for
  exploration and cannot be the reproducible source of truth.
- Public issue text may be stored as local data artifacts, but full bodies and
  comments should not be dumped into routine logs.
- If class balance conflicts with temporal ordering, temporal ordering wins and
  the imbalance is documented in the dataset report.
