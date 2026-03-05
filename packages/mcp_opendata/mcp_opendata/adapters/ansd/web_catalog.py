from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup  # type: ignore[import-untyped]
from mcp_core.http_client import get_http_client
from mcp_core.models.datasets import DatasetItem
from mcp_opendata.domain.repositories import AnsdCatalogPort
from pydantic import HttpUrl


class AnsdWebCatalogAdapter(AnsdCatalogPort):
    """HTML-based catalog adapter for ANSD portal pages.

    This adapter is intentionally conservative and defensive: it relies on the
    shared HTTP client for safety, and keeps a small on-disk cache of parsed
    dataset metadata to respect ANSD's robots/terms.
    """

    BASE_URL = "https://www.ansd.sn"
    DATABASES_PATH = "/bases-de-donnees"
    PUBLICATIONS_PATH = "/toutes-les-publications"

    def __init__(self, cache_dir: Path | None = None) -> None:
        self._http = get_http_client()
        self._cache_dir = cache_dir or Path(".cache") / "ansd"
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        self._catalog_path = self._cache_dir / "catalog.json"
        self._catalog_ttl_seconds = 86_400
        self._datasets: dict[str, DatasetItem] = {}
        self._loaded_at: float | None = None

    def search(self, query: str, limit: int = 10) -> list[DatasetItem]:
        self._ensure_catalog()
        q = query.lower()
        tokens = [t for t in q.split() if t]
        if not tokens:
            return []

        results: list[DatasetItem] = []
        for item in self._datasets.values():
            text = f"{item.title} {item.description}".lower()
            if all(token in text for token in tokens):
                results.append(item)
            if len(results) >= limit:
                break
        return results

    def get_dataset(self, dataset_id: str) -> DatasetItem:
        self._ensure_catalog()
        try:
            return self._datasets[dataset_id]
        except KeyError as exc:
            raise KeyError(f"ANSD dataset not found: {dataset_id}") from exc

    # Internal helpers

    def _ensure_catalog(self) -> None:
        now = datetime.now(UTC).timestamp()
        if self._datasets and self._loaded_at is not None:
            if now - self._loaded_at < self._catalog_ttl_seconds:
                return
        if self._catalog_path.exists():
            try:
                raw = json.loads(self._catalog_path.read_text(encoding="utf-8"))
                datasets = {}
                for item_raw in raw.get("datasets", []):
                    datasets[item_raw["id"]] = DatasetItem(
                        id=item_raw["id"],
                        title=item_raw["title"],
                        description=item_raw.get("description", ""),
                        source=item_raw.get("source", "ANSD Portal"),
                        url=item_raw["url"],
                        updated_at=datetime.fromisoformat(item_raw["updated_at"]),
                    )
                self._datasets = datasets
                self._loaded_at = float(raw.get("generated_at", now))
                if now - self._loaded_at < self._catalog_ttl_seconds:
                    return
            except Exception:
                # Fall through to fresh rebuild on parse errors.
                self._datasets = {}

        self._rebuild_catalog()

    def _rebuild_catalog(self) -> None:
        datasets: dict[str, DatasetItem] = {}
        # Databases listing
        db_items = self._fetch_listing(self.DATABASES_PATH, kind="web")
        datasets.update({item.id: item for item in db_items})
        # Publications listing (treated as potential tabular PDFs or linked datasets)
        pub_items = self._fetch_listing(self.PUBLICATIONS_PATH, kind="pub")
        for item in pub_items:
            if item.id not in datasets:
                datasets[item.id] = item

        self._datasets = datasets
        now = datetime.now(UTC).timestamp()
        self._loaded_at = now
        serialized = {
            "generated_at": now,
            "datasets": [
                {
                    "id": item.id,
                    "title": item.title,
                    "description": item.description,
                    "source": item.source,
                    "url": str(item.url),
                    "updated_at": item.updated_at.isoformat(),
                }
                for item in self._datasets.values()
            ],
        }
        self._catalog_path.write_text(json.dumps(serialized), encoding="utf-8")

    def _fetch_listing(self, path: str, *, kind: str) -> list[DatasetItem]:
        url = urljoin(self.BASE_URL, path)
        resp = self._http.fetch(url)
        if resp.status_code != 200:
            return []

        soup = BeautifulSoup(resp.content, "lxml")
        items: list[DatasetItem] = []

        # The exact CSS classes may evolve; we keep the parsing defensive by
        # looking for common card/link patterns.
        for link in soup.select("a"):
            href = link.get("href") or ""
            text = link.get_text(strip=True)
            if not href or not text:
                continue
            full_url = urljoin(self.BASE_URL, href)
            parsed = urlparse(full_url)
            if not parsed.path.startswith("/"):
                continue

            slug = parsed.path.rstrip("/").split("/")[-1].lower()
            if not slug:
                continue

            if kind == "web":
                dataset_id = f"ansd:web:{slug}"
            elif kind == "pub":
                dataset_id = f"ansd:pub:{slug}"
            else:
                continue

            title = text
            description = ""

            url_value = HttpUrl(full_url)  # type: ignore[call-arg]

            item = DatasetItem(
                id=dataset_id,
                title=title,
                description=description,
                source="ANSD Portal",
                url=url_value,
                updated_at=datetime.fromtimestamp(0, tz=UTC),
            )
            items.append(item)

        return items

