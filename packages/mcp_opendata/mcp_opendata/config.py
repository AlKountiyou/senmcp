from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class OpenDataSettings(BaseSettings):
    """Configuration specific to the open data MCP server."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    assets_dir: Path = Field(default=Path(__file__).parent / "assets", alias="OPENDATA_ASSETS_DIR")


@lru_cache(maxsize=1)
def get_settings() -> OpenDataSettings:
    return OpenDataSettings()
