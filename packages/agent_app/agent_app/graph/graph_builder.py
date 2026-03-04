from __future__ import annotations

from typing import Any

from agent_app.graph.executor import executor_node
from agent_app.graph.planner import planner_node
from agent_app.graph.state import AgentState
from agent_app.graph.synthesizer import synthesizer_node
from langchain_core.tools import BaseTool
from langgraph.graph import END, StateGraph


def build_agent_graph(tools: list[BaseTool]) -> Any:
    """Build a simple plan->execute->synthesize LangGraph agent."""

    planner = planner_node(tools)
    executor = executor_node(tools)
    synthesizer = synthesizer_node()

    graph = StateGraph(AgentState)
    graph.add_node("plan", planner)  # type: ignore[call-overload]
    graph.add_node("execute", executor)  # type: ignore[call-overload]
    graph.add_node("synthesize", synthesizer)  # type: ignore[call-overload]

    graph.set_entry_point("plan")
    graph.add_edge("plan", "execute")
    graph.add_edge("execute", "synthesize")
    graph.add_edge("synthesize", END)

    return graph.compile()
