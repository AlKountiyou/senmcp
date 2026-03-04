from __future__ import annotations

from mcp_core.models.services import ServiceDocument
from mcp_services.adapters.yaml_repository import YamlServiceRepository


class RequiredDocumentsUseCase:
    def __init__(self, repo: YamlServiceRepository) -> None:
        self._repo = repo

    def execute(self, service_id: str) -> list[ServiceDocument]:
        return self._repo.required_documents(service_id=service_id)
