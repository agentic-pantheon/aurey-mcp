"""Adapt LangChain wallet tools to MCP tool handlers."""

from __future__ import annotations

import json
from typing import Any

from langchain_core.tools import BaseTool

from aurey.runtime import AureyRuntime
from aurey.tools.agent_tools import build_aurey_subgraph_tools
from aurey_wallet_mcp.autonomy.tools import build_autonomy_tools
from aurey_wallet_mcp.local_portfolio_tools import build_local_portfolio_tools


def _json_schema_from_tool(tool: BaseTool) -> dict[str, Any]:
    schema = getattr(tool, "args_schema", None)
    if schema is not None and hasattr(schema, "model_json_schema"):
        return schema.model_json_schema()
    return {"type": "object", "properties": {}}


def build_mcp_tool_registry(runtime: AureyRuntime) -> dict[str, tuple[BaseTool, dict[str, Any]]]:
    """Return ``tool_name -> (langchain_tool, input_json_schema)``."""

    registry: dict[str, tuple[BaseTool, dict[str, Any]]] = {}
    for tool in build_aurey_subgraph_tools(runtime):
        name = tool.name
        if not name:
            continue
        registry[name] = (tool, _json_schema_from_tool(tool))
    for tool in build_autonomy_tools(runtime):
        name = tool.name
        if not name or name in registry:
            continue
        registry[name] = (tool, _json_schema_from_tool(tool))
    for tool in build_local_portfolio_tools(runtime):
        name = tool.name
        if not name or name in registry:
            continue
        registry[name] = (tool, _json_schema_from_tool(tool))
    return registry


def invoke_registry_tool(
    registry: dict[str, tuple[BaseTool, dict[str, Any]]],
    name: str,
    arguments: dict[str, Any],
) -> str:
    entry = registry.get(name)
    if entry is None:
        return json.dumps({"ok": False, "error": {"code": "unknown_tool", "message": name}})
    tool, _ = entry
    try:
        out = tool.invoke(arguments)
    except Exception as exc:
        return json.dumps(
            {
                "ok": False,
                "error": {"code": "tool_error", "message": str(exc)[:800]},
            }
        )
    return json.dumps(out, default=str)


__all__ = ["build_mcp_tool_registry", "invoke_registry_tool"]
