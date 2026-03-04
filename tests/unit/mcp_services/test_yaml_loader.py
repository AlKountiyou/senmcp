from __future__ import annotations

from pathlib import Path

from mcp_services.adapters.yaml_repository import YamlServiceRepository


def test_yaml_repository_loads_services(tmp_path: Path) -> None:
    content = """
id: test_service
title: Test service
description: Demo
category: demo
requirements:
  summary: Test
  profile_keys: ["foo"]
documents: []
steps: []
fees: Gratuit
official_sources: []
"""
    catalog_dir = tmp_path / "services_catalog"
    catalog_dir.mkdir()
    (catalog_dir / "test_service.yml").write_text(content, encoding="utf-8")

    repo = YamlServiceRepository(catalog_dir)
    service = repo.get_service("test_service")
    assert service.id == "test_service"
    assert repo.list_services(category="demo")[0].id == "test_service"
