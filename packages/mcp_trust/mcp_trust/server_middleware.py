from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

from mcp_core.errors import TrustPolicyError
from mcp_core.logging import get_logger

from mcp_trust.audit import JsonlAuditLogger
from mcp_trust.context import TrustContext
from mcp_trust.policies import (
    NETWORKED_TOOLS,
    PromptInjectionHeuristics,
    UrlSafety,
    build_default_allowlist_policy,
)
from mcp_trust.provenance import ProvenanceManager

T = TypeVar("T")


async def with_trust_safety(
    tool_name: str,
    params: dict[str, Any],
    handler: Callable[[dict[str, Any], TrustContext], Awaitable[T]],
    audit_logger: JsonlAuditLogger,
    provenance_manager: ProvenanceManager,
) -> T:
    """Run a tool handler with basic trust & safety checks and audit logging."""

    request_prov = provenance_manager.new_request()
    tool_prov = provenance_manager.new_tool_call(request_prov.request_id, tool_name, params)
    ctx = TrustContext(
        request_id=request_prov.request_id,
        tool_call_id=tool_prov.tool_call_id,
        tool_name=tool_name,
    )

    logger = get_logger(__name__, request_id=ctx.request_id, tool_call_id=ctx.tool_call_id)

    injection = PromptInjectionHeuristics().evaluate(json_dump_safe(params))
    if injection.is_suspicious:
        audit_logger.log(
            {
                "request_id": ctx.request_id,
                "tool_call_id": ctx.tool_call_id,
                "tool_name": tool_name,
                "decision": "blocked_prompt_injection",
                "score": injection.score,
                "reasons": injection.reasons,
            }
        )
        logger.warning("Blocked tool call due to prompt injection heuristics.")
        raise TrustPolicyError("Tool call blocked by prompt injection heuristics.")

    if tool_name in NETWORKED_TOOLS:
        allowlist = build_default_allowlist_policy()
        for value in params.values():
            if isinstance(value, str) and value.startswith(("http://", "https://")):
                if not UrlSafety.is_safe(value) or not allowlist.is_allowed(value):
                    audit_logger.log(
                        {
                            "request_id": ctx.request_id,
                            "tool_call_id": ctx.tool_call_id,
                            "tool_name": tool_name,
                            "decision": "blocked_url",
                            "url": value,
                        }
                    )
                    logger.warning("Blocked tool call due to URL safety/allowlist policy.")
                    raise TrustPolicyError("URL is not allowed by safety or allowlist policy.")

    audit_logger.log(
        {
            "request_id": ctx.request_id,
            "tool_call_id": ctx.tool_call_id,
            "tool_name": tool_name,
            "decision": "allowed",
            "input_keys": sorted(params.keys()),
        }
    )

    result = await handler(params, ctx)

    audit_logger.log(
        {
            "request_id": ctx.request_id,
            "tool_call_id": ctx.tool_call_id,
            "tool_name": tool_name,
            "decision": "completed",
        }
    )

    return result


def json_dump_safe(value: Any) -> str:
    """Serialize a value to JSON for heuristics without raising."""

    try:
        import json

        return json.dumps(value, default=str)
    except Exception:
        return str(value)
