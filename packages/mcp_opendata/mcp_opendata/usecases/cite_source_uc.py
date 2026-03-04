from __future__ import annotations

from mcp_core.models.citations import Citation
from mcp_opendata.domain.repositories import CitationRepository


class CiteSourceUseCase:
    def __init__(self, repo: CitationRepository) -> None:
        self._repo = repo

    def execute(self, source_id: str) -> Citation:
        return self._repo.cite_source(source_id=source_id)
