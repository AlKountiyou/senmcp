from __future__ import annotations

import asyncio
import json

import typer

from agent_app.graph.graph_builder import build_agent_graph
from agent_app.graph.state import AgentState
from agent_app.mcp_client import create_mcp_client, load_tools

app = typer.Typer(help="SenCivic MCP Stack CLI.")


@app.command("tools-list")
def tools_list() -> None:
    """List available MCP tools across configured servers."""

    async def _run() -> None:
        client = await create_mcp_client()
        tools = await load_tools(client)
        for tool in tools:
            typer.echo(f"{tool.name} - {tool.description}")

    asyncio.run(_run())


DEFAULT_PARAMS: list[str] = []


@app.command("call")
def call(
    server: str = typer.Argument(..., help="Logical server name (e.g. opendata or services)."),
    tool_name: str = typer.Argument(..., help="Tool name to invoke."),
    param: list[str] | None = typer.Option(
        None,
        "--param",
        "-p",
        help="Repeat: --param key=value",
    ),
) -> None:
    """Call a single MCP tool with key=value parameters."""

    async def _run() -> None:
        client = await create_mcp_client(selected_servers=[server])
        tools = await load_tools(client)
        target = next((t for t in tools if t.name == tool_name), None)
        if target is None:
            raise typer.Exit(code=1)

        parsed_params: dict[str, object] = {}
        if param:
            for item in param:
                if "=" not in item:
                    raise typer.BadParameter(f"Invalid --param {item!r}. Use key=value.")
                key, value = item.split("=", 1)
                try:
                    parsed_params[key] = json.loads(value)
                except json.JSONDecodeError:
                    parsed_params[key] = value

        # MCP tools are usually async.
        if hasattr(target, "ainvoke"):
            result = await target.ainvoke(parsed_params)
        else:
            result = target.invoke(parsed_params)  # type: ignore[assignment]

        if hasattr(result, "model_dump_json"):
            typer.echo(result.model_dump_json(indent=2))
        else:
            try:
                typer.echo(json.dumps(result, indent=2, ensure_ascii=False, default=str))
            except TypeError:
                typer.echo(str(result))

    asyncio.run(_run())


@app.command("chat")
def chat(
    servers: str = typer.Option(
        "opendata,services",
        "--servers",
        help="Comma-separated list of logical MCP servers to use.",
    ),
) -> None:
    """Start a simple REPL using the LangGraph-based MCP agent."""

    async def _chat_loop(selected: list[str]) -> None:
        client = await create_mcp_client(selected_servers=selected)
        tools = await load_tools(client)
        graph = build_agent_graph(tools)

        typer.echo("SenCivic MCP chat. Type 'exit' to quit.")
        while True:
            user_input = input("> ").strip()
            if user_input.lower() in {"exit", "quit"}:
                break

            initial_state: AgentState = {
                "user_input": user_input,
                "planned_calls": [],
                "tool_results": [],
            }
            result = await graph.ainvoke(initial_state)
            typer.echo(result.get("answer", ""))

    selected_servers = [s.strip() for s in servers.split(",") if s.strip()]
    asyncio.run(_chat_loop(selected_servers))


if __name__ == "__main__":
    app()
