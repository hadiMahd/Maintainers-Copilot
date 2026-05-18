# Research: NER and Summarization Tools

## Decision: Use deterministic rule-based extraction for v1 NER

**Rationale**: The requested entity types are code-shaped patterns that can be
handled explainably with regular expressions and small parser helpers. This keeps
the first version easy to test, avoids model training, and lets reviewers inspect
why an entity was produced.

**Alternatives considered**:
- Custom NER training: rejected because the phase explicitly says not to
  overbuild custom NER training.
- Lightweight pretrained NER model: deferred because general NER models often
  miss code-shaped entities and add runtime/model-loading complexity before it
  is necessary.

## Decision: Omit confidence for deterministic rule matches unless a detector can justify it

**Rationale**: Rule-based matches are deterministic rather than probabilistic.
Returning a fake confidence would make the contract less honest. The response
schema supports optional confidence for future pretrained or heuristic detectors.

**Alternatives considered**:
- Always return `1.0`: rejected because a regex match is not the same as model
  certainty.
- Always return a heuristic score: rejected for v1 because it adds unproven
  semantics.

## Decision: Return best-effort source spans using source field, comment index, start, and end

**Rationale**: The caller needs to trace extracted facts back to issue text.
Character offsets within the submitted title, body, or comment are enough for v1
and are straightforward to test.

**Alternatives considered**:
- No spans: rejected because the spec requires spans when practical.
- Global offsets over concatenated issue text: rejected because callers would
  need extra mapping logic to find the source field.

## Decision: Use deterministic duplicate and conflict handling

**Rationale**: Rule order and de-duplication must be stable so tests and callers
receive reproducible results. Exact duplicate matches with the same type and
span are collapsed. When the same text/span matches multiple meaningful entity
types, the extractor uses a documented priority order unless returning multiple
types is necessary to preserve information.

**Alternatives considered**:
- Return every raw detector match: rejected because duplicate entities make the
  API noisy and harder to consume.
- Pick whichever regex runs fastest: rejected because behavior would be
  implementation-order dependent without documentation.

## Decision: Use bounded input validation before extraction or summarization

**Rationale**: NER can run in-process, but unbounded request text can still cause
latency and memory problems. Summarization providers also have context and cost
limits. The service should reject empty input and apply documented maximum text
limits before work starts.

**Alternatives considered**:
- Accept unlimited text: rejected because it creates avoidable operational risk.
- Silently truncate every request: rejected because callers need to know when
  output may be incomplete.

## Decision: Put summarization behind an async adapter with explicit timeout

**Rationale**: The implementation can support a pretrained summarizer or an
LLM-backed summarizer without putting provider logic in routes. An async adapter
with timeout satisfies the non-blocking constitution rule and makes external
failures predictable.

**Alternatives considered**:
- Synchronous provider call in the route: rejected because it blocks request
  paths and violates architecture boundaries.
- Hard-code one provider in the service: rejected because tests must run without
  secrets and provider availability.

## Decision: Provide a deterministic local summarization fallback

**Rationale**: Automated tests and local demos must work without external
credentials. A simple fallback can produce a bounded extractive summary, key
facts, empty unresolved questions when none are detected, and a conservative next
step when supported by the input.

**Alternatives considered**:
- Fail whenever no external summarizer is configured: rejected because it makes
  the endpoint unusable in test and local development.
- Require a local pretrained summarization model for all runs: rejected because
  it adds model download and startup complexity for a bootcamp phase.

## Decision: Use structured tool errors with safe details

**Rationale**: Later backend and chatbot phases need predictable failure
contracts. Errors should expose stable codes, safe messages, request IDs when
available, and bounded metadata such as input length or timeout seconds without
raw issue text.

**Alternatives considered**:
- Return stack traces or raw exception messages: rejected for security and user
  experience.
- Return plain-text error strings: rejected because callers need stable machine
  behavior.

## Decision: Log tool metadata only, never full payloads

**Rationale**: Issue content may contain secrets, tokens, crash dumps, and
private maintainer context. Logs should record request ID, tool name, outcome,
entity count, summary status, duration, and safe lengths while relying on the
redaction layer for any unavoidable diagnostic strings.

**Alternatives considered**:
- Log full request payloads for debugging: rejected because it violates the
  constitution and acceptance criteria.
- Disable logging for these endpoints: rejected because operators still need
  safe observability.
