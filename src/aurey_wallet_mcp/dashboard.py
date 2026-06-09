"""Optional localhost dashboard (portfolio + prepared tx review)."""

from __future__ import annotations

import logging
import threading
from pathlib import Path
from typing import Any

from aurey.runtime import AureyRuntime
from aurey.settings import AureySettings

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
    from fastapi.responses import FileResponse
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
    def portfolio(body: dict[str, Any] | None = None) -> PortfolioSnapshot:
        wallet = resolve_wallet_for_dashboard(runtime)
        if not wallet.wallet_address:
            raise HTTPException(
                status_code=400,
                detail="No EVM address on 1Claw agent — finish signing-key setup or set override.",
            )
        chains = tuple((body or {}).get("chains") or ("ethereum", "base", "arbitrum"))
        period = str((body or {}).get("chart_period") or "month")
        return aggregate_portfolio_snapshot(
            runtime,
            wallet_address=wallet.wallet_address,
            chains=chains,
            chart_period=period,
        )

    dist = Path(__file__).resolve().parents[2] / "miniapp" / "dist"
    if dist.is_dir():
        app.mount("/miniapp", StaticFiles(directory=str(dist), html=True), name="miniapp")

        @app.get("/")
        def root() -> FileResponse:
            index = dist / "index.html"
            return FileResponse(index)
    return app


def maybe_start_dashboard_thread(runtime: AureyRuntime, settings: AureySettings) -> None:
    global _STARTED
    if _STARTED or not settings.dashboard_enabled:
        return
    try:
        import uvicorn
    except ImportError:
        _log.warning("Dashboard enabled but uvicorn not installed (pip install aurey-wallet-mcp[dashboard])")
        return

    app = create_dashboard_app(runtime, settings)
    host = settings.dashboard_host
    port = int(settings.dashboard_port)

    def _run() -> None:
        uvicorn.run(app, host=host, port=port, log_level="info")

    thread = threading.Thread(target=_run, name="aurey-dashboard", daemon=True)
    thread.start()
    _STARTED = True
    _log.info("Aurey dashboard listening on http://%s:%s/", host, port)


__all__ = ["create_dashboard_app", "maybe_start_dashboard_thread"]
