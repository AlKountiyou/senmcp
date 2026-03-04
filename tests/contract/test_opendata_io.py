from __future__ import annotations

from pathlib import Path

from mcp_core.models.citations import Citation
from mcp_core.models.datasets import DatasetItem, IndicatorExplanation, SeriesTable
from mcp_opendata.adapters.static_catalog_source import StaticCatalogSource
from mcp_opendata.usecases.cite_source_uc import CiteSourceUseCase
from mcp_opendata.usecases.explain_indicator_uc import ExplainIndicatorUseCase
from mcp_opendata.usecases.get_series_uc import GetSeriesUseCase
from mcp_opendata.usecases.search_dataset_uc import SearchDatasetUseCase


def _assets_dir() -> Path:
    # tests live under `<root>/tests/...`, so `parents[2]` is the workspace root
    return Path(__file__).parents[2] / "packages" / "mcp_opendata" / "mcp_opendata" / "assets"


def test_search_dataset_contract() -> None:
    source = StaticCatalogSource(_assets_dir())
    uc = SearchDatasetUseCase(source)
    items = uc.execute("population", limit=3)
    for item in items:
        assert isinstance(item, DatasetItem)


def test_get_series_contract() -> None:
    source = StaticCatalogSource(_assets_dir())
    uc = GetSeriesUseCase(source)
    table = uc.execute("population_dakar", filters=None)
    assert isinstance(table, SeriesTable)


def test_explain_indicator_contract() -> None:
    source = StaticCatalogSource(_assets_dir())
    uc = ExplainIndicatorUseCase(source)
    expl = uc.execute("taux_de_croissance_population_dakar", context=None)
    assert isinstance(expl, IndicatorExplanation)


def test_cite_source_contract() -> None:
    source = StaticCatalogSource(_assets_dir())
    uc = CiteSourceUseCase(source)
    citation = uc.execute("ansd_population")
    assert isinstance(citation, Citation)
