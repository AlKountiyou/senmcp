from __future__ import annotations

from pathlib import Path

from mcp_core.models.services import Service, ServiceDocument, ServiceEligibilityResult, ServiceStep
from mcp_services.adapters.yaml_repository import YamlServiceRepository
from mcp_services.usecases.eligibility_check_uc import EligibilityCheckUseCase
from mcp_services.usecases.get_service_uc import GetServiceUseCase
from mcp_services.usecases.list_services_uc import ListServicesUseCase
from mcp_services.usecases.required_documents_uc import RequiredDocumentsUseCase
from mcp_services.usecases.steps_uc import StepsUseCase


def _catalog_dir() -> Path:
    # tests live under `<root>/tests/...`, so `parents[2]` is the workspace root
    return Path(__file__).parents[2] / "data" / "services_catalog"


def test_services_contract() -> None:
    repo = YamlServiceRepository(_catalog_dir())
    list_uc = ListServicesUseCase(repo)
    get_uc = GetServiceUseCase(repo)
    docs_uc = RequiredDocumentsUseCase(repo)
    steps_uc = StepsUseCase(repo)
    elig_uc = EligibilityCheckUseCase(repo)

    services = list_uc.execute(category=None)
    assert services
    s0 = services[0]
    assert isinstance(s0, Service)

    service = get_uc.execute(s0.id)
    assert isinstance(service, Service)

    docs = docs_uc.execute(s0.id)
    assert all(isinstance(d, ServiceDocument) for d in docs)

    steps = steps_uc.execute(s0.id)
    assert all(isinstance(st, ServiceStep) for st in steps)

    elig = elig_uc.execute(s0.id, profile={})
    assert isinstance(elig, ServiceEligibilityResult)
