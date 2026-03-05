from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, HttpUrl


class Citation(BaseModel):
    """Represents a citation for a data source or official document."""

    id: str
    title: str
    url: HttpUrl
    accessed_at: datetime
    snippet: str | None = None
    source_id: str | None = None
    file_hash: str | None = None
