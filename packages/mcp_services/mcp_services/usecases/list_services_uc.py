from __future__ import annotations

from mcp_core.models.services import Service
from mcp_services.adapters.yaml_repository import YamlServiceRepository


class ListServicesUseCase:
    def __init__(self, repo: YamlServiceRepository) -> None:
        self._repo = repo

    def execute(self, category: str | None = None) -> list[Service]:
        return self._repo.list_services(category=category)
