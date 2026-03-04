from __future__ import annotations

from typing import Any, TypedDict


class PlannedCall(TypedDict):
    tool_name: str
    arguments: dict[str, Any]


class ToolResult(TypedDict):
    tool_name: str
    raw: Any


class AgentState(TypedDict, total=False):
    user_input: str
    planned_calls: list[PlannedCall]
    tool_results: list[ToolResult]
    answer: str
