## ADR-0003: ANSD Ingestion Strategy

Status: Accepted  
Date: 2026-03-04

### Context

The SenCivic MCP stack exposes open data from Senegal via the `mcp_opendata` MCP server. Initially, this server only served a curated, offline JSON catalog bundled with the codebase. To better support up-to-date insights and reduce manual curation, we want to incorporate live data from:

- The ANSD main portal (`https://www.ansd.sn/`) for databases, publications, and indicators.
- The ANSD AgriData CKAN portal (`https://agridata.ansd.sn/`) for agriculture datasets.

At the same time, we must:

- Preserve the existing offline JSON assets and behavior as a safe fallback.
- Respect ANSD robots/terms by avoiding aggressive scraping.
- Maintain strong security (allowlist, SSRF protections), provenance (citations), and reproducibility.

### Decision

We will use a **runtime fetch with caching** strategy instead of a separate offline curation pipeline:

- **Offline catalog remains the baseline**:
  - `StaticCatalogSource` continues to provide a curated, version-controlled catalog and datasets.
  - All existing tools and tests that rely on offline IDs (e.g. `population_dakar`) continue to work.

- **Live ANSD portal integration via adapters**:
  - `AnsdWebCatalogAdapter` crawls a small set of stable ANSD entry points (e.g. `/bases-de-donnees`, `/toutes-les-publications`) using a shared HTTP client.
  - It extracts minimal metadata (ID, title, description, source, URL, updated_at) and persists a thin JSON cache under `.cache/ansd` with a TTL.
  - Dataset IDs are namespaced (`ansd:web:<slug>`, `ansd:pub:<slug>`, `ansd:ind:<slug>`) to avoid collisions with offline IDs.
  - `AnsdDownloadAdapter` follows dataset pages to discover `Download CSV/XLS/XLSX` links, downloads the file, parses it to a table (CSV or XLS/XLSX), and returns a `SeriesTable` with citations that include a `file_hash` (SHA-256) and an optional short snippet.

- **Live AgriData CKAN integration via a CKAN adapter**:
  - `CkanAgriDataAdapter` talks to the AgriData CKAN API (`/api/3/action/...`) to:
    - Discover packages/resources (`package_search`, `package_show`).
    - Download resources (CSV/JSON) as tables.
  - CKAN-backed datasets are also namespaced as `ckan:agridata:<package_name>:<resource_id>`.
  - Tables returned from CKAN include citations with `url`, `accessed_at`, and `snippet` or `file_hash`.

- **Use cases and tools aggregate local + live sources**:
  - `SearchDatasetUseCase` queries:
    - Local offline catalog (wrapped as `local:<id>` with source `"Local Catalog"`).
    - ANSD portal catalog.
    - CKAN AgriData catalog.
  - Results are deduplicated by `(title, url)` and sorted by `updated_at`, with graceful degradation if remote sources fail.
  - `GetSeriesUseCase` routes `dataset_id` by prefix:
    - `local:*` → offline JSON.
    - `ansd:*` → ANSD adapters.
    - `ckan:*` → CKAN adapter.
  - `download_table` reuses `GetSeriesUseCase`, so exports work uniformly for offline and live datasets.

### Rationale

- **Freshness and simplicity**:
  - Runtime fetch with caching keeps the architecture simple (no extra ETL or scheduled jobs) while still respecting ANSD infrastructure via rate limiting and disk cache TTL.
  - A separate ingestion pipeline would add operational complexity (scheduling, storage, invalidation) without clear benefit for the current scale.

- **Respecting robots/terms**:
  - The shared HTTP client enforces:
    - Domain allowlist (`ALLOWLIST_DOMAINS`), defaulting to `ansd.sn,agridata.ansd.sn`.
    - Strict `http` / `https` schemes only.
    - SSRF protections that block private IP ranges, localhost, and link-local addresses.
    - Per-host rate limiting (1–2 requests/sec) and caching with TTL.
  - Caches are small and focused on metadata and small tables, not bulk mirroring.

- **Security and provenance**:
  - All outbound HTTP calls go through the shared client, which is configured once in `mcp_core` and reused by adapters.
  - Every table returned from remote sources includes `citations[]` with:
    - `title`, `url`, `accessed_at`.
    - Either a short `snippet` or a `file_hash` for downloaded resources.
  - MCP tools remain wrapped with `with_trust_safety`, so URL parameters are still subject to prompt-injection and allowlist policies, and all calls are audited.

- **Reproducibility**:
  - Offline assets remain available and are always preferred when the dataset_id explicitly uses a `local:*` prefix.
  - Tests for live adapters use HTTP mocking (`respx` + `httpx`) rather than hitting real ANSD endpoints, making the test suite deterministic and CI-friendly.
  - When needed, dataset IDs and `file_hash` values can be used to re-validate downloaded resources.

### Consequences

- The `mcp_opendata` server now has a small runtime dependency on external ANSD/CKAN endpoints when they are allowlisted, but it degrades gracefully to offline-only behavior when:
  - Network is unavailable.
  - Domains are not allowlisted.
  - Remote responses fail or exceed configured limits.

- New configuration parameters in `CoreSettings` and `.env.example` are required to tune:
  - HTTP rate limiting.
  - Cache TTL.
  - Timeouts and response size limits.

- Future extensions (e.g., additional portals or alternative ingestion pipelines) can reuse the same hexagonal pattern:
  - Define a port (`XCatalogPort`, `XTablePort`).
  - Implement an adapter.
  - Plug it into the existing use cases without changing tool signatures.

