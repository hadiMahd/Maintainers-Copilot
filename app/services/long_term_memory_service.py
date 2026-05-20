"""Long-term memory service.

Structured logging: propagate ``request_id`` from middleware and generate
per-operation ``trace_id``.  Pre-persistence redaction must run before
any log, memory write, or audit metadata.  Embedding generation is
offloaded via ``asyncio.to_thread`` to avoid blocking the event loop.
"""

import uuid

import structlog


_log = structlog.get_logger


def _trace_ids(request_id: str | None = None) -> tuple[str, str]:
    rid = request_id or "unknown"
    tid = uuid.uuid4().hex[:12]
    return rid, tid
