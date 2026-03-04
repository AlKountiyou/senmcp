from __future__ import annotations

from functools import lru_cache
from typing import Any

from mcp.server.fastmcp import FastMCP
from mcp_core.config import get_settings as get_core_settings
from mcp_trust.audit import JsonlAuditLogger
from mcp_trust.provenance import ProvenanceManager
from mcp_trust.server_middleware import with_trust_safety

from mcp_services.adapters.yaml_repository import YamlServiceRepository
from mcp_services.config import get_settings as get_services_settings
from mcp_services.usecases.eligibility_check_uc import EligibilityCheckUseCase
from mcp_services.usecases.get_service_uc import GetServiceUseCase
from mcp_services.usecases.list_services_uc import ListServicesUseCase
from mcp_services.usecases.required_documents_uc import RequiredDocumentsUseCase
from mcp_services.usecases.steps_uc import StepsUseCase

mcp = FastMCP("SenCivic Services MCP Server", json_response=True)


@lru_cache(maxsize=1)
def _build_dependencies() -> dict[str, Any]:
    core_settings = get_core_settings()
    services_settings = get_services_settings()
    repo = YamlServiceRepository(services_settings.catalog_dir)
    provenance = ProvenanceManager()
    audit_logger = JsonlAuditLogger(core_settings.audit_services_path)
    return {
        "repo": repo,
        "provenance": provenance,
        "audit_logger": audit_logger,
    }


@mcp.tool()
async def list_services(category: str | None = None) -> dict[str, Any]:
    """List services, optionally filtered by category."""

    deps = _build_dependencies()
    usecase = ListServicesUseCase(deps["repo"])

    async def handler(params: dict[str, Any], ctx: Any) -> dict[str, Any]:
        services = usecase.execute(category=params.get("category"))
        return {
            "text": f"{len(services)} service(s) found.",
            "structuredContent": {"services": [s.model_dump() for s in services]},
        }

    return await with_trust_safety(
        tool_name="services.list_services",
        params={"category": category},
        handler=handler,
        audit_logger=deps["audit_logger"],
        provenance_manager=deps["provenance"],
    )


@mcp.tool()
async def get_service(service_id: str) -> dict[str, Any]:
    """Retrieve a specific service by identifier."""

    deps = _build_dependencies()
    usecase = GetServiceUseCase(deps["repo"])

    async def handler(params: dict[str, Any], ctx: Any) -> dict[str, Any]:
        service = usecase.execute(service_id=params["service_id"])
        return {
            "text": f"Service {service.id}: {service.title}",
            "structuredContent": {"service": service.model_dump()},
        }

    return await with_trust_safety(
        tool_name="services.get_service",
        params={"service_id": service_id},
        handler=handler,
        audit_logger=deps["audit_logger"],
        provenance_manager=deps["provenance"],
    )


@mcp.tool()
async def eligibility_check(service_id: str, profile: dict[str, Any]) -> dict[str, Any]:
    """Check basic eligibility for a service given a user profile."""

    deps = _build_dependencies()
    usecase = EligibilityCheckUseCase(deps["repo"])

    async def handler(params: dict[str, Any], ctx: Any) -> dict[str, Any]:
        result = usecase.execute(service_id=params["service_id"], profile=params.get("profile", {}))
        text = "Eligible." if result.eligible else "Not eligible."
        return {
            "text": f"{text} Reasons: {'; '.join(result.reasons) if result.reasons else 'None'}",
            "structuredContent": {"eligibility": result.model_dump()},
        }

    # NOTE: server-side audit logger will hash and minimize profile content as per design.
    return await with_trust_safety(
        tool_name="services.eligibility_check",
        params={"service_id": service_id, "profile": profile},
        handler=handler,
        audit_logger=deps["audit_logger"],
        provenance_manager=deps["provenance"],
    )


@mcp.tool()
async def required_documents(service_id: str) -> dict[str, Any]:
    """List required documents for a service."""

    deps = _build_dependencies()
    usecase = RequiredDocumentsUseCase(deps["repo"])

    async def handler(params: dict[str, Any], ctx: Any) -> dict[str, Any]:
        docs = usecase.execute(service_id=params["service_id"])
        return {
            "text": f"{len(docs)} document(s) required.",
            "structuredContent": {"documents": [d.model_dump() for d in docs]},
        }

    return await with_trust_safety(
        tool_name="services.required_documents",
        params={"service_id": service_id},
        handler=handler,
        audit_logger=deps["audit_logger"],
        provenance_manager=deps["provenance"],
    )


@mcp.tool()
async def steps(service_id: str) -> dict[str, Any]:
    """List the ordered steps for obtaining a service."""

    deps = _build_dependencies()
    usecase = StepsUseCase(deps["repo"])

    async def handler(params: dict[str, Any], ctx: Any) -> dict[str, Any]:
        steps_list = usecase.execute(service_id=params["service_id"])
        return {
            "text": f"{len(steps_list)} step(s) for service {params['service_id']}.",
            "structuredContent": {"steps": [s.model_dump() for s in steps_list]},
        }

    return await with_trust_safety(
        tool_name="services.steps",
        params={"service_id": service_id},
        handler=handler,
        audit_logger=deps["audit_logger"],
        provenance_manager=deps["provenance"],
    )


def main() -> None:
    core = get_core_settings()
    if core.run_mode == "docker":
        mcp.run(
            transport="streamable-http",
            host=core.mcp_http_host,
            port=core.mcp_http_port,
            path=core.mcp_http_path,
        )  # type: ignore[call-arg]
    else:
        mcp.run()


if __name__ == "__main__":
    main()
