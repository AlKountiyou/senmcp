from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from mcp_core.config import get_settings as get_core_settings


def build_mcp_connections(
    selected_servers: Iterable[str] | None = None,
) -> dict[str, dict[str, Any]]:
    """Build MultiServerMCPClient connection config based on RUN_MODE.

    Local dev -> stdio transports.
    Docker (RUN_MODE=docker) -> HTTP transports only.
    """

    core = get_core_settings()
    servers = {"opendata", "services"}
    if selected_servers is not None:
        servers = servers.intersection(set(selected_servers))

    connections: dict[str, dict[str, Any]] = {}

    if core.run_mode == "docker":
        base_path = core.mcp_http_path
        for name in servers:
            connections[name] = {
                "transport": "http",
                "url": f"http://mcp_{name}:{core.mcp_http_port}{base_path}",
            }
    else:
        for name in servers:
            module = f"mcp_{name}.server"
            connections[name] = {
                "transport": "stdio",
                "command": "python",
                "args": ["-m", module],
            }

    return connections
