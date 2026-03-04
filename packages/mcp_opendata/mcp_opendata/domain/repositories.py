from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from mcp_core.models.citations import Citation
from mcp_core.models.datasets import DatasetItem, IndicatorExplanation, SeriesTable


class DatasetCatalogRepository(ABC):
    """Abstraction over dataset catalog and tables."""

    @abstractmethod
    def search(self, query: str, limit: int = 10) -> list[DatasetItem]:
        raise NotImplementedError

    @abstractmethod
    def get_dataset(self, dataset_id: str) -> DatasetItem:
        raise NotImplementedError

    @abstractmethod
    def get_series(self, dataset_id: str, filters: dict[str, Any] | None = None) -> SeriesTable:
        raise NotImplementedError


class IndicatorRepository(ABC):
    """Abstraction over indicator definitions and caveats."""

    @abstractmethod
    def explain_indicator(
        self, indicator_name: str, context: str | None
    ) -> IndicatorExplanation:
        raise NotImplementedError


class CitationRepository(ABC):
    """Abstraction over citation lookup."""

    @abstractmethod
    def cite_source(self, source_id: str) -> Citation:
        raise NotImplementedError
