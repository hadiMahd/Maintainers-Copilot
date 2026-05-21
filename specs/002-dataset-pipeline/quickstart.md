# Quickstart: Dataset Pipeline

## Prerequisites

- Phase 1 foundation files are available.
- Local configuration uses fake/local values only.
- Optional GitHub token is available locally only when needed.

## Configure The Dataset Source

1. Choose one public open-source repository with enough closed issues and useful
   labels.
2. Record the repository choice criteria in `DECISIONS.md`.
3. Set repository owner/name, fetch limits, and output paths in dataset
   configuration.
4. Define label mapping into `bug`, `feature`, `docs`, and `question` in one
   mapping config file.

Expected result: repository selection and label mapping are config-driven and
auditable.

## Fetch Raw Issues

Run:

```bash
python scripts/fetch_issues.py
```

Expected result: `data/raw/issues.jsonl` exists and contains closed issues with
required raw fields.

## Enrich Comments

Run:

```bash
python scripts/fetch_issue_comments.py
```

Expected result: raw records are enriched with available comments or safe comment
unavailability details.

## Preprocess Labels And Text

Run:

```bash
python scripts/preprocess_issues.py
```

Expected result: `data/processed/issues_labeled.jsonl` exists and every emitted
record has exactly one mapped project label.

## Create Splits

Run:

```bash
python scripts/make_splits.py
```

Expected result: train, validation, test, and held-out RAG/eval files are
generated deterministically. Test records are strictly newer than training
records, and held-out records do not overlap classifier training records.

## Generate Dataset Report

Run:

```bash
python scripts/dataset_report.py
```

Expected result: `data/processed/dataset_report.json` includes counts,
distributions, split boundaries, excluded records, unmapped labels, and
limitations.

## Validate Critical Behavior

Run the Phase 2 tests:

- label mapping behavior
- required raw and processed schemas
- deterministic split assignments
- temporal split invariant
- held-out leakage prevention
- optional-token behavior without committing secrets

Expected result: tests pass without requiring a real GitHub token.

## Update Decisions

Update `DECISIONS.md` with:

- chosen repository and alternatives considered
- label mapping policy and ambiguous/unmapped behavior
- split policy and temporal ordering field
- dataset report summary
- known limitations and risks

Expected result: future classifier and RAG phases can cite the dataset decisions
and generated report.
