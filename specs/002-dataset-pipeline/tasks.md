# Phase 2: Dataset Pipeline — Tasks

## Phase 1: Setup

- [X] T001 Add `httpx>=0.27.0` and `pyyaml>=6.0` to `[project.dependencies]` in `pyproject.toml` — `pyproject.toml`
- [X] T002 [P] Create `config/__init__.py` (empty) and `config/dataset_settings.py` — `DatasetSettings(BaseSettings)` with fields: `repo_owner: str` (required), `repo_name: str` (required), `max_issues: int = 1000`, `github_token: SecretStr | None = None` (pydantic `SecretStr` — automatically masked in `repr()` and logs; use `.get_secret_value()` to access the raw string), `raw_issues_path: str = "data/raw/issues.jsonl"`, `processed_issues_path: str = "data/processed/issues_labeled.jsonl"`, `splits_dir: str = "data/processed/splits"`, `report_path: str = "data/processed/dataset_report.json"`, `label_mapping_path: str = "config/label_mapping.yml"`; `model_config = SettingsConfigDict(env_file=".env", extra="ignore")`; no Vault calls; import `SecretStr` from `pydantic` — `config/__init__.py`, `config/dataset_settings.py`
- [X] T003 [P] Create `config/label_mapping.yml` — YAML with `classes: {bug: [list of source labels], feature: [...], docs: [...], question: [...]}`, `unmapped_policy: exclude`, `ambiguous_policy: first_match`, `priority_order: [bug, feature, docs, question]`; placeholder labels suitable for a common Python OSS repo like `pytorch/pytorch` or `fastapi/fastapi`; NOTE: final repository choice and exact label mapping MUST be updated in `docs/decisions.md` during implementation — `config/label_mapping.yml`

---

## Phase 2: Foundational (Blocking Prerequisites)

- [X] T004 Create `app/infra/github_client.py` — `GitHubClient` class; `__init__(self, token: str | None = None)` stores token (plain string, already extracted via `.get_secret_value()` by caller), does NOT call any network; `async def get_closed_issues(self, owner: str, repo: str, max_issues: int = 1000) -> list[dict]`: uses `httpx.AsyncClient` with `Authorization: Bearer {token}` header when token present; calls `GET https://api.github.com/repos/{owner}/{repo}/issues?state=closed&per_page=100`; follows pagination via `Link` header (look for `rel="next"` URL); stops when `max_issues` reached or no more pages; raises `RuntimeError` with clear safe message for these cases: status 429 → "GitHub API rate limit exceeded"; status 403 → "GitHub API access forbidden (check token or secondary rate limit)"; status 404 → "Repository not found or not public"; status 5xx → "GitHub API server error ({status_code})"; any other non-200 non-paginated → "Unexpected GitHub API response ({status_code})"; timeout=`httpx.Timeout(connect=5.0, read=10.0, write=5.0, pool=5.0)`; `async def get_issue_comments(self, comments_url: str) -> list[dict]`: fetches comment pages via `Link` header pagination; same error handling; MUST NOT log token value; no module-level HTTP calls — `app/infra/github_client.py`
- [X] T005 [P] Extend `tests/conftest.py` with Phase 2 fixtures — `raw_issue_record()` fixture returning a dict with all required raw fields (fake data: `repo="test/repo"`, `issue_number=1`, `title="Test issue"`, `body="Body text"`, `labels=["bug"]`, `state="closed"`, `created_at="2024-01-01T00:00:00Z"`, `closed_at="2024-01-02T00:00:00Z"`, `updated_at="2024-01-02T00:00:00Z"`, `author_association="CONTRIBUTOR"`, `comments_count=2`, `comments_url="https://api.github.com/repos/test/repo/issues/1/comments"`, `comments=[]`, `html_url="https://github.com/test/repo/issues/1"`); `processed_issue_record()` fixture returning a dict with all required processed fields; `sample_label_mapping()` fixture returning a dict loaded from a small inline YAML string — `tests/conftest.py`

---

## Phase 3: User Story 1 — Fetch Reproducible Raw Issue Data (P1)

