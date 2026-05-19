# Quickstart: NER and Summarization Tools

## Prerequisites

- Phase 1 model-server foundation exists with app factory, lifespan, dependency
  injection, request IDs, structured errors, and safe logging.
- No real provider credentials are required for automated tests.
- Optional external summarization credentials, if used locally, resolve through
  settings/Vault or a test fake and are never committed.

## Run Entity Extraction Tests

Run:

```bash
python -m pytest tests/unit/test_entity_extraction_service.py
```

Expected result: the rule-based extractor detects examples for file paths,
function names, class names, package names, version numbers, error codes, URLs,
stack trace markers, environment names, and command snippets. Duplicate handling
and source spans are deterministic.

## Run Summarization Service Tests

Run:

```bash
python -m pytest tests/unit/test_summarization_service.py
```

Expected result: the summarization service returns summary, key facts,
unresolved questions, and suggested next step when supported. Fake adapter
failure and timeout cases return fallback output or structured tool errors.

## Run Endpoint Contract Tests

Run:

```bash
python -m pytest tests/contract/test_issue_analysis_endpoints.py
```

Expected result: `/ner` and `/summarize` accept title, body, and comments; return
typed responses on success; and return structured errors for invalid input,
adapter unavailability, timeouts, and execution failures.

## Verify Payload-Safe Logging

Run:

```bash
python -m pytest tests/unit/test_issue_analysis_logging.py
```

Expected result: fake secret values and full title/body/comment payloads do not
appear unredacted in logs for success or failure paths.

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
function name, version number, error code, URL, command snippet, and stack trace
marker where detectable.

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

Expected result: the response includes a concise summary, key facts, unresolved
questions, and a suggested maintainer next step when supported by the configured
adapter or fallback.

## Validate Adapter Failure Behavior

Run endpoint tests with the fake summarization adapter configured to fail or
timeout.

Expected result: the model server remains healthy and returns a structured
`summarizer_timeout`, `summarizer_unavailable`, or `tool_execution_failed` error
unless fallback output is configured for that case.

## Update Decisions If Needed

If implementation chooses an external summarization provider or local pretrained
summarizer, update `DECISIONS.md` with:

- adapter name and configuration approach
- timeout and fallback policy
- reason the option is acceptable for bootcamp scope
- limitations, including when fallback summaries are used

Expected result: reviewers can understand why the summarization approach is
simple, bounded, and safe.
