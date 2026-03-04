from __future__ import annotations

from pydantic import BaseModel, HttpUrl

from .citations import Citation


class ServiceDocument(BaseModel):
    name: str
    description: str
    required: bool = True


class ServiceStep(BaseModel):
    order: int
    title: str
    description: str


class ServiceRequirements(BaseModel):
    summary: str
    profile_keys: list[str] = []


class OfficialSource(BaseModel):
    label: str
    url: HttpUrl
    last_checked: str


class Service(BaseModel):
    id: str
    title: str
    description: str
    category: str
    requirements: ServiceRequirements
    documents: list[ServiceDocument]
    steps: list[ServiceStep]
    fees: str
    official_sources: list[OfficialSource]
    citations: list[Citation] = []


class ServiceEligibilityResult(BaseModel):
    service_id: str
    eligible: bool
    reasons: list[str]
