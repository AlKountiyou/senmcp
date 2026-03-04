from __future__ import annotations

from typing import Any

from mcp_core.models.services import ServiceEligibilityResult
from mcp_services.adapters.yaml_repository import YamlServiceRepository


class EligibilityCheckUseCase:
    def __init__(self, repo: YamlServiceRepository) -> None:
        self._repo = repo

    def execute(self, service_id: str, profile: dict[str, Any]) -> ServiceEligibilityResult:
        return self._repo.eligibility_check(service_id=service_id, profile=profile)
