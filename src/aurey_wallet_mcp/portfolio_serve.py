"""Run the local portfolio UI HTTP server (without MCP stdio)."""

from __future__ import annotations

import logging
import sys

from aurey.service.bootstrap import AureyRuntimeBootstrapError, bootstrap_aurey_runtime
from aurey_wallet_mcp.config import load_settings
from aurey_wallet_mcp.dashboard import create_dashboard_app
from aurey_wallet_mcp.portfolio_static import portfolio_ui_display_host

_log = logging.getLogger(__name__)


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    settings = load_settings()
    if not settings.dashboard_enabled:
        _log.error(
            "Set [dashboard] enabled = true in ~/.aurey/config.toml "
            "(or AUREY_DASHBOARD_ENABLED=true)."
        )
        raise SystemExit(1)
    try:
        runtime = bootstrap_aurey_runtime(settings)
    except AureyRuntimeBootstrapError as exc:
        _log.error("Bootstrap failed: %s", exc)
        raise SystemExit(1) from exc

    app = create_dashboard_app(runtime, settings)
    host = settings.dashboard_host
    port = int(settings.dashboard_port)
    display = portfolio_ui_display_host(host)
    _log.info("Portfolio UI: http://%s:%s/ (Ctrl+C to stop)", display, port)
    import uvicorn

    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
