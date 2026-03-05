from __future__ import annotations

import json
import os
from pathlib import Path

import httpx
import mcp_core.http_client as http_client_mod
import pytest
import respx
from mcp_core.config import get_settings
from mcp_opendata.adapters.ansd.ckan_agridata import CkanAgriDataAdapter
from mcp_opendata.adapters.ansd.download_adapter import AnsdDownloadAdapter
from mcp_opendata.adapters.ansd.web_catalog import AnsdWebCatalogAdapter

pytestmark = pytest.mark.filterwarnings(
    "ignore:The 'strip_cdata' option of HTMLParser.*:DeprecationWarning"
)


def _reset_core_settings(env: dict[str, str]) -> None:
    os.environ.update(env)
    # Clear cached settings and HTTP client singleton so tests see fresh config.
    get_settings.cache_clear()  # type: ignore[attr-defined]
    http_client_mod._client_instance = None  # type: ignore[attr-defined]


@respx.mock
def test_ansd_html_and_csv_flow(tmp_path: Path) -> None:
    _reset_core_settings({"ALLOWLIST_DOMAINS": '["ansd.sn","agridata.ansd.sn"]'})

    # Mock ANSD listings and dataset page + CSV.
    bases_html = """
    <html><body>
      <a href="/donnees-recensements">Population Dakar</a>
    </body></html>
    """
    page_html = """
    <html><body>
      <a href="https://www.ansd.sn/files/population_dakar.csv">Download CSV</a>
    </body></html>
    """
    csv_body = "year,population\n2020,100\n2021,110\n"

    respx.get("https://www.ansd.sn/bases-de-donnees").mock(
        return_value=httpx.Response(200, text=bases_html)
    )
    respx.get("https://www.ansd.sn/toutes-les-publications").mock(
        return_value=httpx.Response(200, text="<html></html>")
    )
    respx.get("https://www.ansd.sn/donnees-recensements").mock(
        return_value=httpx.Response(200, text=page_html)
    )
    respx.get("https://www.ansd.sn/files/population_dakar.csv").mock(
        return_value=httpx.Response(
            200,
            content=csv_body.encode("utf-8"),
            headers={"Content-Type": "text/csv"},
        )
    )

    catalog = AnsdWebCatalogAdapter(cache_dir=tmp_path / "ansd_cache")
    results = catalog.search("Population", limit=5)
    assert results
    ansd_item = next(item for item in results if item.id.startswith("ansd:web:"))
    assert ansd_item.source == "ANSD Portal"

    downloader = AnsdDownloadAdapter(catalog)
    table = downloader.fetch_table(ansd_item.id, filters=None)
    assert table.columns
    assert table.rows
    assert table.citations
    citation = table.citations[0]
    assert str(citation.url).endswith("population_dakar.csv")
    assert citation.file_hash is not None
    assert citation.accessed_at is not None
    assert citation.snippet is None or len(citation.snippet) <= 300


@respx.mock
def test_ckan_package_search_and_download(tmp_path: Path) -> None:
    _reset_core_settings({"ALLOWLIST_DOMAINS": '["ansd.sn","agridata.ansd.sn"]'})

    # Mock CKAN package_search and package_show plus resource download.
    package_search_payload = {
        "success": True,
        "result": {
            "results": [
                {
                    "name": "agri_pkg",
                    "title": "Agriculture Dataset",
                    "metadata_modified": "2024-01-01T00:00:00+00:00",
                    "notes": "Demo package",
                    "resources": [
                        {
                            "id": "res123",
                            "name": "Yield",
                            "description": "Yields by year",
                            "url": "https://agridata.ansd.sn/dataset/agri_pkg/resource/res123",
                            "format": "CSV",
                        }
                    ],
                }
            ]
        },
    }
    package_show_payload = package_search_payload | {
        "result": package_search_payload["result"]["results"][0]  # type: ignore[index]
    }
    csv_body = "year,yield\n2020,10\n2021,12\n"

    respx.get("https://agridata.ansd.sn/api/3/action/package_search").mock(
        return_value=httpx.Response(
            200,
            content=json.dumps(package_search_payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
    )
    respx.get("https://agridata.ansd.sn/api/3/action/package_show").mock(
        return_value=httpx.Response(
            200,
            content=json.dumps(package_show_payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
    )
    respx.get("https://agridata.ansd.sn/dataset/agri_pkg/resource/res123").mock(
        return_value=httpx.Response(
            200,
            content=csv_body.encode("utf-8"),
            headers={"Content-Type": "text/csv"},
        )
    )

    adapter = CkanAgriDataAdapter()
    items = adapter.search("agriculture", limit=5)
    assert items
    ckan_item = next(item for item in items if item.id.startswith("ckan:agridata:"))
    assert ckan_item.source == "ANSD AgriData (CKAN)"

    table = adapter.fetch_table(ckan_item.id, filters=None)
    assert table.columns
    assert table.rows
    assert table.citations
    citation = table.citations[0]
    assert citation.url.host == "agridata.ansd.sn"  # type: ignore[attr-defined]
    assert citation.file_hash is not None
    assert citation.snippet is None or len(citation.snippet) <= 300

