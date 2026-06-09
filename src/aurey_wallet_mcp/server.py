"""MCP stdio server exposing Aurey wallet tools."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from aurey.service.bootstrap import AureyRuntimeBootstrapError, bootstrap_aurey_runtime
from aurey_wallet_mcp.config import load_settings
from aurey_wallet_mcp.dashboard import maybe_start_dashboard_thread
from aurey_wallet_mcp.tools import build_mcp_tool_registry, invoke_registry_tool

_log = logging.getLogger(__name__)
server = Server("aurey-wallet")

_RUNTIME: Any | None = None
_REGISTRY: dict[str, Any] | None = None


def _ensure_state() -> tuple[Any, dict[str, Any]]:
    global _RUNTIME, _REGISTRY
    if _REGISTRY is None:
        settings = load_settings()
        _RUNTIME = bootstrap_aurey_runtime(settings)
        _REGISTRY = build_mcp_tool_registry(_RUNTIME)
        maybe_start_dashboard_thread(_RUNTIME, settings)
    assert _REGISTRY is not None and _RUNTIME is not None
    return _RUNTIME, _REGISTRY


@server.list_tools()
async def list_tools() -> list[Tool]:
    _, registry = _ensure_state()
    tools: list[Tool] = []
    for name, (_, schema) in sorted(registry.items()):
        tools.append(
            Tool(
                name=name,
                description=f"Aurey wallet tool `{name}` (prepare/confirm/execute safety enforced server-side).",
                inputSchema=schema,
            )
        )
    return tools


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any] | None) -> list[TextContent]:
    _, registry = _ensure_state()
    payload = invoke_registry_tool(registry, name, dict(arguments or {}))
    return [TextContent(type="text", text=payload)]


async def _async_main() -> None:
    logging.basicConfig(level=logging.INFO)
    try:
        _ensure_state()
    except AureyRuntimeBootstrapError as exc:
        _log.error("Bootstrap failed: %s", exc)
        raise SystemExit(1) from exc
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


def main() -> None:
    asyncio.run(_async_main())


if __name__ == "__main__":
    main()
