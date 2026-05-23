"""Thin graph execution orchestration for the Phase 7 chatbot."""

from __future__ import annotations

from typing import Any

from app.domain.chat import ChatGraphState, ConversationMessage
from app.domain.chat_tools import (
    MemoryWriteIntent,
    ToolExecutionResult,
    detect_write_memory_intent,
)
from app.domain.errors import MaxToolCallsExceededError, RecursionLimitExceededError
from app.infra.chatbot_graph import build_chatbot_graph
from app.infra.prompt_registry import PromptRegistry


class ChatbotGraphService:
    """Run the single-LLM tool loop and preserve safe state."""

    def __init__(
        self,
        *,
        llm_adapter,
        prompt_registry: PromptRegistry,
        tool_execution_service,
        tracing_service,
    ) -> None:
        self._llm_adapter = llm_adapter
        self._prompt_registry = prompt_registry
        self._tool_execution_service = tool_execution_service
        self._tracing_service = tracing_service
        self._active_trace_handle = None
        self._graph = build_chatbot_graph(
            llm_step=self._llm_node,
            tool_step=self._tool_node,
            finalize_step=self._finalize_node,
        )

    @property
    def graph_node_names(self) -> tuple[str, ...]:
        """Return the compiled graph node names for tests and review."""
        return self._graph.node_names

    async def run(
        self,
        *,
        request_id: str,
        user_id: str,
        conversation_id: str,
        message_id: str,
        user_message: str,
        context_messages: list[ConversationMessage],
        limits,
        trace_handle,
        trace_root,
        warnings: list[str] | None = None,
    ) -> ChatGraphState:
        """Execute the chat graph for one authenticated user message."""
        state = ChatGraphState(
            request_id=request_id,
            user_id=user_id,
            conversation_id=conversation_id,
            message_id=message_id,
            pending_user_message=user_message,
            messages=context_messages,
            limits=limits,
            trace_id=trace_root.trace_id if trace_root else None,
            run_id=trace_root.run_id if trace_root else None,
            warnings=list(warnings or []),
            metadata={
                "memory_intent": detect_write_memory_intent(user_message).model_dump(),
            },
        )
        try:
            self._active_trace_handle = trace_handle
            result = await self._graph.ainvoke(
                state.model_dump(mode="python"),
                recursion_limit=limits.recursion_limit,
            )
            return ChatGraphState.model_validate(result)
        except Exception as exc:
            if type(exc).__name__ == "GraphRecursionError":
                raise RecursionLimitExceededError("Chat graph recursion limit exceeded") from exc
            raise
        finally:
            self._active_trace_handle = None

    async def _llm_node(self, state: dict[str, Any]) -> dict[str, Any]:
        current = ChatGraphState.model_validate(state)
        prompt_bundle = self._prompt_registry.get_bundle()
        llm_span = await self._tracing_service.start_llm_span(
            self._active_trace_handle,
            current.request_id,
            {
                "prompt_version": prompt_bundle.version,
                "message_count": len(current.messages),
            },
        )
        completion = await self._llm_adapter.generate(
            messages=current.messages,
            prompts=prompt_bundle,
            tools=self._tool_execution_service.registered_tools(),
            request_id=current.request_id,
            trace_id=current.trace_id,
        )
        await self._tracing_service.finish(
            llm_span,
            "success",
            {
                "request_id": current.request_id,
                "finish_reason": completion.finish_reason,
                "tool_call_count": len(completion.tool_calls),
                "run_id": current.run_id,
            },
        )
        messages = list(current.messages)
        if completion.message and not completion.tool_calls:
            messages.append(ConversationMessage(role="assistant", content=completion.message))
        current.messages = messages
        current.tool_calls = completion.tool_calls
        if completion.message and not current.final_response:
            current.final_response = completion.message
        return current.model_dump(mode="python")

    async def _tool_node(self, state: dict[str, Any]) -> dict[str, Any]:
        current = ChatGraphState.model_validate(state)
        memory_intent = MemoryWriteIntent.model_validate(current.metadata.get("memory_intent", {}))
        if current.tool_call_count + len(current.tool_calls) > current.limits.max_tool_calls:
            raise MaxToolCallsExceededError("Chat tool-call limit exceeded")
        tool_results = list(current.tool_results)
        messages = list(current.messages)
        for tool_call in current.tool_calls:
            tool_span = await self._tracing_service.start_tool_span(
                self._active_trace_handle,
                current.request_id,
                {"tool_name": tool_call.name, "tool_call_id": tool_call.tool_call_id},
            )
            result = await self._tool_execution_service.execute(
                tool_call=tool_call,
                user_id=current.user_id,
                conversation_id=current.conversation_id,
                message_id=current.message_id,
                request_id=current.request_id,
                trace_id=current.trace_id,
                memory_intent=memory_intent,
            )
            if tool_call.name == "answer_project_question" and result.status == "success":
                rag_span = await self._tracing_service.start_rag_span(
                    self._active_trace_handle,
                    current.request_id,
                    {"tool_name": tool_call.name},
                )
                await self._tracing_service.finish(
                    rag_span,
                    "success",
                    {
                        "request_id": current.request_id,
                        "trace_id": current.trace_id,
                        "run_id": current.run_id,
                    },
                )
            await self._tracing_service.finish(
                tool_span,
                "success" if result.status == "success" else "failed",
                {
                    "request_id": current.request_id,
                    "trace_id": current.trace_id,
                    "run_id": current.run_id,
                    "tool_name": tool_call.name,
                    "status": result.status,
                },
            )
            tool_results.append(result)
            messages.append(
                ConversationMessage(
                    role="tool",
                    name=tool_call.name,
                    content=self._tool_message_content(tool_call.name, result),
                )
            )
        current.messages = messages
        current.tool_results = tool_results
        current.tool_call_count += len(current.tool_calls)
        current.tool_calls = []
        return current.model_dump(mode="python")

    async def _finalize_node(self, state: dict[str, Any]) -> dict[str, Any]:
        current = ChatGraphState.model_validate(state)
        if current.final_response:
            return current.model_dump(mode="python")
        if current.tool_results:
            last = current.tool_results[-1]
            if last.status == "success":
                current.final_response = "Tool execution completed successfully."
            else:
                current.final_response = "A required tool failed, so this answer is partial."
        else:
            current.final_response = "I could not produce a safe answer for this request."
        return current.model_dump(mode="python")

    def _tool_message_content(self, tool_name: str, result: ToolExecutionResult) -> str:
        if result.status != "success":
            return f"Tool {tool_name} failed safely: {result.error.message if result.error else 'unknown error'}"
        if tool_name == "answer_project_question":
            answer = result.output.get("answer", "") if result.output else ""
            return (
                f"{self._prompt_registry.get_bundle().untrusted_context_prompt}\n"
                f"Answer: {answer}\n"
                f"Sources: {result.output.get('supporting_sources', []) if result.output else []}"
            )
        return f"Tool {tool_name} result: {result.output}"
