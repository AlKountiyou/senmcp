from __future__ import annotations

from mcp_core.models.datasets import IndicatorExplanation
from mcp_opendata.domain.repositories import IndicatorRepository


class ExplainIndicatorUseCase:
    def __init__(self, repo: IndicatorRepository) -> None:
        self._repo = repo

    def execute(self, indicator_name: str, context: str | None = None) -> IndicatorExplanation:
        return self._repo.explain_indicator(indicator_name=indicator_name, context=context)
