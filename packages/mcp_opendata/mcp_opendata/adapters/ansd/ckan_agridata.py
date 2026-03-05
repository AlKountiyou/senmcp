from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urljoin

from mcp_core.http_client import get_http_client
from mcp_core.models.citations import Citation
from mcp_core.models.datasets import DatasetItem, SeriesColumn, SeriesTable
from mcp_opendata.domain.repositories import CkanCatalogPort, CkanTablePort
from pydantic import HttpUrl


class CkanAgriDataAdapter(CkanCatalogPort, CkanTablePort):
    """CKAN adapter for ANSD AgriData (https://agridata.ansd.sn/)."""

    BASE_URL = "https://agridata.ansd.sn/"
    API_BASE = urljoin(BASE_URL, "api/3/action/")

    def __init__(self) -> None:
        self._http = get_http_client()

    # Catalog port

    def search(self, query: str, limit: int = 10) -> list[DatasetItem]:
        packages = self._package_search(query=query, rows=limit)
        items: list[DatasetItem] = []
        for pkg in packages:
            package_name = pkg.get("name") or pkg.get("id")
            if not package_name:
                continue
            pkg_title = pkg.get("title") or package_name
            pkg_desc = pkg.get("notes") or ""
            pkg_updated_raw = (
                pkg.get("metadata_modified")
                or pkg.get("metadata_created")
                or datetime.fromtimestamp(0, tz=UTC).isoformat()
            )
            try:
                pkg_updated_at = datetime.fromisoformat(pkg_updated_raw)
            except Exception:
                pkg_updated_at = datetime.fromtimestamp(0, tz=UTC)

            for res in pkg.get("resources", []):
                res_id = res.get("id")
                if not res_id:
                    continue
                res_name = res.get("name") or res_id
                res_desc = res.get("description") or pkg_desc
                res_url = res.get("url") or urljoin(
                    self.BASE_URL,
                    f"dataset/{package_name}/resource/{res_id}",
                )
                dataset_id = f"ckan:agridata:{package_name}:{res_id}"
                url_value = HttpUrl(res_url)  # type: ignore[call-arg]
                item = DatasetItem(
                    id=dataset_id,
                    title=f"{pkg_title} – {res_name}",
                    description=res_desc,
                    source="ANSD AgriData (CKAN)",
                    url=url_value,
                    updated_at=pkg_updated_at,
                )
                items.append(item)
        return items

    def get_dataset(self, dataset_id: str) -> DatasetItem:
        package_name, resource_id = self._parse_dataset_id(dataset_id)
        pkg = self._package_show(package_name)
        pkg_title = pkg.get("title") or package_name
        pkg_desc = pkg.get("notes") or ""
        pkg_updated_raw = (
            pkg.get("metadata_modified")
            or pkg.get("metadata_created")
            or datetime.fromtimestamp(0, tz=UTC).isoformat()
        )
        try:
            pkg_updated_at = datetime.fromisoformat(pkg_updated_raw)
        except Exception:
            pkg_updated_at = datetime.fromtimestamp(0, tz=UTC)

        res = next((r for r in pkg.get("resources", []) if r.get("id") == resource_id), None)
        if res is None:
            raise KeyError(f"CKAN resource not found for dataset_id={dataset_id}")
        res_name = res.get("name") or resource_id
        res_desc = res.get("description") or pkg_desc
        res_url = res.get("url") or urljoin(
            self.BASE_URL,
            f"dataset/{package_name}/resource/{resource_id}",
        )
        try:
            url_value = HttpUrl(res_url)  # type: ignore[call-arg]
        except Exception as exc:
            raise ValueError(f"Invalid CKAN resource URL: {res_url}") from exc

        return DatasetItem(
            id=dataset_id,
            title=f"{pkg_title} – {res_name}",
            description=res_desc,
            source="ANSD AgriData (CKAN)",
            url=url_value,
            updated_at=pkg_updated_at,
        )

    def list_resources(self, dataset_id: str) -> list[dict[str, Any]]:
        package_name, _ = self._parse_dataset_id(dataset_id)
        pkg = self._package_show(package_name)
        return list(pkg.get("resources", []))

    # Table port

    def fetch_table(self, dataset_id: str, filters: dict[str, Any] | None = None) -> SeriesTable:
        package_name, resource_id = self._parse_dataset_id(dataset_id)
        pkg = self._package_show(package_name)
        res = next((r for r in pkg.get("resources", []) if r.get("id") == resource_id), None)
        if res is None:
            raise KeyError(f"CKAN resource not found for dataset_id={dataset_id}")

        download_url = res.get("url") or urljoin(
            self.BASE_URL,
            f"dataset/{package_name}/resource/{resource_id}",
        )
        resp = self._http.fetch(download_url)
        if resp.status_code != 200:
            raise RuntimeError(f"Failed to download CKAN resource: {download_url}")

        content = resp.content
        file_hash = hashlib.sha256(content).hexdigest()
        content_type = resp.headers.get("Content-Type", "").lower()
        table = self._parse_resource(content, content_type)

        pkg_title = pkg.get("title") or package_name
        res_name = res.get("name") or resource_id
        metadata = {
            "dataset_id": dataset_id,
            "package_name": package_name,
            "resource_id": resource_id,
            "title": f"{pkg_title} – {res_name}",
            "description": res.get("description") or pkg.get("notes") or "",
            "resource_format": (res.get("format") or "").upper(),
            "resource_url": download_url,
            "source": "ANSD AgriData (CKAN)",
        }

        snippet = self._build_snippet(table)
        citation = Citation(
            id=dataset_id,
            title=metadata["title"],
            url=HttpUrl(download_url),  # type: ignore[call-arg]
            accessed_at=datetime.now(UTC),
            snippet=snippet,
            source_id=dataset_id,
            file_hash=file_hash,
        )

        return SeriesTable(
            columns=table.columns,
            rows=table.rows,
            metadata=metadata,
            citations=[citation],
        )

    # Internal helpers

    def _package_search(self, query: str, rows: int) -> list[dict[str, Any]]:
        url = urljoin(self.API_BASE, "package_search")
        import json
        from urllib.parse import urlencode

        q_url = f"{url}?{urlencode({'q': query, 'rows': rows})}"
        resp = self._http.fetch(q_url, method="GET", headers=None, use_cache=True)
        if resp.status_code != 200:
            return []
        payload = json.loads(resp.content.decode("utf-8", errors="replace"))
        if not payload.get("success"):
            return []
        result = payload.get("result") or {}
        return list(result.get("results", []))

    def _package_show(self, package_name: str) -> dict[str, Any]:
        url = urljoin(self.API_BASE, "package_show")
        # CKAN allows GET with ?id=...
        from urllib.parse import urlencode

        q_url = f"{url}?{urlencode({'id': package_name})}"
        resp = self._http.fetch(q_url, method="GET", headers=None, use_cache=True)
        if resp.status_code != 200:
            raise RuntimeError(f"Failed to fetch CKAN package_show for {package_name}")
        import json

        payload = json.loads(resp.content.decode("utf-8", errors="replace"))
        if not payload.get("success"):
            raise RuntimeError(f"CKAN package_show unsuccessful for {package_name}")
        return payload.get("result") or {}

    @staticmethod
    def _parse_dataset_id(dataset_id: str) -> tuple[str, str]:
        # Expected pattern: ckan:agridata:<package_name>:<resource_id>
        parts = dataset_id.split(":", 3)
        if len(parts) != 4 or parts[0] != "ckan" or parts[1] != "agridata":
            raise ValueError(f"Invalid CKAN dataset_id format: {dataset_id}")
        return parts[2], parts[3]

    @staticmethod
    def _parse_resource(content: bytes, content_type: str) -> SeriesTable:
        if "csv" in content_type:
            return CkanAgriDataAdapter._parse_csv(content)
        if "json" in content_type or content_type.endswith("+json"):
            return CkanAgriDataAdapter._parse_json(content)
        # Fallback: try CSV then JSON.
        try:
            return CkanAgriDataAdapter._parse_csv(content)
        except Exception:
            return CkanAgriDataAdapter._parse_json(content)

    @staticmethod
    def _parse_csv(content: bytes) -> SeriesTable:
        import csv
        from io import StringIO

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
    def _parse_json(content: bytes) -> SeriesTable:
        import json

        data = json.loads(content.decode("utf-8", errors="replace"))
        if isinstance(data, dict):
            # CKAN datastore_search style: records under "result.records"
            if (
                "result" in data
                and isinstance(data["result"], dict)
                and "records" in data["result"]
            ):
                records = data["result"]["records"]
            else:
                records = [data]
        else:
            records = data

        if not records:
            return SeriesTable(columns=[], rows=[])

        # Normalize list[dict] into table.
        if isinstance(records, list) and isinstance(records[0], dict):
            columns_names = sorted({key for row in records for key in row.keys()})
            columns = [SeriesColumn(name=str(name), type="string") for name in columns_names]
            rows: list[list[Any]] = []
            for row in records:
                rows.append([str(row.get(col, "")) for col in columns_names])
            return SeriesTable(columns=columns, rows=rows)

        # Fallback: treat as single-column string rows.
        columns = [SeriesColumn(name="value", type="string")]
        rows = [[str(record)] for record in records]
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