**Goal:** Configure a public repo, run fetch + comment enrichment, produce `data/raw/issues.jsonl` with all required fields, confirm no token committed.

**Independent Test:**
```bash
# With a mock GitHub server or recorded responses:
uv run python scripts/fetch_issues.py  # → data/raw/issues.jsonl with required fields
uv run python scripts/fetch_issue_comments.py  # → comments enriched
uv run pytest tests/test_schemas.py -v  # passes without real token
```

### Tests (write before implementation):

- [X] T006 [P] [US1] Write `tests/test_schemas.py` — `test_raw_record_has_required_fields(raw_issue_record)`: assert all required fields present and non-None (except optional author_association); `test_raw_record_labels_is_list`: assert labels field is a list; `test_processed_record_has_required_fields(processed_issue_record)`: assert all required processed fields present; `test_processed_record_mapped_label_is_valid`: assert mapped_label is one of `{bug, feature, docs, question}`; `test_processed_record_classifier_text_nonempty`: assert classifier_text is a non-empty string; `test_raw_record_no_token_field`: assert no field named `token`, `github_token`, or `authorization` in raw record dict; use the `raw_issue_record` and `processed_issue_record` fixtures from conftest — `tests/test_schemas.py`

### Implementation:

- [X] T007 [US1] Create `scripts/fetch_issues.py` — `asyncio.run(main())` entry point; loads `DatasetSettings()` from env; instantiates `GitHubClient(settings.github_token.get_secret_value() if settings.github_token else None)`; calls `await client.get_closed_issues(settings.repo_owner, settings.repo_name, settings.max_issues)`; maps each GitHub API response item to a raw issue record dict with all required fields (set `comments=[]` placeholder, `comments_url` from API response); writes records to `settings.raw_issues_path` atomically (write to temp file then `os.replace()`); on `RuntimeError` with "rate-limit" in message: print clear error message to stderr and `sys.exit(1)`; MUST NOT log or print token value; add `if __name__ == "__main__":` guard — `scripts/fetch_issues.py`
- [X] T008 [US1] Create `scripts/fetch_issue_comments.py` — `asyncio.run(main())` entry point; loads `DatasetSettings()`; instantiates `GitHubClient(settings.github_token.get_secret_value() if settings.github_token else None)`; reads existing `settings.raw_issues_path` line by line; for each record, if `comments_count > 0` and `comments_url` present, calls `await client.get_issue_comments(record["comments_url"])`; maps comment response to `{body, author_association, created_at}`; sets `record["comments"] = comments`; writes enriched records back atomically; on rate-limit error: print error to stderr and `sys.exit(1)` without corrupting existing file — `scripts/fetch_issue_comments.py`
- [X] T009 [P] [US1] Update `docs/decisions.md` — add `## Phase 2 Data Source Decision` section: record the chosen public repository (e.g., `fastapi/fastapi` or another suitable repo), selection criteria (enough closed issues, useful bug/feature/docs/question labels, permissive license), and fetch limit (1000); record the fetch library choice (httpx REST v3, not PyGithub); record rate-limit policy (fail fast, exit non-zero) — `docs/decisions.md`

**Checkpoint:** `pytest tests/test_schemas.py` passes; `data/raw/issues.jsonl` produced with correct fields; no token in any file.

---

## Phase 4: User Story 2 — Produce Labeled Processed Records (P2)

**Goal:** Run preprocessing on raw data, produce `data/processed/issues_labeled.jsonl` where every record has exactly one valid label from the configured mapping.

**Independent Test:**
```bash
uv run python scripts/preprocess_issues.py
uv run pytest tests/test_label_mapping.py -v
```

### Tests (write before implementation):

- [X] T010 [P] [US2] Write `tests/test_label_mapping.py` — `test_valid_label_maps_correctly(sample_label_mapping)`: given a raw record with `labels=["bug"]`, assert mapped_label is `"bug"`; `test_unmapped_label_excluded(sample_label_mapping)`: given `labels=["invalid_label"]` and `unmapped_policy=exclude`, assert record is excluded (function returns None or empty); `test_ambiguous_label_uses_first_match(sample_label_mapping)`: given `labels=["bug", "feature"]` and `ambiguous_policy=first_match`, assert mapped_label follows priority_order; `test_empty_labels_excluded(sample_label_mapping)`: given `labels=[]`, assert record is excluded; `test_mapped_label_is_valid_class(sample_label_mapping)`: assert mapped_label is always one of `{bug, feature, docs, question}` or record is excluded; all tests use the `sample_label_mapping` fixture; no real files needed — `tests/test_label_mapping.py`

