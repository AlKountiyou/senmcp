from __future__ import annotations

from typing import Any

from mcp_core.models.datasets import SeriesTable
from mcp_opendata.domain.repositories import (
    AnsdTablePort,
    CkanTablePort,
    DatasetCatalogRepository,
)


class GetSeriesUseCase:
    """Route get_series calls based on dataset_id prefix."""

    def __init__(
        self,
        local_repo: DatasetCatalogRepository,
        ansd_table: AnsdTablePort | None = None,
        ckan_table: CkanTablePort | None = None,
    ) -> None:
        self._local_repo = local_repo
        self._ansd_table = ansd_table
        self._ckan_table = ckan_table

    def execute(self, dataset_id: str, filters: dict[str, Any] | None = None) -> SeriesTable:
        # Backwards compatibility: no prefix means local dataset ID.
        effective_id = dataset_id
        if ":" not in effective_id:
            effective_id = f"local:{effective_id}"

        if effective_id.startswith("local:"):
            local_id = effective_id.split(":", 1)[1]
            return self._local_repo.get_series(dataset_id=local_id, filters=filters)

        if effective_id.startswith("ansd:"):
            if self._ansd_table is None:
                raise RuntimeError("ANSD table adapter is not configured.")
            return self._ansd_table.fetch_table(dataset_id=effective_id, filters=filters)

        if effective_id.startswith("ckan:"):
            if self._ckan_table is None:
                raise RuntimeError("CKAN table adapter is not configured.")
            return self._ckan_table.fetch_table(dataset_id=effective_id, filters=filters)

        raise ValueError(f"Unsupported dataset_id prefix for get_series: {dataset_id}")

