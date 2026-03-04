from __future__ import annotations

from mcp_core.models.services import Service
from mcp_services.adapters.yaml_repository import YamlServiceRepository


class GetServiceUseCase:
    def __init__(self, repo: YamlServiceRepository) -> None:
        self._repo = repo

    def execute(self, service_id: str) -> Service:
        return self._repo.get_service(service_id=service_id)
