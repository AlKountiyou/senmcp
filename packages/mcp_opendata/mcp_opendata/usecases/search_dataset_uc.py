from __future__ import annotations

from mcp_core.models.datasets import DatasetItem
from mcp_opendata.domain.repositories import DatasetCatalogRepository


class SearchDatasetUseCase:
    def __init__(self, repo: DatasetCatalogRepository) -> None:
        self._repo = repo

    def execute(self, query: str, limit: int = 10) -> list[DatasetItem]:
        return self._repo.search(query=query, limit=limit)
