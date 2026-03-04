from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any
from uuid import uuid4

from mcp_core.logging import get_logger

from mcp_trust.audit import JsonlAuditLogger
from mcp_trust.policies import PromptInjectionHeuristics
from mcp_trust.utils import json_dump_safe


async def trust_safety_interceptor(request: Any, handler: Callable[[Any], Awaitable[Any]]) -> Any:
    """Interceptor for MultiServerMCPClient tool calls.

    This function assumes `request` is an object with at least:
    - `tool_name`
    - `params` (dict-like)
    - optional `transport` / `headers` attributes for HTTP.
    """

    request_id = str(uuid4())
    tool_name = getattr(request, "tool_name", "unknown_tool")
    params: dict[str, Any] = getattr(request, "params", {}) or {}

    logger = get_logger(__name__, request_id=request_id)
    audit_logger = JsonlAuditLogger("./logs/audit-agent.jsonl")

    # Inject X-Request-ID header for HTTP transports when possible.
    transport = getattr(request, "transport", None)
    if transport == "http":
        headers = getattr(request, "headers", None) or {}
        headers["X-Request-ID"] = request_id
        request.headers = headers

    text_for_heuristics = json_dump_safe(params)
    injection = PromptInjectionHeuristics().evaluate(text_for_heuristics)
    if injection.is_suspicious:
        audit_logger.log(
            {
                "request_id": request_id,
                "tool_name": tool_name,
                "decision": "blocked_prompt_injection",
                "score": injection.score,
                "reasons": injection.reasons,
            }
        )
        logger.warning(
            "Client-side interceptor blocked tool call due to prompt injection heuristics."
        )
        raise RuntimeError("Tool call blocked by client-side trust & safety interceptor.")

    audit_logger.log(
        {
            "request_id": request_id,
            "tool_name": tool_name,
            "decision": "allowed",
            "input_keys": sorted(params.keys()),
        }
    )

    result = await handler(request)

    audit_logger.log(
        {
            "request_id": request_id,
            "tool_name": tool_name,
            "decision": "completed",
        }
    )

    return result
