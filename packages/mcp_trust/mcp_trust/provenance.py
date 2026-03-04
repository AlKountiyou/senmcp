from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from mcp_core.models.provenance import RequestProvenance, ToolCallProvenance


class ProvenanceManager:
    """Creates request and tool-call provenance records."""

    def new_request(self) -> RequestProvenance:
        return RequestProvenance(request_id=str(uuid4()), created_at=datetime.now(UTC))

    def new_tool_call(
        self, request_id: str, tool_name: str, raw_input: dict[str, Any]
    ) -> ToolCallProvenance:
        tool_call_id = str(uuid4())
        normalized = json.dumps(raw_input, sort_keys=True, separators=(",", ":"), default=str)
        source_hash = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
        return ToolCallProvenance(
            request_id=request_id,
            tool_call_id=tool_call_id,
            tool_name=tool_name,
            accessed_at=datetime.now(UTC),
            source_hash=source_hash,
            metadata={},
        )
