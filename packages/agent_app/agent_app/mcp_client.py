from __future__ import annotations

from collections.abc import Iterable

from langchain_core.tools import BaseTool
from langchain_mcp_adapters.client import MultiServerMCPClient
from mcp_trust.client_interceptors import trust_safety_interceptor

from agent_app.config import build_mcp_connections


async def create_mcp_client(
    selected_servers: Iterable[str] | None = None,
) -> MultiServerMCPClient:
    """Create a MultiServerMCPClient configured for the requested servers."""

    connections = build_mcp_connections(selected_servers)
    client = MultiServerMCPClient(
        connections, tool_interceptors=[trust_safety_interceptor]
    )  # type: ignore[arg-type]
    return client


async def load_tools(client: MultiServerMCPClient) -> list[BaseTool]:
    """Load all tools from the configured MCP servers."""

    tools = await client.get_tools()
    return list(tools)
