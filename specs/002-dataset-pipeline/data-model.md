# Data Model: Dataset Pipeline

## Repository Selection

**Purpose**: Defines the public GitHub repository and fetch behavior used by the
dataset pipeline.

**Fields**:
- `owner`: repository owner.
- `name`: repository name.
- `issues_state`: must be `closed` for this phase.
- `max_issues`: optional local cap for development runs.
- `since`: optional lower timestamp bound.
- `github_token_env`: optional setting name for a local token.
- `output_raw_path`: raw JSONL output path.

**Validation Rules**:
- Owner and name are required.
- Repository must be public and open-source.
- Token is optional and must never be serialized into artifacts.
- Closed issues are the only source records for this phase.

## Label Mapping

**Purpose**: Maps source repository labels to project classes.

**Fields**:
- `bug`: list of source labels mapped to bug.
- `feature`: list of source labels mapped to feature.
- `docs`: list of source labels mapped to docs.
- `question`: list of source labels mapped to question.
- `unmapped_policy`: `exclude` or `report`.
- `ambiguous_policy`: `exclude`, `priority_order`, or `report`.
- `priority_order`: optional ordered class list used only by `priority_order`.

**Validation Rules**:
- Only `bug`, `feature`, `docs`, and `question` are valid target classes.
- A source label should not map to multiple classes unless ambiguous handling is
  documented.
- Unmapped and ambiguous policies must be deterministic.

## Raw Issue Record

**Purpose**: Source issue data captured before normalization.

**Fields**:
- `repo`: repository owner/name.
- `issue_number`: issue number.
- `title`: issue title.
- `body`: issue body or empty string.
- `labels`: list of source label names.
- `state`: issue state.
- `created_at`: creation timestamp.
- `closed_at`: close timestamp.
- `updated_at`: update timestamp.
- `author_association`: optional author association.
- `comments_count`: number of comments reported by the source.
- `comments_url`: comments API URL when available.
- `comments`: optional list of issue comments after enrichment.
- `html_url`: issue source URL.

**Validation Rules**:
- `state` must be `closed`.
- `repo`, `issue_number`, `title`, `created_at`, `closed_at`, and `html_url` are
  required.
- Records must be uniquely identified by `repo` and `issue_number`.
- Missing body or comments normalize to empty strings/lists.

## Issue Comment

**Purpose**: Comment content associated with a raw issue.

**Fields**:
- `id`: comment identifier.
- `body`: comment body or empty string.
- `created_at`: comment creation timestamp.
- `updated_at`: comment update timestamp.
- `author_association`: optional author association.
- `html_url`: optional comment source URL.

**Validation Rules**:
- Duplicate comment identifiers are ignored or reported.
- Missing/deleted bodies normalize to empty strings.
- Comment content must not be logged wholesale during routine runs.

## Processed Issue Record

**Purpose**: Clean normalized record used by classifier and future RAG phases.

**Fields**:
- `id`: stable record identifier.
- `repo`: repository owner/name.
- `issue_number`: issue number.
- `title`: normalized title.
- `body`: normalized body.
- `comments`: normalized comments text or list.
- `labels_original`: original source labels.
- `label_mapped`: one of `bug`, `feature`, `docs`, `question`.
- `created_at`: creation timestamp.
- `closed_at`: close timestamp.
- `text_for_classifier`: text used by classifier training/evaluation.
- `text_for_rag`: text used by future RAG ingestion/evaluation.
- `source_url`: issue source URL.

**Validation Rules**:
- `id` must be stable across reruns for the same source issue.
- `label_mapped` must be exactly one valid project label.
- Text fields must be deterministic for unchanged raw input.
- Source URL must preserve traceability to the original issue.

## Dataset Split

**Purpose**: Deterministic assignment of processed records to downstream uses.

**Fields**:
- `record_id`: processed record identifier.
- `split`: `train`, `validation`, `test`, or `heldout_rag_eval`.
- `ordering_timestamp`: selected split ordering timestamp.
- `label_mapped`: project class.
- `source_url`: traceability URL.

**Validation Rules**:
- Re-running with unchanged input produces identical assignments.
- Test records must be strictly newer than training records.
- Class balance is attempted but cannot override temporal ordering.
- Classifier training records must not overlap held-out RAG/eval records.

## Dataset Report

**Purpose**: Auditable statistics and limitations for the generated dataset.

**Fields**:
- `source_repository`: configured repository.
- `generated_at`: report generation timestamp.
- `raw_count`: raw issue count.
- `processed_count`: processed issue count.
- `excluded_count`: excluded record count.
- `class_counts`: counts per mapped class.
- `split_counts`: counts per split.
- `split_boundaries`: temporal boundaries per split.
- `unmapped_labels`: labels not mapped to project classes.
- `limitations`: known limitations and risks.

**Validation Rules**:
- Counts must match artifact contents.
- Report must include class and split distributions.
- Limitations must mention insufficient data, imbalance, or mapping gaps when
  present.

## Dataset Decision Record

**Purpose**: Durable documentation of data decisions in `DECISIONS.md`.

**Fields**:
- `chosen_repository`: selected public repository and rationale.
- `label_mapping_policy`: mapping and ambiguity behavior.
- `split_policy`: temporal ordering and leakage controls.
- `limitations`: known data risks.
- `alternatives_considered`: rejected repository or mapping alternatives.

**Validation Rules**:
- Must be updated before the phase is considered complete.
- Must reference generated dataset report or equivalent statistics.
