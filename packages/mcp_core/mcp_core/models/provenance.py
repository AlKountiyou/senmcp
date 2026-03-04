from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class RequestProvenance(BaseModel):
    """Provenance information for a single user request."""

    request_id: str
    created_at: datetime


class ToolCallProvenance(BaseModel):
    """Provenance information for an individual MCP tool call."""

    request_id: str
    tool_call_id: str
    tool_name: str
    accessed_at: datetime
    source_hash: str
    metadata: dict[str, Any] = {}
