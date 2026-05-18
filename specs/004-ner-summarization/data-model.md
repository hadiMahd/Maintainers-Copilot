# Data Model: NER and Summarization Tools

## Issue Analysis Request

**Purpose**: Shared issue-thread input accepted by NER and summarization tools.

**Fields**:
- `title`: issue title text.
- `body`: issue body text.
- `comments`: ordered list of issue comment text.

**Validation Rules**:
- At least one of `title`, `body`, or `comments` must contain non-whitespace
  text.
- Empty or whitespace-only comments are ignored deterministically.
- Duplicate comments are ignored only when exact duplicate handling is enabled
  by the service policy.
- Request text must stay within the documented endpoint limit; oversized input
  returns a structured validation error or documented truncation warning.
- Raw request text is not logged wholesale.

## Entity Type

**Purpose**: Stable category for code-shaped entities.

**Values**:
- `file_path`
- `function_name`
- `class_name`
- `package_name`
- `version_number`
- `error_code`
- `url`
- `stack_trace_marker`
- `environment_name`
- `command_snippet`

**Validation Rules**:
- Returned entity types must be one of the supported values.
- Detector priority and conflict behavior must be deterministic.

## Source Span

**Purpose**: Best-effort trace to where an entity was found.

**Fields**:
- `source_field`: `title`, `body`, or `comments`.
- `comment_index`: zero-based comment index when `source_field` is `comments`.
- `start`: zero-based start character offset within the source field.
- `end`: exclusive end character offset within the source field.

**Validation Rules**:
- `start` must be greater than or equal to zero.
- `end` must be greater than `start`.
- `comment_index` is present only for comment spans.
- Spans are omitted when the extractor cannot identify reliable offsets.

## Extracted Entity

**Purpose**: One detected code-shaped entity.

**Fields**:
- `text`: matched entity text.
- `type`: supported entity type.
- `confidence`: optional confidence value when the extraction method can justify
  it.
- `span`: optional source span.
- `source_field`: source field shorthand for callers that do not inspect spans.

**Validation Rules**:
- `text` must be non-empty after trimming.
- `type` must be a supported entity type.
- `confidence`, when present, must be between `0` and `1`.
- Duplicate entities with the same `text`, `type`, and `span` are collapsed.

## NER Response

**Purpose**: Structured response from the `/ner` tool.

**Fields**:
- `entities`: ordered list of extracted entities.
- `request_id`: request identifier when available.
- `warnings`: optional safe warnings such as truncation or unavailable spans.

**Validation Rules**:
- The response always contains `entities`, even when no entities are detected.
- Entity order is deterministic by source order and detector priority.
- Warnings must not include raw issue payloads.

## Summarization Request

**Purpose**: Issue thread content submitted to `/summarize`.

**Fields**:
- `title`: issue title text.
- `body`: issue body text.
- `comments`: ordered list of issue comment text.
- `max_summary_sentences`: optional caller hint for concise output.

**Validation Rules**:
- At least one text field must be non-empty.
- Caller hints must stay within documented bounds.
- Oversized text follows the documented limit, truncation, or structured error
  policy.

## Issue Summary

**Purpose**: Structured summary of a long issue thread.

**Fields**:
- `summary`: concise issue summary.
- `key_facts`: list of maintainer-relevant facts.
- `unresolved_questions`: list of unanswered or uncertain questions.
- `suggested_next_step`: optional suggested maintainer action.
- `limitations`: optional safe limitations such as fallback mode or truncation.
- `request_id`: request identifier when available.

**Validation Rules**:
- `summary` is required for successful responses.
- `key_facts` and `unresolved_questions` are always lists.
- `suggested_next_step` may be omitted or null when unsupported.
- Output must not reveal provider secrets or internal exception details.

## Tool Error

**Purpose**: Stable failure shape returned by issue-analysis tools.

**Fields**:
- `code`: stable machine-readable error code.
- `message`: safe human-readable error summary.
- `request_id`: request identifier when available.
- `details`: optional safe metadata.

**Validation Rules**:
- Error details must not include full raw title, body, comments, prompts,
  provider responses, credentials, or stack traces.
- Known validation, timeout, unavailable-adapter, and execution failures map to
  stable codes.

## Summarization Adapter

**Purpose**: Optional external or local summarization provider behind the
summarization service.

**Fields**:
- `name`: adapter name, such as `fallback`, `local`, or provider identifier.
- `timeout_seconds`: configured request timeout.
- `configured`: whether the adapter is available for runtime use.
- `supports_next_step`: whether the adapter can produce next-step guidance.

**Validation Rules**:
- Adapter configuration must not contain secrets in logs or reports.
- External calls must use async clients with explicit timeouts.
- Tests must be able to use fake or fallback adapters without real credentials.
