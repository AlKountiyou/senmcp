from __future__ import annotations

from collections.abc import Callable
from typing import cast

from agent_app.graph.state import AgentState, PlannedCall
from langchain_core.tools import BaseTool


def build_tool_index(tools: list[BaseTool]) -> dict[str, BaseTool]:
    return {tool.name: tool for tool in tools}


def planner_node(tools: list[BaseTool]) -> Callable[[AgentState], AgentState]:
    """Factory returning a planner function bound to the available tools."""

    tool_index = build_tool_index(tools)
    tool_names = list(tool_index.keys())

    def _planner(state: AgentState) -> AgentState:
        user_input = state.get("user_input", "").lower()
        planned: list[PlannedCall] = []

        # Very small heuristic dispatcher; this is intentionally simple.
        if "population" in user_input or "dakar" in user_input:
            if "search_dataset" in tool_names:
                planned.append(
                    PlannedCall(
                        tool_name="search_dataset",
                        arguments={"query": state["user_input"], "limit": 5},
                    )
                )
        if "service" in user_input or "allocation" in user_input or "carte" in user_input:
            if "list_services" in tool_names:
                planned.append(PlannedCall(tool_name="list_services", arguments={"category": None}))

        if not planned:
            # Fallback: do nothing; synthesizer will respond accordingly.
            planned = []

        new_state = cast(AgentState, dict(state))
        new_state["planned_calls"] = planned
        return new_state

    return _planner
