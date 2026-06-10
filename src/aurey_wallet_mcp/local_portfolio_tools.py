"""MCP tools for the local agent portfolio UI."""

from __future__ import annotations

from typing import Any

from langchain_core.tools import StructuredTool
from pydantic import BaseModel

from aurey.custody.agent_wallet import effective_evm_wallet_address
from aurey.runtime import AureyRuntime
from aurey_wallet_mcp.portfolio_static import (
    portfolio_ui_display_host,
    resolve_portfolio_static_dir,
)


class _EmptyArgs(BaseModel):
    pass


def _zerion_configured(settings: Any) -> bool:
    if (settings.zerion_api_key or "").strip():
        return True
    path = settings.zerion_api_secret_path
    return path is not None and str(path).strip()


def build_local_portfolio_tools(runtime: AureyRuntime) -> list[StructuredTool]:
    settings = runtime.settings

    def get_local_portfolio_url() -> dict[str, Any]:
        enabled = bool(settings.dashboard_enabled)
        bind_host = (settings.dashboard_host or "127.0.0.1").strip()
        display_host = portfolio_ui_display_host(bind_host)
        port = int(settings.dashboard_port)
        auth_required = bool((settings.dashboard_auth_token or "").strip())
        wallet = (effective_evm_wallet_address(runtime) or "").strip() or None
        static_available = resolve_portfolio_static_dir() is not None
        url = f"http://{display_host}:{port}/" if enabled else None
        return {
            "url": url,
            "bind_host": bind_host,
            "enabled": enabled,
            "static_available": static_available,
            "wallet_address": wallet,
            "zerion_configured": _zerion_configured(settings),
            "auth_required": auth_required,
        }

    tool = StructuredTool.from_function(
        func=get_local_portfolio_url,
        name="get_local_portfolio_url",
        description=(
            "Return the localhost portfolio UI URL and readiness (dashboard enabled, Zerion "
            "config, static assets). Open url in a browser while MCP is running."
        ),
        args_schema=_EmptyArgs,
    )
    return [tool]


__all__ = ["build_local_portfolio_tools"]
