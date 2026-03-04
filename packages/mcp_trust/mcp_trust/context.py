from __future__ import annotations

from dataclasses import dataclass


@dataclass
class TrustContext:
    """Context passed through trust & safety middleware."""

    request_id: str
    tool_call_id: str
    tool_name: str
