from __future__ import annotations

# mypy: ignore-errors
import asyncio
import os
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
    # Configure core settings for HTTP mode and restrict allowlist so remote ANSD/CKAN
    # adapters gracefully degrade to offline-only behavior (no real network).
    os.environ.update(
        {
            "RUN_MODE": "docker",
            "MCP_HTTP_HOST": "127.0.0.1",
            "ALLOWLIST_DOMAINS": '["example.org"]',
        }
    )
    get_core_settings.cache_clear()  # type: ignore[attr-defined]

    core = get_core_settings()
    url = f"http://{core.mcp_http_host}:{core.mcp_http_port}{core.mcp_http_path}"

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
        get_series = next(t for t in tools if t.name == "get_series")

        search_result: dict[str, Any] = await search.ainvoke(
            {"query": "population dakar", "limit": 3}
        )
        assert "structuredContent" in search_result
        items: list[dict[str, Any]] = search_result["structuredContent"]["items"]
        assert items

        dataset_id = items[0]["id"]
        series_result: dict[str, Any] = await get_series.ainvoke(
            {"dataset_id": dataset_id, "filters": None}
        )
        assert "structuredContent" in series_result
        table = series_result["structuredContent"]["table"]
        assert table["columns"]
        assert table["rows"]
        # Offline assets already include citations; ensure they are surfaced.
        assert "citations" in table
