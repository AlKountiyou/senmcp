from __future__ import annotations

import csv
import hashlib
from datetime import UTC, datetime
from io import StringIO
from typing import Any

import pandas as pd  # type: ignore[import-untyped]
from bs4 import BeautifulSoup  # type: ignore[import-untyped]
from mcp_core.http_client import get_http_client
from mcp_core.models.citations import Citation
from mcp_core.models.datasets import SeriesColumn, SeriesTable
from mcp_opendata.domain.repositories import AnsdCatalogPort, AnsdTablePort
from pydantic import HttpUrl


class AnsdDownloadAdapter(AnsdTablePort):
    """Adapter that follows ANSD dataset pages and downloads CSV/XLS(X) tables."""

    def __init__(self, catalog: AnsdCatalogPort) -> None:
        self._catalog = catalog
        self._http = get_http_client()

    def fetch_table(self, dataset_id: str, filters: dict[str, Any] | None = None) -> SeriesTable:
        # Look up dataset metadata first to find the page URL.
        dataset = self._catalog.get_dataset(dataset_id)
        page_url = str(dataset.url)

        page_resp = self._http.fetch(page_url)
        if page_resp.status_code != 200:
            raise RuntimeError(f"Failed to fetch ANSD dataset page: {page_url}")

        soup = BeautifulSoup(page_resp.content, "lxml")
        download_url = self._find_download_link(soup, page_url)
        if not download_url:
            raise RuntimeError("No suitable download link (CSV/XLS/XLSX) found on ANSD page.")

        file_resp = self._http.fetch(download_url)
        if file_resp.status_code != 200:
            raise RuntimeError(f"Failed to download ANSD dataset file: {download_url}")

        content = file_resp.content
        file_hash = hashlib.sha256(content).hexdigest()

        content_type = file_resp.headers.get("Content-Type", "").lower()
        table = self._parse_table(content, content_type)

        metadata = {
            "dataset_id": dataset.id,
            "title": dataset.title,
            "description": dataset.description,
            "page_url": page_url,
            "download_url": download_url,
            "content_type": content_type,
            "source": dataset.source,
            "url": str(dataset.url),
            "updated_at": dataset.updated_at.isoformat(),
        }

        snippet = self._build_snippet(table)
        citation = Citation(
            id=dataset.id,
            title=dataset.title,
            url=HttpUrl(download_url),  # type: ignore[call-arg]
            accessed_at=datetime.now(UTC),
            snippet=snippet,
            source_id=dataset.id,
            file_hash=file_hash,
        )

        return SeriesTable(
            columns=table.columns,
            rows=table.rows,
            metadata=metadata,
            citations=[citation],
        )

    @staticmethod
    def _find_download_link(soup: BeautifulSoup, base_url: str) -> str | None:
        # Prefer explicit CSV/XLS/XLSX links by inspecting anchor text and href.
        candidates: list[str] = []
        for link in soup.find_all("a"):
            href = link.get("href") or ""
            text = (link.get_text() or "").lower()
            href_lower = href.lower()
            download_phrases = (
                "download csv",
                "télécharger csv",
                "download xls",
                "download xlsx",
            )
            if any(ext in href_lower for ext in (".csv", ".xls", ".xlsx")) or any(
                phrase in text for phrase in download_phrases
            ):
                candidates.append(href)

        if not candidates:
            return None

        # Use the first candidate; the shared HTTP client enforces allowlist and safety.
        from urllib.parse import urljoin

        return urljoin(base_url, candidates[0])

    @staticmethod
    def _parse_table(content: bytes, content_type: str) -> SeriesTable:
        # Very lightweight content-type inspection; rely on extension hints when available.
        if "csv" in content_type:
            return AnsdDownloadAdapter._parse_csv(content)
        if "excel" in content_type or "spreadsheetml" in content_type:
            return AnsdDownloadAdapter._parse_excel(content)

        # Fallback: try CSV first, then Excel.
        try:
            return AnsdDownloadAdapter._parse_csv(content)
        except Exception:
            return AnsdDownloadAdapter._parse_excel(content)

    @staticmethod
    def _parse_csv(content: bytes) -> SeriesTable:
        text = content.decode("utf-8", errors="replace")
        reader = csv.reader(StringIO(text))
        rows = list(reader)
        if not rows:
            return SeriesTable(columns=[], rows=[])
        headers = rows[0]
        data_rows = rows[1:]
        columns = [SeriesColumn(name=h, type="string") for h in headers]
        return SeriesTable(columns=columns, rows=data_rows)

    @staticmethod
    def _parse_excel(content: bytes) -> SeriesTable:
        # Read only the first sheet, with conservative row/column limits.
        with pd.ExcelFile(content) as xf:
            sheet_name = xf.sheet_names[0]
            df = pd.read_excel(xf, sheet_name=sheet_name, nrows=5000)
        df = df.fillna("")
        columns = [SeriesColumn(name=str(col), type="string") for col in df.columns]
        rows: list[list[Any]] = df.astype(str).values.tolist()
        return SeriesTable(columns=columns, rows=rows)

    @staticmethod
    def _build_snippet(table: SeriesTable) -> str | None:
        if not table.columns or not table.rows:
            return None
        header = [col.name for col in table.columns]
        first_row = [str(v) for v in table.rows[0]]
        snippet = f"Headers: {', '.join(header)}; First row: {', '.join(first_row)}"
        if len(snippet) > 300:
            return snippet[:297] + "..."
        return snippet

