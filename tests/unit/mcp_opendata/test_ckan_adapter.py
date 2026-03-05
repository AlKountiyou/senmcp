from __future__ import annotations

import json

import pytest
from mcp_core.models.datasets import SeriesTable
from mcp_opendata.adapters.ansd.ckan_agridata import CkanAgriDataAdapter


def test_ckan_parse_dataset_id_valid() -> None:
    package, resource = CkanAgriDataAdapter._parse_dataset_id("ckan:agridata:pkg:res")
    assert package == "pkg"
    assert resource == "res"


def test_ckan_parse_dataset_id_invalid() -> None:
    invalid_ids = [
        "ckan:other:pkg:res",
        "ckan:agridata:onlypkg",
        "notckan:agridata:pkg:res",
    ]
    for dataset_id in invalid_ids:
        with pytest.raises(ValueError):
            CkanAgriDataAdapter._parse_dataset_id(dataset_id)


def test_ckan_parse_json_records_and_snippet() -> None:
    payload = {
        "success": True,
        "result": {
            "records": [
                {"a": 1, "b": 2},
                {"a": 3, "b": 4},
            ]
        },
    }
    content = json.dumps(payload).encode("utf-8")
    table: SeriesTable = CkanAgriDataAdapter._parse_json(content)

    assert table.columns
    names = sorted(col.name for col in table.columns)
    assert names == ["a", "b"]
    assert table.rows == [["1", "2"], ["3", "4"]]

    snippet = CkanAgriDataAdapter._build_snippet(table)
    assert snippet is not None
    assert "Headers:" in snippet

