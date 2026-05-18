# Command Contracts: Dataset Pipeline

## Shared Requirements

- Commands run from the repository root.
- Commands use typed settings for repository selection, paths, and optional
  GitHub token.
- Commands fail non-zero when required inputs are missing or outputs cannot be
  produced.
- Commands must not print or write real tokens.
- Commands are idempotent or safe to rerun.

## `python scripts/fetch_issues.py`

**Purpose**: Fetch closed GitHub issues for the configured repository.

**Inputs**:
- Repository selection config.
- Optional local GitHub token via settings.
- Optional fetch limit or timestamp lower bound.

**Output**:
- `data/raw/issues.jsonl`

**Record Contract**:
- One JSON object per issue.
- Includes repository owner/name, issue number, title, body, labels, state,
  created_at, closed_at, updated_at, author association when available, comments
  count, comments URL, and HTML URL.

**Failure Behavior**:
- Rate limits, network errors, malformed responses, and insufficient repository
  config produce clear errors.
- Partial output must not corrupt a previously valid raw dataset.

## `python scripts/fetch_issue_comments.py`

**Purpose**: Enrich raw issue records with comments.

**Inputs**:
- `data/raw/issues.jsonl`
- Repository selection config.
- Optional local GitHub token via settings.

**Output**:
- Enriched raw issue records, either replacing `data/raw/issues.jsonl` safely or
  writing a documented enriched raw file consumed by preprocessing.

**Record Contract**:
- Preserves all raw issue fields.
- Adds or updates `comments` with available comment records.
- Records unavailable comments safely without dropping the issue unexpectedly.

**Failure Behavior**:
- Duplicate, unavailable, deleted, or paginated comments are handled
  deterministically.

## `python scripts/preprocess_issues.py`

**Purpose**: Normalize raw issues and map labels into project classes.

**Inputs**:
- Raw or enriched issue JSONL.
- Label mapping config.

**Output**:
- `data/processed/issues_labeled.jsonl`

**Record Contract**:
- One JSON object per included processed issue.
- Includes id, repo, issue_number, title, body, comments, labels_original,
  label_mapped, created_at, closed_at, text_for_classifier, text_for_rag, and
  source_url.

**Failure Behavior**:
- Unmapped or ambiguous labels follow the documented mapping policy.
- Malformed records are reported and excluded or fail the command according to
  severity.

## `python scripts/make_splits.py`

**Purpose**: Create deterministic dataset splits.

**Inputs**:
- `data/processed/issues_labeled.jsonl`
- Split configuration.

**Outputs**:
- `data/processed/train.jsonl`
- `data/processed/validation.jsonl`
- `data/processed/test.jsonl`
- `data/processed/heldout_rag_eval.jsonl`

**Split Contract**:
- Assignments are deterministic for unchanged input.
- Test records are strictly newer than training records.
- Held-out RAG/eval records do not overlap classifier training records.
- Class balance is attempted and reported but does not override temporal
  ordering.

**Failure Behavior**:
- Insufficient records or impossible split constraints produce clear errors and
  limitations.

## `python scripts/dataset_report.py`

**Purpose**: Generate dataset statistics and limitations.

**Inputs**:
- Raw, processed, and split JSONL artifacts.
- Label mapping config.

**Output**:
- `data/processed/dataset_report.json`

**Report Contract**:
- Includes source repository, raw count, processed count, excluded count, class
  counts, split counts, split date boundaries, unmapped labels, and limitations.

**Failure Behavior**:
- Missing artifacts or count mismatches fail the command clearly.
