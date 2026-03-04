## ADR-0001: Overall Architecture for SenCivic MCP Stack

Status: Accepted  
Date: 2026-03-04

This ADR documents the high-level architecture for the SenCivic MCP Stack, including a shared core (`mcp_core`), trust & safety layer (`mcp_trust`), two MCP servers (`mcp_opendata`, `mcp_services`), and an agent application (`agent_app`) built on LangChain and LangGraph that consumes MCP tools via `MultiServerMCPClient`.

