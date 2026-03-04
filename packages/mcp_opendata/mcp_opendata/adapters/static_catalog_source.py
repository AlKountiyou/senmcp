from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from mcp_core.models.citations import Citation
from mcp_core.models.datasets import DatasetItem, IndicatorExplanation, SeriesColumn, SeriesTable
from mcp_opendata.domain.repositories import (
    CitationRepository,
    DatasetCatalogRepository,
    IndicatorRepository,
)


class StaticCatalogSource(DatasetCatalogRepository, IndicatorRepository, CitationRepository):
    """Offline-first catalog and dataset source backed by JSON assets."""

    def __init__(self, assets_dir: Path) -> None:
        self._assets_dir = assets_dir
        self._catalog = self._load_json(assets_dir / "catalog.json")
        self._indicators = self._load_json(assets_dir / "indicators.json")

    @staticmethod
    def _load_json(path: Path) -> Any:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)

    def search(self, query: str, limit: int = 10) -> list[DatasetItem]:
        q = query.lower()
        items: list[DatasetItem] = []
        for raw in self._catalog.get("datasets", []):
            text = f"{raw.get('title','')} {raw.get('description','')}".lower()
            # Simple token-based match: require all query tokens to appear.
            tokens = [t for t in q.split() if t]
            if tokens and all(token in text for token in tokens):
                items.append(self._parse_dataset_item(raw))
            if len(items) >= limit:
                break
        return items

    def get_dataset(self, dataset_id: str) -> DatasetItem:
        for raw in self._catalog.get("datasets", []):
            if raw.get("id") == dataset_id:
                return self._parse_dataset_item(raw)
        raise KeyError(f"Dataset not found: {dataset_id}")

    def get_series(self, dataset_id: str, filters: dict[str, Any] | None = None) -> SeriesTable:
        dataset = self.get_dataset(dataset_id)
        data_path = self._assets_dir / "datasets" / f"{dataset_id}.json"
        raw = self._load_json(data_path)
        columns = [SeriesColumn(**col) for col in raw.get("columns", [])]
        rows = raw.get("rows", [])
        metadata = {
            "dataset_id": dataset.id,
            "title": dataset.title,
            "description": dataset.description,
            "source": dataset.source,
            "url": str(dataset.url),
            "updated_at": dataset.updated_at.isoformat(),
        }
        citations = [self._parse_citation(c) for c in raw.get("citations", [])]
        return SeriesTable(columns=columns, rows=rows, metadata=metadata, citations=citations)

    def explain_indicator(
        self, indicator_name: str, context: str | None
    ) -> IndicatorExplanation:
        key = indicator_name.lower()
        raw = self._indicators.get("indicators", {}).get(key)
        if not raw:
            raise KeyError(f"Indicator not found: {indicator_name}")
        citations = [self._parse_citation(c) for c in raw.get("citations", [])]
        explanation = raw.get("explanation", "")
        caveats = raw.get("caveats", "")
        if context:
            explanation = f"{explanation}\n\nContext: {context}"
        return IndicatorExplanation(
            indicator_name=indicator_name,
            explanation=explanation,
            caveats=caveats,
            citations=citations,
        )

    def cite_source(self, source_id: str) -> Citation:
        for raw in self._catalog.get("sources", []):
            if raw.get("id") == source_id:
                return self._parse_citation(raw)
        raise KeyError(f"Source not found: {source_id}")

    @staticmethod
    def _parse_dataset_item(raw: dict[str, Any]) -> DatasetItem:
        return DatasetItem(
            id=raw["id"],
            title=raw["title"],
            description=raw.get("description", ""),
            source=raw.get("source", ""),
            url=raw["url"],
            updated_at=datetime.fromisoformat(raw["updated_at"]),
        )

    @staticmethod
    def _parse_citation(raw: dict[str, Any]) -> Citation:
        return Citation(
            id=raw.get("id", raw.get("source_id", "")),
            title=raw["title"],
            url=raw["url"],
            accessed_at=datetime.fromisoformat(raw["accessed_at"]),
            snippet=raw.get("snippet"),
            source_id=raw.get("source_id"),
        )
