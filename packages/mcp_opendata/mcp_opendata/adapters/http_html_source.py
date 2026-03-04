from __future__ import annotations

from datetime import UTC, datetime
from typing import cast

import httpx
from mcp_core.models.citations import Citation
from mcp_trust.policies import UrlSafety, build_default_allowlist_policy
from pydantic import HttpUrl


class HttpHtmlSource:
    """Optional HTTP HTML source for enriching citations.

    This adapter respects SourceAllowlistPolicy and UrlSafety to avoid SSRF
    and only accesses approved domains.
    """

    def __init__(self, timeout_seconds: float, max_bytes: int) -> None:
        self._timeout = timeout_seconds
        self._max_bytes = max_bytes
        self._allowlist = build_default_allowlist_policy()

    async def fetch_citation(self, url: str, title: str | None = None) -> Citation:
        if not UrlSafety.is_safe(url) or not self._allowlist.is_allowed(url):
            raise ValueError("URL not allowed by safety or allowlist policy.")

        async with httpx.AsyncClient(timeout=self._timeout, follow_redirects=True) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            content = resp.text[: self._max_bytes]

        snippet = content[:300].replace("\n", " ").strip()
        title_value = title or url
        url_value = cast("HttpUrl", url)
        return Citation(
            id=url,
            title=title_value,
            url=url_value,
            accessed_at=datetime.now(UTC),
            snippet=snippet,
            source_id=url,
        )
