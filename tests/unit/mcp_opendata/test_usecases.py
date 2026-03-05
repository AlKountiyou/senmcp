from __future__ import annotations

from pathlib import Path

from mcp_opendata.adapters.static_catalog_source import StaticCatalogSource
from mcp_opendata.usecases.get_series_uc import GetSeriesUseCase
from mcp_opendata.usecases.search_dataset_uc import SearchDatasetUseCase


def _assets_dir() -> Path:
    return Path(__file__).parents[3] / "packages" / "mcp_opendata" / "mcp_opendata" / "assets"


def test_search_dataset_returns_results() -> None:
    source = StaticCatalogSource(_assets_dir())
    usecase = SearchDatasetUseCase(local_repo=source)
    results = usecase.execute("population dakar", limit=5)
    assert results
    assert all(item.id.startswith("local:") for item in results)
    assert any("Dakar" in item.title for item in results)


def test_get_series_returns_table() -> None:
    source = StaticCatalogSource(_assets_dir())
    usecase = GetSeriesUseCase(local_repo=source)
    table = usecase.execute("population_dakar", filters=None)
    assert table.columns
    assert table.rows
