from __future__ import annotations

from collections.abc import Callable
from typing import Any, cast

from agent_app.graph.state import AgentState, ToolResult


def synthesizer_node() -> Callable[[AgentState], AgentState]:
    """Create a synthesizer node that formats tool results and extracts citations/tables."""

    def _synthesizer(state: AgentState) -> AgentState:
        user_input = state.get("user_input", "")
        results: list[ToolResult] = state.get("tool_results", [])

        if not results:
            answer = (
                "Je n'ai pas pu trouver d'outil MCP pertinent pour cette demande pour le moment. "
                "Essayez de préciser si vous cherchez un dataset (opendata) "
                "ou un service administratif."
            )
        else:
            parts: list[str] = [f"Demande: {user_input}", ""]
            for res in results:
                text, details = _extract_text_and_structured(res["raw"])
                parts.append(f"- Résultat de `{res['tool_name']}`: {text}")
                if details:
                    parts.append(details)
            answer = "\n".join(parts)

        new_state = dict(state)
        new_state["answer"] = answer
        return cast(AgentState, new_state)

    return _synthesizer


def _extract_text_and_structured(raw: Any) -> tuple[str, str]:
    """Handle ToolMessage-like objects and dicts with structuredContent."""

    # If this is a LangChain ToolMessage, it may expose .content and .artifact.
    text = ""
    structured_summary = ""

    artifact: Any = None
    if hasattr(raw, "artifact"):
        artifact = raw.artifact
        content = getattr(raw, "content", "")
        text = str(content)
    elif isinstance(raw, dict):
        text = str(raw.get("text", ""))
        artifact = raw.get("structuredContent")

    if artifact:
        # Very small, generic summarisation of structured content.
        if isinstance(artifact, dict):
            if "table" in artifact:
                structured_summary = "Tableau disponible (colonnes: {}).".format(
                    ", ".join(col.get("name", "?") for col in artifact["table"].get("columns", []))
                )
            elif "services" in artifact:
                structured_summary = "Services trouvés: {}.".format(
                    ", ".join(s.get("title", s.get("id", "?")) for s in artifact["services"][:5])
                )
            elif "service" in artifact:
                structured_summary = "Détails du service: {}.".format(
                    artifact["service"].get("title", artifact["service"].get("id", "?"))
                )
            elif "eligibility" in artifact:
                eligible = artifact["eligibility"].get("eligible")
                structured_summary = f"Éligible: {eligible}."

    return text or "(pas de texte renvoyé par l'outil)", structured_summary
