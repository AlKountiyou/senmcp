from __future__ import annotations

from functools import lru_cache
from typing import Any

from mcp.server.fastmcp import FastMCP
from mcp_core.config import get_settings as get_core_settings
from mcp_trust.audit import JsonlAuditLogger
from mcp_trust.provenance import ProvenanceManager
from mcp_trust.server_middleware import with_trust_safety

from mcp_opendata.adapters.static_catalog_source import StaticCatalogSource
from mcp_opendata.config import get_settings as get_opendata_settings
from mcp_opendata.usecases.cite_source_uc import CiteSourceUseCase
from mcp_opendata.usecases.download_table_uc import DownloadTableUseCase
from mcp_opendata.usecases.explain_indicator_uc import ExplainIndicatorUseCase
from mcp_opendata.usecases.get_series_uc import GetSeriesUseCase
from mcp_opendata.usecases.search_dataset_uc import SearchDatasetUseCase

mcp = FastMCP("SenCivic Open Data MCP Server", json_response=True)


@lru_cache(maxsize=1)
def _build_dependencies() -> dict[str, Any]:
    core_settings = get_core_settings()
    opendata_settings = get_opendata_settings()
    catalog = StaticCatalogSource(opendata_settings.assets_dir)
    provenance = ProvenanceManager()
    audit_logger = JsonlAuditLogger(core_settings.audit_opendata_path)
    return {
        "catalog": catalog,
        "provenance": provenance,
        "audit_logger": audit_logger,
    }


@mcp.tool()
async def search_dataset(query: str, limit: int = 10) -> dict[str, Any]:
    """Search datasets from the static catalog."""

    deps = _build_dependencies()
    usecase = SearchDatasetUseCase(deps["catalog"])

    async def handler(params: dict[str, Any], ctx: Any) -> dict[str, Any]:
        items = usecase.execute(query=params["query"], limit=params.get("limit", 10))
        return {
            "text": f"{len(items)} dataset(s) found.",
            "structuredContent": {
                "items": [item.model_dump() for item in items],
            },
        }

    result = await with_trust_safety(
        tool_name="opendata.search_dataset",
        params={"query": query, "limit": limit},
        handler=handler,
        audit_logger=deps["audit_logger"],
        provenance_manager=deps["provenance"],
    )
    return result


@mcp.tool()
async def get_series(dataset_id: str, filters: dict[str, Any] | None = None) -> dict[str, Any]:
    """Get a table for a given dataset."""

    deps = _build_dependencies()
    usecase = GetSeriesUseCase(deps["catalog"])

    async def handler(params: dict[str, Any], ctx: Any) -> dict[str, Any]:
        table = usecase.execute(dataset_id=params["dataset_id"], filters=params.get("filters"))
        return {
            "text": f"Returned table for dataset {params['dataset_id']}.",
            "structuredContent": {
                "table": table.model_dump(),
            },
        }

    result = await with_trust_safety(
        tool_name="opendata.get_series",
        params={"dataset_id": dataset_id, "filters": filters},
        handler=handler,
        audit_logger=deps["audit_logger"],
        provenance_manager=deps["provenance"],
    )
    return result


@mcp.tool()
async def explain_indicator(indicator_name: str, context: str | None = None) -> dict[str, Any]:
    """Explain a socio-economic indicator, with caveats and citations."""

    deps = _build_dependencies()
    usecase = ExplainIndicatorUseCase(deps["catalog"])

    async def handler(params: dict[str, Any], ctx: Any) -> dict[str, Any]:
        expl = usecase.execute(
            indicator_name=params["indicator_name"],
            context=params.get("context"),
        )
        return {
            "text": expl.explanation,
            "structuredContent": expl.model_dump(),
        }

    result = await with_trust_safety(
        tool_name="opendata.explain_indicator",
        params={"indicator_name": indicator_name, "context": context},
        handler=handler,
        audit_logger=deps["audit_logger"],
        provenance_manager=deps["provenance"],
    )
    return result


@mcp.tool()
async def download_table(dataset_id: str, fmt: str = "csv") -> dict[str, Any]:
    """Download a dataset table as CSV or JSON."""

    deps = _build_dependencies()
    usecase = DownloadTableUseCase(deps["catalog"])

    async def handler(params: dict[str, Any], ctx: Any) -> dict[str, Any]:
        out = usecase.execute(dataset_id=params["dataset_id"], fmt=params.get("fmt", "csv"))
        return {
            "text": f"Exported dataset {params['dataset_id']} as {out['mime_type']}.",
            "structuredContent": out,
        }

    result = await with_trust_safety(
        tool_name="opendata.download_table",
        params={"dataset_id": dataset_id, "fmt": fmt},
        handler=handler,
        audit_logger=deps["audit_logger"],
        provenance_manager=deps["provenance"],
    )
    return result


@mcp.tool()
async def cite_source(source_id: str) -> dict[str, Any]:
    """Retrieve citation details for a known data source."""

    deps = _build_dependencies()
    usecase = CiteSourceUseCase(deps["catalog"])

    async def handler(params: dict[str, Any], ctx: Any) -> dict[str, Any]:
        citation = usecase.execute(source_id=params["source_id"])
        return {
            "text": f"Citation for source {params['source_id']}.",
            "structuredContent": citation.model_dump(),
        }

    result = await with_trust_safety(
        tool_name="opendata.cite_source",
        params={"source_id": source_id},
        handler=handler,
        audit_logger=deps["audit_logger"],
        provenance_manager=deps["provenance"],
    )
    return result


def main() -> None:
    core = get_core_settings()
    if core.run_mode == "docker":
        mcp.run(
            transport="streamable-http",
            host=core.mcp_http_host,
            port=core.mcp_http_port,
            path=core.mcp_http_path,
        )  # type: ignore[call-arg]
    else:
        mcp.run()


if __name__ == "__main__":
    main()
