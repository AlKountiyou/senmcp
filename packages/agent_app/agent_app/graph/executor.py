from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import cast

from agent_app.graph.state import AgentState, PlannedCall, ToolResult
from langchain_core.tools import BaseTool


def executor_node(tools: list[BaseTool]) -> Callable[[AgentState], Awaitable[AgentState]]:
    """Factory returning an async executor node bound to the available tools."""

    index: dict[str, BaseTool] = {tool.name: tool for tool in tools}

    async def _executor(state: AgentState) -> AgentState:
        planned: list[PlannedCall] = state.get("planned_calls", [])
        results: list[ToolResult] = []

        for call in planned:
            tool = index.get(call["tool_name"])
            if tool is None:
                continue
            # Tools from MCP adapters can be async; use ainvoke if available.
            if hasattr(tool, "ainvoke"):
                raw = await tool.ainvoke(call["arguments"])
            else:
                raw = tool.invoke(call["arguments"])  # type: ignore[assignment]
            results.append(ToolResult(tool_name=call["tool_name"], raw=raw))

        new_state = cast(AgentState, dict(state))
        new_state["tool_results"] = results
        return new_state

    return _executor
