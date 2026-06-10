"""Optional localhost dashboard (portfolio + prepared tx review)."""

from __future__ import annotations

import logging
import threading
from typing import Any

from aurey.runtime import AureyRuntime
from aurey.settings import AureySettings
from aurey_wallet_mcp.portfolio_static import (
    portfolio_ui_display_host,
    read_portfolio_ui_bundle_id,
    resolve_portfolio_static_dir,
)

_log = logging.getLogger(__name__)
_STARTED = False


def _auth_ok(settings: AureySettings, authorization: str | None) -> bool:
    expected = (settings.dashboard_auth_token or "").strip()
    if not expected:
        return True
    if not authorization or not authorization.startswith("Bearer "):
        return False
    return authorization.removeprefix("Bearer ").strip() == expected


def create_dashboard_app(runtime: AureyRuntime, settings: AureySettings) -> Any:
    from fastapi import Depends, FastAPI, Header, HTTPException
    from fastapi.responses import HTMLResponse
    from fastapi.staticfiles import StaticFiles

    from aurey.miniapp.portfolio import aggregate_portfolio_snapshot
    from aurey.miniapp.schemas import PortfolioSnapshot
    from aurey.miniapp.wallet import resolve_wallet_for_dashboard

    app = FastAPI(title="Aurey Local Dashboard", version="0.1.0")

    def require_auth(authorization: str | None = Header(default=None)) -> None:
        if not _auth_ok(settings, authorization):
            raise HTTPException(status_code=401, detail="Unauthorized")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/v1/dashboard/ui-info")
    def ui_info() -> dict[str, Any]:
        static_dir = resolve_portfolio_static_dir()
        return {
            "ui_mode": "local_agent",
            "static_dir": str(static_dir) if static_dir is not None else None,
            "js_bundle": read_portfolio_ui_bundle_id(static_dir),
            "telegram_only_ui": False,
        }

    @app.get("/v1/dashboard/status", dependencies=[Depends(require_auth)])
    def status() -> dict[str, Any]:
        wallet = resolve_wallet_for_dashboard(runtime)
        prepared = []
        store = runtime.prepared_txs
        with store._lock:  # noqa: SLF001 — local debug surface
            for pid, rec in list(store._records.items())[:32]:
                prepared.append(
                    {
                        "prepared_id": pid,
                        "kind": rec.kind,
                        "summary": rec.summary,
                    }
                )
        return {
            "wallet_address": wallet.wallet_address,
            "evm_signing_mode": settings.evm_signing_mode,
            "route_builder_configured": bool((settings.route_builder_url or "").strip()),
            "prepared_transactions": prepared,
        }

    @app.post("/v1/dashboard/portfolio", dependencies=[Depends(require_auth)])
    def portfolio(body: dict[str, Any] | None = None) -> dict[str, Any]:
        wallet = resolve_wallet_for_dashboard(runtime)
        if not wallet.wallet_address:
            raise HTTPException(
                status_code=400,
                detail="No EVM address on 1Claw agent — finish signing-key setup or set override.",
            )
        chains = tuple((body or {}).get("chains") or ("ethereum", "base", "arbitrum"))
        period = str((body or {}).get("chart_period") or "month")
        snapshot: PortfolioSnapshot = aggregate_portfolio_snapshot(
            runtime,
            wallet_address=wallet.wallet_address,
            chains=chains,
            chart_period=period,
        )
        return snapshot.model_dump()

    dist = resolve_portfolio_static_dir()
    if dist is not None:
        app.mount("/", StaticFiles(directory=str(dist), html=True), name="portfolio_ui")
    else:
        _log.warning(
            "Portfolio UI static files missing — run scripts/build_portfolio_static.py "
            "or cd miniapp && npm run build"
        )

        @app.get("/")
        def root_missing() -> HTMLResponse:
            return HTMLResponse(
                "<p>Portfolio UI not built. From repo root: "
                "<code>uv run python scripts/build_portfolio_static.py</code></p>",
                status_code=503,
            )

    return app


def maybe_start_dashboard_thread(runtime: AureyRuntime, settings: AureySettings) -> None:
    global _STARTED
    if _STARTED or not settings.dashboard_enabled:
        return

    try:
        app = create_dashboard_app(runtime, settings)
    except ImportError as exc:
        _log.warning(
            "Portfolio UI not started (missing dependency: %s). "
            "From repo: uv tool install --force . · or pip install 'aurey-wallet-mcp'",
            exc,
        )
        return

    host = settings.dashboard_host
    port = int(settings.dashboard_port)
    static_dir = resolve_portfolio_static_dir()

    def _run() -> None:
        try:
            import uvicorn
        except ImportError as exc:
            _log.warning("Portfolio UI not started (uvicorn missing: %s)", exc)
            return

        try:
            uvicorn.run(app, host=host, port=port, log_level="info")
        except OSError as exc:
            if exc.errno in {98, 10048}:  # EADDRINUSE on Linux / Windows
                _log.warning(
                    "Portfolio UI port %s busy — another aurey-wallet-mcp likely serves it",
                    port,
                )
            else:
                _log.warning("Portfolio UI failed to start: %s", exc)

    thread = threading.Thread(target=_run, name="aurey-dashboard", daemon=True)
    thread.start()
    _STARTED = True
    display = portfolio_ui_display_host(host)
    url = f"http://{display}:{port}/"
    if static_dir is None:
        _log.info("Portfolio API at %s (static UI missing)", url)
    else:
        _log.info("Portfolio UI: %s", url)
        if host.strip() in ("0.0.0.0", "::", "[::]"):
            _log.info(
                "Portfolio UI listening on all interfaces — use LAN IP or tunnel; "
                "set dashboard.auth_token when exposing beyond loopback"
            )


__all__ = ["create_dashboard_app", "maybe_start_dashboard_thread"]
