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

- `mcp_opendata` HTTP MCP server (exposed on `localhost:8000`)
- `mcp_services` HTTP MCP server (exposed on `localhost:8001`)
- `agent_app` container running the `sencivic` chat agent configured for HTTP transports

## ANSD live mode

The open data MCP server (`mcp_opendata`) can combine the offline JSON catalog with live data from:

- ANSD main portal (`ansd.sn`) for databases, publications, and indicators.
- ANSD AgriData CKAN (`agridata.ansd.sn`) for agriculture datasets.

### Configuration

Key environment variables (see `.env.example`):

- `ALLOWLIST_DOMAINS`: comma-separated list of allowed domains for outbound HTTP requests.  
  Defaults for ANSD live mode: `ansd.sn,agridata.ansd.sn`.
- `HTTP_RATE_LIMIT_PER_HOST`: max HTTP requests per second per host (default `1.0`).
- `HTTP_CACHE_TTL_SECONDS`: disk cache TTL in seconds for HTTP responses (default `86400`).
- `HTTP_TIMEOUT_SECONDS`: per-request timeout in seconds for outbound HTTP calls (default `10.0`).
- `HTTP_MAX_BYTES`: maximum number of bytes to read from any HTTP response body (default `10000000`).

The shared HTTP client in `mcp_core` enforces:

- Strict `http`/`https` schemes only.
- Domain allowlist + SSRF protections (blocks private IP ranges, localhost, link-local).
- Per-host rate limiting and conditional requests using `ETag` / `Last-Modified` when provided.

### Using live datasets

When `ALLOWLIST_DOMAINS` includes `ansd.sn` and `agridata.ansd.sn`, `search_dataset` will return:

- Local/offline entries with IDs like `local:population_dakar` and source `"Local Catalog"`.
- ANSD portal entries with IDs like `ansd:web:<slug>` or `ansd:pub:<slug>` and source `"ANSD Portal"`.
- ANSD AgriData CKAN entries with IDs like `ckan:agridata:<package_name>:<resource_id>` and source `"ANSD AgriData (CKAN)"`.

`get_series` and `download_table` accept these IDs and return tables with `citations[]` that include:

- `title`, `url`, `accessed_at` (ISO8601).
- Either a short `snippet` (headers + first row, <= 300 chars) or a `file_hash` (SHA-256 of downloaded content).

