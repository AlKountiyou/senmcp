from __future__ import annotations

from mcp_core.models.datasets import DatasetItem
from mcp_opendata.domain.repositories import (
    AnsdCatalogPort,
    CkanCatalogPort,
    DatasetCatalogRepository,
)


class SearchDatasetUseCase:
    """Aggregate search across local, ANSD, and CKAN catalogs."""

    def __init__(
        self,
        local_repo: DatasetCatalogRepository,
        ansd_catalog: AnsdCatalogPort | None = None,
        ckan_catalog: CkanCatalogPort | None = None,
    ) -> None:
        self._local_repo = local_repo
        self._ansd_catalog = ansd_catalog
        self._ckan_catalog = ckan_catalog

    def execute(self, query: str, limit: int = 10) -> list[DatasetItem]:
        results: list[DatasetItem] = []

        # Local/offline catalog, wrapped with local:* prefix.
        for item in self._local_repo.search(query=query, limit=limit):
            results.append(
                DatasetItem(
                    id=f"local:{item.id}",
                    title=item.title,
                    description=item.description,
                    source=item.source or "Local Catalog",
                    url=item.url,
                    updated_at=item.updated_at,
                )
            )

        # ANSD portal catalog.
        if self._ansd_catalog is not None:
            try:
                results.extend(self._ansd_catalog.search(query=query, limit=limit))
            except Exception:
                # Graceful degradation: ignore remote failures.
                # In this context we only care that the local catalog remains usable.
                ...

        # CKAN (AgriData) catalog.
        if self._ckan_catalog is not None:
            try:
                results.extend(self._ckan_catalog.search(query=query, limit=limit))
            except Exception:
                # Graceful degradation: ignore remote failures.
                ...

        # Dedupe by (normalized title, normalized url), keep freshest updated_at.
        dedup: dict[tuple[str, str], DatasetItem] = {}
        for item in results:
            key = (item.title.strip().lower(), str(item.url).strip().lower())
            existing = dedup.get(key)
            if existing is None or item.updated_at > existing.updated_at:
                dedup[key] = item

        # Sort by updated_at desc and respect limit.
        combined = sorted(dedup.values(), key=lambda d: d.updated_at, reverse=True)
        return combined[:limit]

