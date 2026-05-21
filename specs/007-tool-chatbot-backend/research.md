# Research: Single Tool-Calling Chatbot Backend

## Decision: Use LangGraph only as a thin single-LLM tool loop

**Rationale**: LangGraph can make the LLM/tool loop explicit, observable, and
recoverable through state nodes, conditional routing, recursion limits, and
streaming. The graph remains one assistant: one primary LLM node decides whether
to call tools, and supporting nodes execute tools, handle timeout/error cases,
record traces, and format the final response.

**Alternatives considered**:
- No graph wrapper: simpler, but harder to make recursion/error recovery and
  tracing explicit.
- Multi-agent LangGraph workflow: rejected because the constitution and user
  instruction explicitly prohibit planner, researcher, critic, memory, router,
  or specialist agents.

## Decision: Use one primary LLM node and simple support nodes

**Rationale**: A single primary LLM node preserves the single-assistant behavior.
Support nodes are implementation structure only: tool execution, timeout/error
handling, tracing, and final formatting. They do not make independent planning
or model decisions.

**Alternatives considered**:
- Separate planner/router node: rejected because it creates an additional agent
  role.
- Separate critic or verifier node: rejected because Phase 7 is not a
  multi-agent review system.

## Decision: Use runtime recursion limits plus project max tool-call limit

**Rationale**: LangGraph supports runtime recursion limits for graph executions.
The project also needs an explicit max tool-call count because recursion steps
and tool calls are related but not identical. Both limits give predictable cost
and failure behavior.

**Alternatives considered**:
- Recursion limit only: rejected because multiple graph steps may not map cleanly
  to tool-call policy.
- Tool-call count only: rejected because graph-level runaway behavior should
  still be bounded.

## Decision: Use total chatbot timeout in addition to node/tool timeouts

**Rationale**: Node/tool timeouts protect individual operations, but the user
experience requires a full-response cap. A total timeout lets the service stop
the graph and return a bounded partial response.

**Alternatives considered**:
- Tool timeouts only: rejected because repeated valid tool calls can still exceed
  the total user-facing budget.
- No timeout on streaming requests: rejected because streams can hang and consume
  resources.

## Decision: Keep provider-specific LLM code in an infra adapter

**Rationale**: Services should work against a project-owned tool-calling LLM
interface. Provider-specific request formats, streaming details, credentials,
and retry behavior belong in infra so the service layer remains testable and
provider-neutral.

**Alternatives considered**:
- Call provider SDKs directly from chat services: rejected because it couples
  workflow behavior to vendor-specific code.
- Put provider calls in routes: rejected because routes must remain thin.

## Decision: Store prompts as version-controlled files

**Rationale**: Prompt files under `prompts/` make behavior reviewable, diffable,
and aligned with future evaluation or audit needs. They also separate prompt text
from service code.

**Alternatives considered**:
- Hard-code prompts in Python constants: rejected because behavior changes are
  harder to review.
- Fetch prompts dynamically from an external service: rejected because this phase
  needs local reproducibility and no new infrastructure.

## Decision: Treat RAG retrieved documents as untrusted context

**Rationale**: Retrieved documents can contain prompt injection text or outdated
instructions. The chatbot must treat retrieved text as evidence only and never
allow it to override system/developer instructions or tool policy.

**Alternatives considered**:
- Insert retrieved text without boundaries: rejected because it exposes prompt
  injection risk.
- Exclude RAG from chat: rejected because Phase 7 requires a RAG tool.

## Decision: Gate write_memory on explicit user intent

**Rationale**: Long-term memory is persistent and sensitive. The chatbot may call
write_memory only when the user explicitly asks it to remember something. This
preserves the Phase 6 no-auto-write rule.

**Alternatives considered**:
- Let the LLM decide implicitly based on inferred usefulness: rejected because it
  creates hidden long-term memory writes.
- Disable write_memory in chat: rejected because Phase 7 requires the tool when
  intent is explicit.

## Decision: Return partial answers on tool failures

**Rationale**: A failed classifier, summarizer, RAG, or memory tool should not
turn the whole chat request into a 500 if the assistant can still provide safe
information. Tool failures become structured tool results that the LLM or final
formatter can explain safely.

**Alternatives considered**:
- Bubble every tool failure to the API boundary: rejected because acceptance
  criteria require graceful recovery.
- Hide all failures from the user: rejected because users need to know when a
  capability was unavailable.

## Decision: Use LangSmith tracing with fake tracing adapters in tests

**Rationale**: Earlier LLM phases already use LangSmith, and the Phase 7 spec
requires LangSmith run IDs for log correlation. Keeping LangSmith behind an
infra tracing adapter preserves service-layer neutrality while giving reviewers
a concrete trace tree for successful and failed chat paths when credentials are
configured. Automated tests use a fake tracing adapter so CI does not require
external tracing credentials.

**Alternatives considered**:
- Log-only observability: rejected because the brief requires a trace UI.
- Local Jaeger or Tempo: rejected because the spec standardizes on LangSmith and
  explicitly avoids adding a Jaeger/Tempo service to the local stack.
- Hosted tracing only with no fake seam: rejected because CI review should not
  require external credentials.

## Decision: Snapshot RAG retrieved chunks after RAG tool calls

**Rationale**: The brief requires per-conversation retrieved-chunk snapshots for
recent conversations. The chatbot calls the Phase 5 snapshot service after RAG
tool use so trace/log review can reference redacted evidence without storing raw
chunks in chat telemetry.

**Alternatives considered**:
- Store full retrieved chunks in chat state: rejected because source text may be
  sensitive and large.
- Skip snapshots and rely only on spans: rejected because the brief requires
  stored retrieved-chunk snapshots.

## Sources

- LangGraph Graph API: https://docs.langchain.com/oss/python/langgraph/graph-api
- LangGraph fault tolerance: https://docs.langchain.com/oss/python/langgraph/fault-tolerance
- LangGraph graph usage and recursion limits: https://docs.langchain.com/oss/python/langgraph/use-graph-api
- LangGraph tool node reference: https://reference.langchain.com/python/langgraph/agents/
