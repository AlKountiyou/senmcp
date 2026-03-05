from __future__ import annotations

from typing import Literal, TypedDict

from mcp_opendata.adapters.table_exporter import export_table
from mcp_opendata.usecases.get_series_uc import GetSeriesUseCase


class DownloadTableResult(TypedDict):
    content_base64: str
    filename: str
    mime_type: str


class DownloadTableUseCase:
    def __init__(self, get_series_uc: GetSeriesUseCase) -> None:
        self._get_series_uc = get_series_uc

    def execute(self, dataset_id: str, fmt: Literal["csv", "json"]) -> DownloadTableResult:
        table = self._get_series_uc.execute(dataset_id=dataset_id, filters=None)
        content_b64, filename, mime_type = export_table(dataset_id, table, fmt)
        return {
            "content_base64": content_b64,
            "filename": filename,
            "mime_type": mime_type,
        }