### Implementation:

- [X] T011 [US2] Create `scripts/preprocess_issues.py` — `main()` entry point (sync is acceptable, no async required); loads `DatasetSettings()`; reads `settings.raw_issues_path`; loads `config/label_mapping.yml` via PyYAML; for each raw record: apply label mapping logic (first match by priority_order for ambiguous, exclude for unmapped, exclude for empty labels); produce processed record with all required fields: `id=f"{repo}#{issue_number}"`, `repo`, `issue_number`, `title`, `body`, `comments` (list of comment bodies kept as list), `original_labels`, `mapped_label`, `created_at`, `closed_at`, `classifier_text=f"{title}\n\n{body}"` (trimmed), `rag_text=f"{title}\n\n{body}\n\n{comments_text}"` (trimmed), `source_url=html_url`; writes to `settings.processed_issues_path` atomically; prints summary: N records processed, M excluded (with reasons) — `scripts/preprocess_issues.py`
- [X] T012 [P] [US2] Update `docs/decisions.md` — add `## Phase 2 Label Mapping Decision` section: record the chosen label mapping (which source labels map to which classes), the chosen repository's actual label names, the unmapped policy (exclude), the ambiguous policy (first_match), and any labels that were excluded and why — `docs/decisions.md`

**Checkpoint:** `pytest tests/test_label_mapping.py` passes; `data/processed/issues_labeled.jsonl` has 100% valid mapped labels; no unmapped labels present.

---

## Phase 5: User Story 3 — Create Auditable Dataset Splits and Statistics (P3)

**Goal:** Run split and reporting commands twice on the same processed data and get identical outputs; test split strictly newer than train; zero overlap between train and held-out.

**Independent Test:**
```bash
uv run python scripts/split_dataset.py
uv run python scripts/split_dataset.py  # second run: identical outputs
uv run python scripts/generate_report.py
uv run pytest tests/test_splits.py -v
```

### Tests (write before implementation):

- [X] T013 [P] [US3] Write `tests/test_splits.py` — create fixtures that produce 100 fake processed records with deterministic `closed_at` timestamps spanning 2020-2024; `test_split_is_deterministic`: run split logic twice, assert output files are byte-identical; `test_test_split_newer_than_train`: assert `min(test_split closed_at) > max(train_split closed_at)`; `test_no_leakage_train_held_out`: assert intersection of train and held_out issue_number sets is empty; `test_no_leakage_train_val_test`: assert no issue_number appears in more than one of train/val/test/held_out; `test_split_covers_all_records`: assert len(train)+len(val)+len(test)+len(held_out) == total processed records; `test_approximate_ratios`: assert len(train)/total is between 0.60 and 0.80 (allowing for rounding with small datasets); all tests use only in-memory fixtures, no file system required (test the split logic function directly, not the script) — `tests/test_splits.py`

### Implementation:

