from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, HttpUrl

from .citations import Citation


class DatasetItem(BaseModel):
    """Summary information for a dataset in the catalog."""

    id: str
    title: str
    description: str
    source: str
    url: HttpUrl
    updated_at: datetime


class SeriesColumn(BaseModel):
    """Column metadata for a tabular time series or indicator dataset."""

    name: str
    type: str
    description: str | None = None


class SeriesTable(BaseModel):
    """Tabular data returned by get_series or download_table."""

    columns: list[SeriesColumn]
    rows: list[list[Any]]
    metadata: dict[str, Any] = {}
    citations: list[Citation] = []


class IndicatorExplanation(BaseModel):
    """Explanation of a socio-economic indicator."""

    indicator_name: str
    explanation: str
    caveats: str
    citations: list[Citation] = []
