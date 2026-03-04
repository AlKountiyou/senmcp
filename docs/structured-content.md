## Structured Content Contract for MCP Tools

This document defines the structured content (`structuredContent` / `ToolMessage.artifact`) contract used by SenCivic MCP tools. All MCP tools should return a short human-readable `text` summary plus a structured payload in `structuredContent` that downstream agents can consume reliably.

At a high level:

- Open data tools return artifacts shaped like:
  - `{"table": {...}, "citations": [...], "metadata": {...}}`
- Service catalog tools return artifacts shaped like:
  - `{"service": {...}, "eligibility": {...}, "citations": [...]}`

The LangGraph synthesizer node in `agent_app` is responsible for reading these artifacts, extracting tables and citations, and formatting them into the final answer.

