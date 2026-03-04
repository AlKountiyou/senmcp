from __future__ import annotations

from typing import Any

from mcp_core.models.datasets import SeriesTable
from mcp_opendata.domain.repositories import DatasetCatalogRepository


class GetSeriesUseCase:
    def __init__(self, repo: DatasetCatalogRepository) -> None:
        self._repo = repo

    def execute(self, dataset_id: str, filters: dict[str, Any] | None = None) -> SeriesTable:
        return self._repo.get_series(dataset_id=dataset_id, filters=filters)
