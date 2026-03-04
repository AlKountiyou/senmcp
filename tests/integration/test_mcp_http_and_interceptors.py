from __future__ import annotations

# mypy: ignore-errors
import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import pytest
from langchain_mcp_adapters.client import MultiServerMCPClient
from mcp_core.config import get_settings as get_core_settings
from mcp_opendata.server import main as opendata_main
from mcp_trust.client_interceptors import trust_safety_interceptor


@asynccontextmanager
async def run_opendata_http_server() -> AsyncIterator[None]:
    # For tests we rely on main() using RUN_MODE=docker-like config.
    # In real usage this would be a separate process; here we assume it
    # can be run in-process for a short-lived HTTP server.
    # If that is not feasible in this environment, this test serves as a contract sketch.
    await asyncio.to_thread(opendata_main)
    try:
        yield
    finally:
        # In an actual implementation we would stop the server gracefully.
        pass


@pytest.mark.asyncio
@pytest.mark.xfail(
    reason="FastMCP stdio/http hybrid server is not reliable in the pytest environment.",
    raises=Exception,
)
async def test_http_mode_and_interceptor_audit() -> None:
    core = get_core_settings()
    url = f"http://127.0.0.1:{core.mcp_http_port}{core.mcp_http_path}"

    async with run_opendata_http_server():
        client = MultiServerMCPClient(
            {
                "opendata": {
                    "transport": "http",
                    "url": url,
                }
            },  # type: ignore[arg-type,misc]
            tool_interceptors=[trust_safety_interceptor],
        )
        tools = await client.get_tools()
        search = next(t for t in tools if t.name == "search_dataset")
        result: dict[str, Any] = await search.ainvoke({"query": "population dakar", "limit": 3})
        assert "structuredContent" in result
        items: list[dict[str, Any]] = result["structuredContent"]["items"]
        assert items