- [X] T014 [US3] Create `scripts/split_dataset.py` — `main()` entry point; loads `DatasetSettings()`; reads `settings.processed_issues_path`; sorts all records by `closed_at` ascending (deterministic); assigns records to splits: last ~5% → held_out, next ~10% → test (strictly newer than train), next ~15% → validation, remaining ~70% → train; writes each split to `settings.splits_dir/{train,validation,test,held_out}.jsonl` atomically (write to temp file then `os.replace()`); creates `settings.splits_dir/` if it does not exist; second run produces identical output because sort is deterministic; after assignment: compute per-split class distribution and log it — if any class is entirely absent from the train split, log a WARNING and add an entry to a `limitations` list that is passed to `generate_report.py` via a sidecar JSON file (e.g., `splits_dir/split_limitations.json`) — `scripts/split_dataset.py`
- [X] T015 [US3] Create `scripts/generate_report.py` — `main()` entry point; loads `DatasetSettings()`; reads train/validation/test/held_out split files; counts: total records per split, class distribution per split, excluded record count (total raw minus total processed), split date boundaries (`min_date`/`max_date` per split); loads `split_limitations.json` from `splits_dir` if it exists (written by T014) and merges its entries into the `limitations` list; writes `settings.report_path` atomically (write to temp file then `os.replace()`) as JSON with fields: `total_raw`, `total_processed`, `total_excluded`, `splits: {train: {count, class_counts, min_date, max_date}, validation: ..., test: ..., held_out: ...}`, `limitations: [...]` — `scripts/generate_report.py`
- [X] T016 [P] [US3] Update `docs/decisions.md` — add `## Phase 2 Split Policy Decision` section: record the 70/15/10/5 ratios, the temporal ordering rule, why temporal ordering takes precedence over balance, and any class imbalance observed in the produced splits — `docs/decisions.md`

**Checkpoint:** `pytest tests/test_splits.py` passes; both split commands produce identical output on second run; `dataset_report.json` has all required fields.

---

## Phase 6: Polish and Cross-Cutting Concerns

- [X] T017 [P] Extend `tests/test_no_secrets.py` — add `test_label_mapping_yml_no_secrets`: read `config/label_mapping.yml` and assert no token/password/key patterns; add `test_dataset_settings_token_not_logged`: mock a `DatasetSettings` with a fake token and assert `repr(settings)` does not include the token value (pydantic-settings masks secrets — verify the field is declared with `SecretStr` or the repr is safe) — `tests/test_no_secrets.py`
- [X] T018 [P] Walk through `docs/quickstart.md` — verify every command produces the expected output; update any path or command that changed during implementation — `docs/quickstart.md`
- [X] T019 Run the full test suite — `uv run pytest tests/test_schemas.py tests/test_label_mapping.py tests/test_splits.py tests/test_no_secrets.py -v` and confirm 0 failures; if any test fails, fix the underlying implementation before marking complete — `tests/`

---

## Dependencies and Execution Order

```
Phase 1 (Setup: T001–T003): No dependencies — can start immediately. T002–T003 are [P].

Phase 2 (Foundational: T004–T005): Depends on Phase 1.
  T004 (github_client.py) must complete before T007 and T008.
  T005 (conftest fixtures) must complete before T006, T010, T013.

Phase 3 (US1: T006–T009): Depends on Phase 2.
  T006 (schemas test) before T007 and T008 (scripts).
  T007 before T008 (comments enrich relies on raw issues file format).
  T009 [P] can run alongside T006–T008.

Phase 4 (US2: T010–T012): Depends on Phase 2 and Phase 3.
  T010 (label mapping test) before T011 (preprocess script).
  T012 [P] alongside T010–T011.

Phase 5 (US3: T013–T016): Depends on Phase 4.
  T013 (splits test) before T014 (split script).
  T014 before T015 (report reads split files).
  T016 [P] alongside T013–T015.

Phase 6 (Polish: T017–T019): Depends on all story phases.
  T017–T018 [P] can run in parallel.
  T019 runs last.
```

## Implementation Strategy

1. Complete Setup (T001–T003) + Foundational (T004–T005)
2. Write tests/test_schemas.py (T006), ensure they fail, then implement fetch scripts (T007–T008) → MVP: raw data pipeline working
3. Write tests/test_label_mapping.py (T010), ensure they fail, then implement preprocess (T011) → labeled data ready
4. Write tests/test_splits.py (T013), ensure they fail, then implement split + report (T014–T015) → complete pipeline
5. Polish (T017–T019)

## Notes

- No real GitHub token is required for any test — all API calls are mocked with httpx fixtures or inline fake records
- `config/label_mapping.yml` must be updated with the actual chosen repository's label names before running the real fetch; the placeholder labels in T003 are for tests only
- `data/raw/` and `data/processed/` are gitignored — never commit real issue data
- Scripts run with `uv run python scripts/<name>.py`; each script loads settings from environment variables (copy `.env.example` → `.env` and set `REPO_OWNER`, `REPO_NAME`, etc.)
