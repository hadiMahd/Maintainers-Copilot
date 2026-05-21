"""Thin LangGraph wrapper around one tool-calling LLM loop."""

from __future__ import annotations

from typing import Any, Awaitable, Callable


class ChatbotGraph:
    """Small wrapper that exposes the compiled graph plus node names."""

    def __init__(self, compiled_graph, node_names: tuple[str, ...]) -> None:
        self._compiled_graph = compiled_graph
        self.node_names = node_names

    async def ainvoke(self, state: dict[str, Any], *, recursion_limit: int) -> dict[str, Any]:
        """Run the compiled graph with an explicit recursion limit."""
        return await self._compiled_graph.ainvoke(
            state,
            config={"recursion_limit": recursion_limit},
        )


class _FallbackCompiledGraph:
    """Minimal fallback executor used when LangGraph is unavailable."""

    def __init__(self, llm_step, tool_step, finalize_step) -> None:
        self._llm_step = llm_step
        self._tool_step = tool_step
        self._finalize_step = finalize_step

    async def ainvoke(self, state: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
        recursion_limit = int(config.get("recursion_limit", 8))
        current = dict(state)
        steps = 0
        while True:
            if steps >= recursion_limit:
                raise RuntimeError("GraphRecursionError")
            current = await self._llm_step(current)
            steps += 1
            if current.get("tool_calls"):
                if steps >= recursion_limit:
                    raise RuntimeError("GraphRecursionError")
                current = await self._tool_step(current)
                steps += 1
                continue
            if steps >= recursion_limit:
                raise RuntimeError("GraphRecursionError")
            current = await self._finalize_step(current)
            return current


def build_chatbot_graph(
    *,
    llm_step: Callable[[dict[str, Any]], Awaitable[dict[str, Any]]],
    tool_step: Callable[[dict[str, Any]], Awaitable[dict[str, Any]]],
    finalize_step: Callable[[dict[str, Any]], Awaitable[dict[str, Any]]],
) -> ChatbotGraph:
    """Build the thin Phase 7 chat graph.

    The project currently uses a plain ``dict`` state shape. With the installed
    LangGraph version, that path can retain stale list fields across loop
    iterations and never exit a completed tool cycle. The fallback executor keeps
    the intended single-LLM loop semantics deterministic for both tests and local
    runtime.
    """
    compiled = _FallbackCompiledGraph(llm_step, tool_step, finalize_step)

    return ChatbotGraph(
        compiled_graph=compiled,
        node_names=("llm", "execute_tools", "finalize"),
    )
