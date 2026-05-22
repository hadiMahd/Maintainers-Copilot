"""Typed tool registry, validation, timeout handling, and safe results."""

from __future__ import annotations

import asyncio
import json
import time

from pydantic import BaseModel, ValidationError

from app.domain.chat_tools import (
    LLMToolCall,
    MemoryWriteIntent,
    RAGToolClientResponse,
    RAGToolResult,
    ToolDefinition,
    ToolExecutionError,
    ToolExecutionResult,
    WriteMemoryOutput,
    build_default_tool_definitions,
)
from app.infra.redaction import redact_tool_payload


class ToolExecutionService:
    """Validate and execute supported chat tools."""

    def __init__(
        self,
        *,
        model_server_tools,
        rag_tool_client,
        memory_tool_client,
        rag_snapshot_coordinator,
        per_tool_timeout_seconds: int,
        definitions: dict[str, ToolDefinition] | None = None,
    ) -> None:
        self._model_server_tools = model_server_tools
        self._rag_tool_client = rag_tool_client
        self._memory_tool_client = memory_tool_client
        self._rag_snapshot_coordinator = rag_snapshot_coordinator
        self._per_tool_timeout_seconds = per_tool_timeout_seconds
        self._definitions = definitions or build_default_tool_definitions(per_tool_timeout_seconds)
        self._write_memory_called = False

    def registered_tools(self) -> list[ToolDefinition]:
        """Return the supported tool registry."""
        return list(self._definitions.values())

    async def execute(
        self,
        *,
        tool_call: LLMToolCall,
        user_id: str,
        conversation_id: str,
        message_id: str,
        request_id: str,
        trace_id: str | None,
        memory_intent: MemoryWriteIntent,
    ) -> ToolExecutionResult:
        """Execute one requested tool and always return a safe structured result."""
        started = time.monotonic()
        definition = self._definitions.get(tool_call.name)
        if definition is None:
            return self._failed_result(
                tool_call=tool_call,
                code="unknown_tool",
                message="Requested tool is not registered",
                request_id=request_id,
                trace_id=trace_id,
                duration_ms=self._duration_ms(started),
            )

        redacted_input = redact_tool_payload(tool_call.arguments)
        try:
            parsed_input = definition.input_model.model_validate(tool_call.arguments)
        except ValidationError as exc:
            return self._failed_result(
                tool_call=tool_call,
                code="invalid_tool_input",
                message="Tool input validation failed",
                request_id=request_id,
                trace_id=trace_id,
                details={"errors": exc.errors()},
                duration_ms=self._duration_ms(started),
                redacted_input=redacted_input,
            )

        if definition.requires_explicit_intent and not memory_intent.present:
            return self._failed_result(
                tool_call=tool_call,
                code="tool_execution_failed",
                message="Explicit remember intent is required for write_memory",
                request_id=request_id,
                trace_id=trace_id,
                duration_ms=self._duration_ms(started),
                redacted_input=redacted_input,
            )

        if tool_call.name == "write_memory" and self._write_memory_called:
            return self._failed_result(
                tool_call=tool_call,
                code="tool_execution_failed",
                message="write_memory is limited to one call per request",
                request_id=request_id,
                trace_id=trace_id,
                duration_ms=self._duration_ms(started),
                redacted_input=redacted_input,
            )

        try:
            raw_output = await asyncio.wait_for(
                self._execute_definition(
                    definition.name,
                    parsed_input,
                    user_id=user_id,
                    conversation_id=conversation_id,
                    message_id=message_id,
                    request_id=request_id,
                    trace_id=trace_id,
                ),
                timeout=definition.timeout_seconds,
            )
        except asyncio.TimeoutError:
            return self._failed_result(
                tool_call=tool_call,
                code="tool_timeout",
                message="Tool execution timed out",
                request_id=request_id,
                trace_id=trace_id,
                duration_ms=self._duration_ms(started),
                redacted_input=redacted_input,
            )
        except Exception as exc:
            return self._failed_result(
                tool_call=tool_call,
                code="tool_execution_failed",
                message="Tool execution failed",
                request_id=request_id,
                trace_id=trace_id,
                details={"reason": type(exc).__name__},
                duration_ms=self._duration_ms(started),
                redacted_input=redacted_input,
            )

        try:
            output_model = definition.output_model.model_validate(self._as_payload(raw_output))
        except ValidationError as exc:
            return self._failed_result(
                tool_call=tool_call,
                code="invalid_tool_output",
                message="Tool output validation failed",
                request_id=request_id,
                trace_id=trace_id,
                details={"errors": exc.errors()},
                duration_ms=self._duration_ms(started),
                redacted_input=redacted_input,
            )

        raw_payload = self._as_payload(output_model)
        if len(json.dumps(raw_payload)) > 8_000:
            return self._failed_result(
                tool_call=tool_call,
                code="tool_output_too_large",
                message="Tool output exceeded the safe size limit",
                request_id=request_id,
                trace_id=trace_id,
                duration_ms=self._duration_ms(started),
                redacted_input=redacted_input,
            )

        return ToolExecutionResult(
            tool_call_id=tool_call.tool_call_id,
            name=tool_call.name,
            status="success",
            output=raw_payload,
            error=None,
            redacted_input=redacted_input,
            redacted_output=redact_tool_payload(raw_payload),
            duration_ms=self._duration_ms(started),
        )

    async def _execute_definition(
        self,
        tool_name: str,
        parsed_input: BaseModel,
        *,
        user_id: str,
        conversation_id: str,
        message_id: str,
        request_id: str,
        trace_id: str | None,
    ) -> BaseModel:
        if tool_name == "classify_issue":
            return await self._model_server_tools.classify_issue(
                parsed_input,
                request_id=request_id,
                trace_id=trace_id,
            )
        if tool_name == "extract_entities":
            return await self._model_server_tools.extract_entities(
                parsed_input,
                request_id=request_id,
                trace_id=trace_id,
            )
        if tool_name == "summarize_issue":
            return await self._model_server_tools.summarize_issue(
                parsed_input,
                request_id=request_id,
                trace_id=trace_id,
            )
        if tool_name == "answer_project_question":
            rag_result = await self._rag_tool_client.answer_project_question(
                parsed_input,
                request_id=request_id,
                trace_id=trace_id,
            )
            snapshot_ref = await self._rag_snapshot_coordinator.store_snapshot(
                conversation_id=conversation_id,
                message_id=message_id,
                question=parsed_input.question,
                rag_result=rag_result,
                trace_id=trace_id,
            )
            return RAGToolResult(
                answer=rag_result.answer,
                supporting_sources=rag_result.supporting_sources,
                limitations=rag_result.limitations,
                retrieval_trace_id=snapshot_ref.retrieval_trace_id,
                snapshot_id=snapshot_ref.snapshot_id,
                untrusted_context_used=True,
            )
        if tool_name == "recall_memory":
            return await self._memory_tool_client.recall_memory(
                user_id,
                conversation_id,
                parsed_input,
                request_id=request_id,
            )
        if tool_name == "write_memory":
            self._write_memory_called = True
            return await self._memory_tool_client.write_memory(
                user_id,
                parsed_input,
                request_id=request_id,
            )
        raise RuntimeError(f"Unknown tool requested: {tool_name}")

    @staticmethod
    def _as_payload(model_or_payload) -> dict:
        if isinstance(model_or_payload, BaseModel):
            return model_or_payload.model_dump(exclude_none=True)
        if isinstance(model_or_payload, RAGToolClientResponse):
            return model_or_payload.model_dump(exclude_none=True)
        if isinstance(model_or_payload, WriteMemoryOutput):
            return model_or_payload.model_dump(exclude_none=True)
        return dict(model_or_payload)

    @staticmethod
    def _failed_result(
        *,
        tool_call: LLMToolCall,
        code: str,
        message: str,
        request_id: str,
        trace_id: str | None,
        duration_ms: int,
        details: dict | None = None,
        redacted_input: dict | None = None,
    ) -> ToolExecutionResult:
        return ToolExecutionResult(
            tool_call_id=tool_call.tool_call_id,
            name=tool_call.name,
            status="failed",
            output=None,
            error=ToolExecutionError(
                code=code,
                message=message,
                request_id=request_id,
                trace_id=trace_id,
                details=details,
            ),
            redacted_input=redacted_input,
            redacted_output=None,
            duration_ms=duration_ms,
        )

    @staticmethod
    def _duration_ms(started: float) -> int:
        return int((time.monotonic() - started) * 1000)
