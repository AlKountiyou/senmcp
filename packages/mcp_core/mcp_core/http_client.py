from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx
import orjson
from mcp_trust.policies import UrlSafety, build_default_allowlist_policy

from mcp_core.config import get_settings
from mcp_core.logging import get_logger


@dataclass
class HttpResponse:
    status_code: int
    headers: dict[str, str]
    content: bytes


class HttpClient:
    """Shared HTTP client with allowlist, SSRF protections, caching, and rate limiting."""

    def __init__(self) -> None:
        settings = get_settings()
        self._timeout = settings.http_timeout_seconds
        self._max_bytes = settings.http_max_bytes
        self._rate_limit_per_host = settings.http_rate_limit_per_host
        self._cache_ttl = settings.http_cache_ttl_seconds
        self._allowlist = build_default_allowlist_policy()
        self._client = httpx.Client(
            follow_redirects=True,
            timeout=self._timeout,
            headers={
                "User-Agent": "senmcp (+https://github.com/sencivic/senmcp)",
            },
        )
        self._cache_dir = Path(".cache") / "http"
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        self._host_last_request: dict[str, float] = {}
        self._logger = get_logger(__name__)

    def _validate_url(self, url: str) -> None:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            raise ValueError(f"Unsupported URL scheme for HTTP client: {parsed.scheme}")
        if not UrlSafety.is_safe(url) or not self._allowlist.is_allowed(url):
            raise ValueError("URL is not allowed by safety or allowlist policy.")

    def _rate_limit(self, host: str) -> None:
        if self._rate_limit_per_host <= 0:
            return
        now = time.time()
        last = self._host_last_request.get(host)
        min_interval = 1.0 / self._rate_limit_per_host
        if last is not None:
            elapsed = now - last
            if elapsed < min_interval:
                time.sleep(min_interval - elapsed)
        self._host_last_request[host] = time.time()

    def _cache_key(self, method: str, url: str) -> Path:
        raw = f"{method.upper()} {url}".encode()
        digest = hashlib.sha256(raw).hexdigest()
        return self._cache_dir / digest

    def _load_cache(
        self,
        method: str,
        url: str,
    ) -> tuple[HttpResponse | None, dict[str, Any] | None]:
        path = self._cache_key(method, url)
        meta_path = path.with_suffix(".json")
        body_path = path.with_suffix(".bin")
        if not meta_path.exists() or not body_path.exists():
            return None, None
        try:
            meta = orjson.loads(meta_path.read_bytes())
            fetched_at = float(meta.get("fetched_at", 0.0))
            if time.time() - fetched_at > self._cache_ttl:
                return None, meta
            body = body_path.read_bytes()
            return (
                HttpResponse(
                    status_code=int(meta["status_code"]),
                    headers={str(k): str(v) for k, v in meta.get("headers", {}).items()},
                    content=body,
                ),
                meta,
            )
        except Exception:
            return None, None

    def _store_cache(
        self,
        method: str,
        url: str,
        response: HttpResponse,
        meta: dict[str, Any] | None = None,
    ) -> None:
        path = self._cache_key(method, url)
        meta_path = path.with_suffix(".json")
        body_path = path.with_suffix(".bin")
        data: dict[str, Any] = {
            "method": method.upper(),
            "url": url,
            "status_code": response.status_code,
            "headers": response.headers,
            "fetched_at": time.time(),
        }
        if meta is not None:
            etag = meta.get("etag")
            last_modified = meta.get("last_modified")
            if etag is not None:
                data["etag"] = etag
            if last_modified is not None:
                data["last_modified"] = last_modified
        meta_path.write_bytes(orjson.dumps(data))
        body_path.write_bytes(response.content)

    def fetch(
        self,
        url: str,
        *,
        method: str = "GET",
        headers: dict[str, str] | None = None,
        use_cache: bool = True,
    ) -> HttpResponse:
        """Fetch a URL with safety, caching, and size limits.

        This is a synchronous helper intended for use inside domain adapters.
        """
        self._validate_url(url)
        parsed = urlparse(url)
        host = parsed.hostname or ""

        method_upper = method.upper()
        headers = headers.copy() if headers is not None else {}

        cached_response: HttpResponse | None = None
        cached_meta: dict[str, Any] | None = None
        if use_cache and method_upper == "GET":
            cached_response, cached_meta = self._load_cache(method_upper, url)
            if cached_response is not None:
                self._logger.info(
                    "HTTP cache hit",
                    extra={
                        "url": url,
                        "status_code": cached_response.status_code,
                        "from_cache": True,
                    },
                )
                return cached_response
            # Stale cache: use conditional headers if available.
            if cached_meta is not None:
                etag = cached_meta.get("etag")
                last_modified = cached_meta.get("last_modified")
                if etag:
                    headers["If-None-Match"] = str(etag)
                if last_modified:
                    headers["If-Modified-Since"] = str(last_modified)

        self._rate_limit(host)

        with self._client.stream(method_upper, url, headers=headers) as resp:
            content_chunks: list[bytes] = []
            total = 0
            for chunk in resp.iter_bytes():
                if not chunk:
                    continue
                content_chunks.append(chunk)
                total += len(chunk)
                if total > self._max_bytes:
                    self._logger.warning(
                        "HTTP response exceeded max bytes",
                        extra={"url": url, "limit": self._max_bytes},
                    )
                    raise httpx.HTTPError("HTTP response exceeded configured size limit.")
            content = b"".join(content_chunks)

            response = HttpResponse(
                status_code=resp.status_code,
                headers={str(k): str(v) for k, v in resp.headers.items()},
                content=content,
            )

        self._logger.info(
            "HTTP request completed",
            extra={"url": url, "status_code": response.status_code, "from_cache": False},
        )

        if use_cache and method_upper == "GET" and response.status_code == 200:
            meta: dict[str, Any] = {
                "etag": response.headers.get("ETag"),
                "last_modified": response.headers.get("Last-Modified"),
            }
            self._store_cache(method_upper, url, response, meta=meta)
        elif (
            use_cache
            and method_upper == "GET"
            and response.status_code == 304
            and cached_meta is not None
            and cached_response is not None
        ):
            # Server indicates cached content is still valid; refresh fetched_at.
            self._store_cache(method_upper, url, cached_response, meta=cached_meta)
            return cached_response

        return response


_client_instance: HttpClient | None = None


def get_http_client() -> HttpClient:
    """Return a process-wide shared HttpClient instance."""
    global _client_instance
    if _client_instance is None:
        _client_instance = HttpClient()
    return _client_instance

