from __future__ import annotations

import os

import httpx
import pytest
from mcp_core.config import get_settings
from mcp_core.http_client import HttpClient


def _reset_settings_env(env: dict[str, str]) -> None:
    os.environ.update(env)
    # Clear cached settings so changes take effect.
    get_settings.cache_clear()  # type: ignore[attr-defined]


def test_http_client_validate_url_respects_scheme_and_allowlist() -> None:
    _reset_settings_env({"ALLOWLIST_DOMAINS": '["example.org"]'})
    client = HttpClient()

    # Allowed: https + allowlisted domain.
    client._validate_url("https://example.org/resource")  # type: ignore[attr-defined]

    # Block non-HTTP schemes.
    with pytest.raises(ValueError):
        client._validate_url("ftp://example.org/resource")  # type: ignore[attr-defined]

    # Block domains not in allowlist.
    with pytest.raises(ValueError):
        client._validate_url("https://other.com/resource")  # type: ignore[attr-defined]


def test_http_client_enforces_max_bytes_limit() -> None:
    _reset_settings_env(
            {
                "ALLOWLIST_DOMAINS": '["example.org"]',
                "HTTP_MAX_BYTES": "10",
            }
    )
    client = HttpClient()

    # Replace underlying client with a mock transport that returns more than 10 bytes.
    def handler(request: httpx.Request) -> httpx.Response:  # type: ignore[override]
        return httpx.Response(200, text="x" * 20)

    transport = httpx.MockTransport(handler)  # type: ignore[arg-type]
    client._client = httpx.Client(transport=transport, timeout=client._timeout)  # type: ignore[attr-defined]

    with pytest.raises(httpx.HTTPError):
        client.fetch("https://example.org/resource")

