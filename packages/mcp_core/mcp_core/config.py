from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class CoreSettings(BaseSettings):
    """Shared configuration for the SenCivic MCP Stack."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    run_mode: str = Field("local", alias="RUN_MODE")

    allowlist_domains: list[str] = Field(
        default_factory=list,
        alias="ALLOWLIST_DOMAINS",
        description="Comma-separated list of allowed domains for network access.",
    )

    mcp_http_host: str = Field("0.0.0.0", alias="MCP_HTTP_HOST")
    mcp_http_port: int = Field(8000, alias="MCP_HTTP_PORT")
    mcp_http_path: str = Field("/mcp", alias="MCP_HTTP_PATH")

    audit_opendata_path: str = Field("./logs/audit-opendata.jsonl", alias="AUDIT_OPENDATA_PATH")
    audit_services_path: str = Field("./logs/audit-services.jsonl", alias="AUDIT_SERVICES_PATH")
    audit_agent_path: str = Field("./logs/audit-agent.jsonl", alias="AUDIT_AGENT_PATH")

    http_rate_limit_per_host: float = Field(
        1.0,
        alias="HTTP_RATE_LIMIT_PER_HOST",
        description="Maximum number of outbound HTTP requests per second for a single host.",
    )
    http_cache_ttl_seconds: int = Field(
        86_400,
        alias="HTTP_CACHE_TTL_SECONDS",
        description="TTL in seconds for HTTP disk cache entries.",
    )
    http_timeout_seconds: float = Field(
        10.0,
        alias="HTTP_TIMEOUT_SECONDS",
        description="Per-request timeout in seconds for outbound HTTP calls.",
    )
    http_max_bytes: int = Field(
        10_000_000,
        alias="HTTP_MAX_BYTES",
        description="Maximum number of bytes to read from any single HTTP response body.",
    )


@lru_cache(maxsize=1)
def get_settings() -> CoreSettings:
    """Return a singleton CoreSettings instance."""

    settings = CoreSettings()  # type: ignore[call-arg]

    return settings
