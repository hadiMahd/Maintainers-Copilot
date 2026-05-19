# Quickstart: NER and Summarization Tools

## Prerequisites

- Phase 1 model-server foundation exists with FastAPI app creation, lifespan,
  structured errors, request IDs, and safe logging.
- Phase 3 Vault bootstrap and Azure OpenAI settings flow already exist.
- Automated tests use a fake LangChain summarization adapter and do not require
  real Azure credentials.

## Run Entity Pipeline Tests

Run:

```bash
uv run pytest tests/unit/test_entity_ruler_pipeline.py tests/unit/test_ner_service.py -v
```

Expected result: the spaCy EntityRuler pipeline detects representative file
paths, function names, class names, package names, version numbers, error
codes, URLs, stack-trace markers, environment names, and command snippets with
deterministic ordering and best-effort spans.

## Run Summarization Service Tests

Run:

```bash
uv run pytest tests/unit/test_summarization_service.py tests/unit/test_summarization_adapter.py -v
```

Expected result: the summarization service returns `summary`, `key_facts`,
`unresolved_questions`, and optional `suggested_next_step` on success, and maps
fake-adapter timeout or availability failures to structured tool errors with no
stub summary content.

## Run Endpoint Contract Tests

Run:

```bash
uv run pytest tests/contract/test_issue_analysis_endpoints.py -v
```

Expected result: `/ner` and `/summarize` accept title/body/comments payloads,
return typed responses on success, reject combined payloads over 8,000
characters with validation errors, and return structured 503 responses for
summarizer timeout or unavailability.

## Run Lifecycle And Logging Tests

Run:

```bash
uv run pytest tests/integration/test_issue_analysis_lifecycle.py tests/unit/test_issue_analysis_redaction.py tests/unit/test_issue_analysis_tracing.py tests/test_model_server_route_boundaries.py -v
```

Expected result: the model server initializes the spaCy pipeline and
summarization adapter during lifespan, keeps failures isolated to tool
responses, and never logs full title/body/comment payloads or fake secret
values unredacted.

## Run Full Phase 4 Test Suite

```bash
uv run pytest tests/unit/test_entity_ruler_pipeline.py tests/unit/test_ner_service.py tests/unit/test_summarization_service.py tests/unit/test_summarization_adapter.py tests/unit/test_issue_analysis_redaction.py tests/unit/test_issue_analysis_tracing.py tests/contract/test_issue_analysis_endpoints.py tests/integration/test_issue_analysis_lifecycle.py tests/test_model_server_route_boundaries.py -q
```

Expected: 105 tests pass with no failures.

## Try The NER Endpoint Locally

Start the model server, then call:

```bash
curl -s -X POST http://localhost:8001/ner \
  -H 'Content-Type: application/json' \
  -d '{
    "title": "TypeError in src/app/parser.py",
    "body": "Running pytest -q fails in parse_issue() on Python 3.11 with ERR_PARSER_42. See https://example.test/bug",
    "comments": ["Stack trace includes File \"src/app/parser.py\", line 12, in parse_issue"]
  }'
```

Expected result: the response contains typed entities for the file path,
function name, version number, error code, URL, command snippet, and stack
trace marker where detectable.

## Try The Summarization Endpoint Locally

Call:

```bash
curl -s -X POST http://localhost:8001/summarize \
  -H 'Content-Type: application/json' \
  -d '{
    "title": "Parser fails on Python 3.11",
    "body": "The issue appears after upgrading. The failing command is pytest -q.",
    "comments": [
      "Maintainer asked whether this happens on Python 3.10.",
      "Reporter has not confirmed the Python 3.10 behavior yet."
    ],
    "max_summary_sentences": 3
  }'
```

Expected result: the response includes a concise summary, key facts,
unresolved questions, and a suggested maintainer next step when the Azure
adapter is configured and successful.

## Validate Failure Behavior

Run the endpoint tests with the fake summarization adapter configured to time
out or report unavailable status.

Expected result: the model server stays healthy and `/summarize` returns a
structured `summarizer_timeout`, `summarizer_unavailable`, or
`tool_execution_failed` error. It does not return fallback or stub summary
content.

## Update Decisions If Needed

If implementation changes the Azure deployment name, LangSmith tracing
configuration, or spaCy pattern-set coverage, update `DECISIONS.md` with:

- summarization provider and tracing configuration
- fixed timeout policy (`15` seconds)
- reason for choosing `EntityRuler` over a trained NER model
- known limitations in entity coverage or summary quality
