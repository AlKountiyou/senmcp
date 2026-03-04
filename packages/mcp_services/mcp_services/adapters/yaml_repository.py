from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from mcp_core.models.services import (
    OfficialSource,
    Service,
    ServiceDocument,
    ServiceEligibilityResult,
    ServiceRequirements,
    ServiceStep,
)


class YamlServiceRepository:
    """Loads and validates a YAML-based service catalog."""

    def __init__(self, catalog_dir: Path) -> None:
        self._catalog_dir = catalog_dir
        self._services: dict[str, Service] = {}
        self._load()

    def _load(self) -> None:
        if not self._catalog_dir.exists():
            return
        for path in sorted(self._catalog_dir.glob("*.yml")) + sorted(
            self._catalog_dir.glob("*.yaml")
        ):
            with path.open("r", encoding="utf-8") as f:
                raw = yaml.safe_load(f) or {}
            service = self._parse_service(raw)
            self._services[service.id] = service

    @staticmethod
    def _parse_service(raw: dict[str, Any]) -> Service:
        documents = [ServiceDocument(**d) for d in raw.get("documents", [])]
        steps = [ServiceStep(**s) for s in raw.get("steps", [])]
        requirements = ServiceRequirements(**raw.get("requirements", {}))
        sources = [OfficialSource(**s) for s in raw.get("official_sources", [])]
        return Service(
            id=raw["id"],
            title=raw["title"],
            description=raw.get("description", ""),
            category=raw.get("category", ""),
            requirements=requirements,
            documents=documents,
            steps=steps,
            fees=raw.get("fees", ""),
            official_sources=sources,
        )

    def list_services(self, category: str | None = None) -> list[Service]:
        values = list(self._services.values())
        if category:
            values = [s for s in values if s.category == category]
        return values

    def get_service(self, service_id: str) -> Service:
        try:
            return self._services[service_id]
        except KeyError as exc:
            raise KeyError(f"Service not found: {service_id}") from exc

    def eligibility_check(
        self, service_id: str, profile: dict[str, Any]
    ) -> ServiceEligibilityResult:
        service = self.get_service(service_id)
        required_keys = set(service.requirements.profile_keys)
        profile_keys = set(profile.keys())
        missing = sorted(required_keys - profile_keys)
        reasons: list[str] = []
        if missing:
            reasons.append(f"Missing profile keys: {', '.join(missing)}")
        eligible = not missing
        return ServiceEligibilityResult(service_id=service_id, eligible=eligible, reasons=reasons)

    def required_documents(self, service_id: str) -> list[ServiceDocument]:
        return self.get_service(service_id).documents

    def steps(self, service_id: str) -> list[ServiceStep]:
        return sorted(self.get_service(service_id).steps, key=lambda s: s.order)
