from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ServicesSettings(BaseSettings):
    """Configuration specific to the services MCP server."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    catalog_dir: Path = Field(
        default=Path(__file__).parents[3] / "data" / "services_catalog",
        alias="SERVICES_CATALOG_DIR",
    )


@lru_cache(maxsize=1)
def get_settings() -> ServicesSettings:
    return ServicesSettings()
