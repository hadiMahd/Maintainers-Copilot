"""Authenticated SSE chat orchestration and safe event shaping."""

from __future__ import annotations

import asyncio
import json

import structlog

from app.domain.chat import (
    ChatErrorBody,
    ChatExecutionResult,
    ChatGraphState,
    ChatRequest,
    ChatStreamEvent,
    new_message_id,
)
from app.domain.errors import (
    ChatbotTimeoutError,
    ChatValidationError,
    ContextLimitExceededError,
    LLMUnavailableError,
    MaxToolCallsExceededError,
    RecursionLimitExceededError,
    RequestTooLargeError,
    ToolExecutionFailedError,
    TracingFailedError,
)
from app.infra.redaction import redact_sse_event

_log = structlog.get_logger


class ChatbotService:
    """Validate chat requests, run the graph, and format SSE output."""

    def __init__(
        self,
        *,
        conversation_state_service,
        chatbot_graph_service,
        tracing_service,
        limits,
    ) -> None:
        self._conversation_state_service = conversation_state_service
        self._chatbot_graph_service = chatbot_graph_service
        self._tracing_service = tracing_service
        self._limits = limits

    async def execute_chat(
        self,
        *,
        user_id: str,
        body: ChatRequest,
        request_id: str,
    ) -> ChatExecutionResult:
        """Run a full chat request and return safe SSE events."""
        self._validate_request(body)

        message_id = new_message_id()
        state = await self._conversation_state_service.read_conversation(
            user_id=user_id,
            conversation_id=body.conversation_id,
            request_id=request_id,
        )
        context_messages, trimmed = self._conversation_state_service.shape_context(
            state=state,
            latest_user_message=body.message,
        )
        if (
            sum(len(message.content) for message in context_messages)
            > self._limits.context_size_limit_chars
        ):
            raise ContextLimitExceededError("Chat context exceeds the configured limit")

        trace_handle = await self._tracing_service.start_chat_trace(
            user_id=user_id,
            conversation_id=body.conversation_id,
            message_id=message_id,
            request_id=request_id,
        )
        trace_root = self._tracing_service.to_trace_root(trace_handle)
        warnings = []
        if trimmed:
            warnings.append("Older short-term context was trimmed to fit the configured limit.")
        if state.degraded:
            warnings.append(
                "Short-term conversation state was unavailable; continuing without prior context."
            )

        try:
            graph_state = await asyncio.wait_for(
                self._chatbot_graph_service.run(
                    request_id=request_id,
                    user_id=user_id,
                    conversation_id=body.conversation_id,
                    message_id=message_id,
                    user_message=body.message,
                    context_messages=context_messages,
                    limits=self._limits,
                    trace_handle=trace_handle,
                    trace_root=trace_root,
                    warnings=warnings,
                ),
                timeout=self._limits.total_timeout_seconds,
            )
        except (
            MaxToolCallsExceededError,
            RecursionLimitExceededError,
            LLMUnavailableError,
            ToolExecutionFailedError,
            TracingFailedError,
        ) as exc:
            await self._tracing_service.finish(
                trace_handle,
                "failed",
                {
                    "request_id": request_id,
                    "trace_id": trace_root.trace_id if trace_root else None,
                    "run_id": trace_root.run_id if trace_root else None,
                    "status": "failed",
                    "error_code": exc.error_code,
                },
            )
            return self._error_result(
                request_id=request_id,
                conversation_id=body.conversation_id,
                message_id=message_id,
                trace_id=trace_root.trace_id if trace_root else None,
                run_id=trace_root.run_id if trace_root else None,
                error_code=exc.error_code,
                message=exc.message,
                details=exc.details,
            )
        except asyncio.TimeoutError:
            await self._tracing_service.finish(
                trace_handle,
                "failed",
                {
                    "request_id": request_id,
                    "trace_id": trace_root.trace_id if trace_root else None,
                    "run_id": trace_root.run_id if trace_root else None,
                    "status": "timeout",
                },
            )
            return self._error_result(
                request_id=request_id,
                conversation_id=body.conversation_id,
                message_id=message_id,
                trace_id=trace_root.trace_id if trace_root else None,
                run_id=trace_root.run_id if trace_root else None,
                error_code=ChatbotTimeoutError.error_code,
                message="Chat request exceeded the configured timeout",
                details=None,
            )

        await self._conversation_state_service.append_exchange(
            user_id=user_id,
            conversation_id=body.conversation_id,
            user_message=body.message,
            assistant_message=graph_state.final_response,
            prior_state=state,
            request_id=request_id,
        )
        await self._tracing_service.finish(
            trace_handle,
            (
                "partial"
                if any(result.status == "failed" for result in graph_state.tool_results)
                else "success"
            ),
            {
                "request_id": request_id,
                "trace_id": graph_state.trace_id,
                "run_id": graph_state.run_id,
                "status": "completed",
                "tool_result_count": len(graph_state.tool_results),
            },
        )
        result = ChatExecutionResult(
            request_id=request_id,
            conversation_id=body.conversation_id,
            message_id=message_id,
            trace_id=graph_state.trace_id,
            run_id=graph_state.run_id,
            warnings=graph_state.warnings,
        )
        result.events = self._build_events(graph_state)
        _log().info(
            "chat_completed",
            request_id=request_id,
            trace_id=graph_state.trace_id,
            run_id=graph_state.run_id,
            conversation_id=body.conversation_id,
            message_id=message_id,
            event_count=len(result.events),
        )
        return result

    @staticmethod
    def format_sse(result: ChatExecutionResult):
        """Yield SSE frames for a completed chat execution."""
        for event in result.events:
            payload = event.model_dump(exclude_none=True)
            redacted = redact_sse_event(payload)
            _log().info(
                "chat_sse_event_emitted",
                request_id=result.request_id,
                trace_id=result.trace_id,
                run_id=result.run_id,
                event_type=event.event_type,
                event_payload=redacted,
            )
            yield f"data: {json.dumps(payload)}\n\n"

    def _validate_request(self, body: ChatRequest) -> None:
        if not body.conversation_id.strip() or not body.message.strip():
            raise ChatValidationError("Conversation ID and message must be non-empty")
        body_size = len(body.model_dump_json().encode())
        if body_size > self._limits.request_size_limit_bytes:
            raise RequestTooLargeError(
                "Chat request exceeds the configured size limit",
                details={"request_size_bytes": body_size},
            )

    def _build_events(self, graph_state: ChatGraphState) -> list[ChatStreamEvent]:
        events: list[ChatStreamEvent] = []
        sequence = 0
        for warning in graph_state.warnings:
            events.append(
                ChatStreamEvent(
                    event_type="warning",
                    conversation_id=graph_state.conversation_id,
                    message_id=graph_state.message_id,
                    sequence=sequence,
                    content=warning,
                    trace_id=graph_state.trace_id,
                )
            )
            sequence += 1
        for result in graph_state.tool_results:
            content = (
                f"{result.name} completed"
                if result.status == "success"
                else f"{result.name} failed safely: {result.error.message if result.error else 'unknown error'}"
            )
            events.append(
                ChatStreamEvent(
                    event_type="tool_status",
                    conversation_id=graph_state.conversation_id,
                    message_id=graph_state.message_id,
                    sequence=sequence,
                    content=content,
                    trace_id=graph_state.trace_id,
                )
            )
            sequence += 1
        for chunk in self._split_message(graph_state.final_response):
            events.append(
                ChatStreamEvent(
                    event_type="message_delta",
                    conversation_id=graph_state.conversation_id,
                    message_id=graph_state.message_id,
                    sequence=sequence,
                    content=chunk,
                    trace_id=graph_state.trace_id,
                )
            )
            sequence += 1
        events.append(
            ChatStreamEvent(
                event_type="done",
                conversation_id=graph_state.conversation_id,
                message_id=graph_state.message_id,
                sequence=sequence,
                content="done",
                trace_id=graph_state.trace_id,
            )
        )
        return events

    @staticmethod
    def _split_message(message: str) -> list[str]:
        if not message:
            return [""]
        return [message[index : index + 120] for index in range(0, len(message), 120)]

    @staticmethod
    def _error_result(
        *,
        request_id: str,
        conversation_id: str,
        message_id: str,
        trace_id: str | None,
        run_id: str | None,
        error_code: str,
        message: str,
        details: dict | None,
    ) -> ChatExecutionResult:
        result = ChatExecutionResult(
            request_id=request_id,
            conversation_id=conversation_id,
            message_id=message_id,
            trace_id=trace_id,
            run_id=run_id,
        )
        result.events = [
            ChatStreamEvent(
                event_type="error",
                conversation_id=conversation_id,
                message_id=message_id,
                sequence=0,
                trace_id=trace_id,
                error=ChatErrorBody(
                    code=error_code,
                    message=message,
                    request_id=request_id,
                    trace_id=trace_id,
                    details=details,
                ),
            ),
            ChatStreamEvent(
                event_type="done",
                conversation_id=conversation_id,
                message_id=message_id,
                sequence=1,
                content="done",
                trace_id=trace_id,
            ),
        ]
        return result
