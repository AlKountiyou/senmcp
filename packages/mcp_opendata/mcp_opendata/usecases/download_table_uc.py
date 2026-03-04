from __future__ import annotations

from typing import Literal, TypedDict

from mcp_opendata.adapters.table_exporter import export_table
from mcp_opendata.domain.repositories import DatasetCatalogRepository


class DownloadTableResult(TypedDict):
    content_base64: str
    filename: str
    mime_type: str


class DownloadTableUseCase:
    def __init__(self, repo: DatasetCatalogRepository) -> None:
        self._repo = repo

    def execute(self, dataset_id: str, fmt: Literal["csv", "json"]) -> DownloadTableResult:
        table = self._repo.get_series(dataset_id=dataset_id, filters=None)
        content_b64, filename, mime_type = export_table(dataset_id, table, fmt)
        return {
            "content_base64": content_b64,
            "filename": filename,
            "mime_type": mime_type,
        }
