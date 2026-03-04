from __future__ import annotations

from mcp_core.models.services import ServiceStep
from mcp_services.adapters.yaml_repository import YamlServiceRepository


class StepsUseCase:
    def __init__(self, repo: YamlServiceRepository) -> None:
        self._repo = repo

    def execute(self, service_id: str) -> list[ServiceStep]:
        return self._repo.steps(service_id=service_id)
