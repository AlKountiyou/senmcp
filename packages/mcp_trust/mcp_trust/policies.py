from __future__ import annotations

import ipaddress
from collections.abc import Iterable
from dataclasses import dataclass
from urllib.parse import urlparse

from mcp_core.config import get_settings
from pydantic import BaseModel

NETWORKED_TOOLS: set[str] = set()


class PromptInjectionResult(BaseModel):
    score: float
    reasons: list[str]

    @property
    def is_suspicious(self) -> bool:
        # In this MVP, any single strong heuristic match is enough to flag.
        return self.score >= 0.3


class PromptInjectionHeuristics:
    """Very lightweight prompt-injection heuristics."""

    SUSPICIOUS_PATTERNS: list[str] = [
        "ignore previous instructions",
        "ignore all previous instructions",
        "reveal the system prompt",
        "exfiltrate",
        "leak",
        "bypass safety",
    ]

    def evaluate(self, text: str) -> PromptInjectionResult:
        lowered = text.lower()
        reasons: list[str] = []
        for pattern in self.SUSPICIOUS_PATTERNS:
            if pattern in lowered:
                reasons.append(f"matched pattern: {pattern}")
        score = min(1.0, 0.3 * len(reasons))
        return PromptInjectionResult(score=score, reasons=reasons)


@dataclass
class SourceAllowlistPolicy:
    """Domain-based allowlist for outbound HTTP requests."""

    allowed_domains: Iterable[str]

    def is_allowed(self, url: str) -> bool:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return False
        host = parsed.hostname or ""
        if not host:
            return False
        normalized = host.lower()
        for domain in self.allowed_domains:
            d = domain.lower()
            if normalized == d or normalized.endswith(f".{d}"):
                return True
        return False


class UrlSafety:
    """Utility helpers for basic SSRF and URL safety checks."""

    PRIVATE_NETWORKS = [
        ipaddress.ip_network("127.0.0.0/8"),
        ipaddress.ip_network("10.0.0.0/8"),
        ipaddress.ip_network("172.16.0.0/12"),
        ipaddress.ip_network("192.168.0.0/16"),
        ipaddress.ip_network("169.254.0.0/16"),
    ]

    @classmethod
    def is_safe(cls, url: str) -> bool:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return False

        host = parsed.hostname
        if host is None:
            return False

        try:
            ip = ipaddress.ip_address(host)
        except ValueError:
            # Not an IP literal; hostnames are allowed.
            return True

        for net in cls.PRIVATE_NETWORKS:
            if ip in net:
                return False
        return True


def build_default_allowlist_policy() -> SourceAllowlistPolicy:
    settings = get_settings()
    return SourceAllowlistPolicy(allowed_domains=settings.allowlist_domains)
