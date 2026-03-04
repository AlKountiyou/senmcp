from __future__ import annotations

from typing import Any

import pytest
from mcp_opendata.server import search_dataset
from mcp_services.server import list_services


@pytest.mark.asyncio
@pytest.mark.xfail(
    reason="FastMCP stdio server cannot be cleanly driven from pytest without real stdio.",
    raises=Exception,
)
async def test_opendata_search_dataset_stdio() -> None:
    result: dict[str, Any] = await search_dataset("population dakar", limit=5)
    assert "structuredContent" in result
    items: list[dict[str, Any]] = result["structuredContent"]["items"]
    assert items


@pytest.mark.asyncio
async def test_services_get_service_stdio() -> None:
    # call list_services, then pick first service for a follow-up
    result: dict[str, Any] = await list_services(category=None)
    services: list[dict[str, Any]] = result["structuredContent"]["services"]
    assert services
