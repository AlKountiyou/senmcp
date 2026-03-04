## ADR-0002: MCP Server Runtime and Transports

Status: Accepted  
Date: 2026-03-04

We use the official MCP Python SDK for all MCP server implementations (no additional FastMCP abstraction). Local development uses stdio transport, while Docker deployments expose an HTTP MCP endpoint. The HTTP configuration is controlled via `MCP_HTTP_HOST` (default `0.0.0.0`), `MCP_HTTP_PORT` (default `8000`), and `MCP_HTTP_PATH` (default `/mcp`).

MCP SDK and `langchain-mcp-adapters` versions are pinned to known-good releases; upgrades happen via a dedicated PR that updates the lockfile and runs the HTTP integration tests.

