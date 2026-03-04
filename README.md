# senmcp

An open-source Senegal civic MCP stack: MCP servers for public data and citizen services, with a LangChain/LangGraph agent, provenance, and safety-by-design.

## Quickstart

1. Install dependencies (locally, with `uv`):

```bash
uv sync
```

2. Run lint, type-check, and tests:

```bash
make lint
make typecheck
make test
```

3. List MCP tools via the CLI:

```bash
uv run sencivic tools-list
```

4. Call a specific tool:

```bash
uv run sencivic call opendata search_dataset -p query='"population dakar"' -p limit=5
```

5. Start an interactive chat using both MCP servers:

```bash
uv run sencivic chat --servers opendata,services
```

6. Run everything in Docker:

```bash
docker compose up --build
```

This will start:

- `mcp_opendata` HTTP MCP server
- `mcp_services` HTTP MCP server
- `agent_app` container running the `sencivic` chat agent configured for HTTP transports

