"""Hosted Li.Fi route-builder (integrator fee protected)."""

from __future__ import annotations

import os
from typing import Any
from urllib.parse import urlencode

import httpx
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(title="Aurey Route Builder", version="0.1.0")

_LIFI_BASE = os.environ.get("AUREY_ROUTE_BUILDER_LIFI_BASE", "https://li.quest").rstrip("/")
_INTEGRATOR = os.environ.get("AUREY_ROUTE_BUILDER_INTEGRATOR", "aurey-agentic-pantheon")
_FEE_BPS = int(os.environ.get("AUREY_ROUTE_BUILDER_FEE_BPS", "25"))
_API_KEY = (os.environ.get("AUREY_ROUTE_BUILDER_LIFI_API_KEY") or "").strip()
_AUTH = (os.environ.get("AUREY_ROUTE_BUILDER_AUTH_TOKEN") or "").strip()
_UA = "Aurey-Route-Builder/0.1 (+https://agentic-pantheon.com)"


class QuoteRequest(BaseModel):
    query: dict[str, str] = Field(description="LiFi /v1/quote query parameters")


def _require_auth(authorization: str | None) -> None:
    if not _AUTH:
        return
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Unauthorized")
    if authorization.removeprefix("Bearer ").strip() != _AUTH:
        raise HTTPException(status_code=401, detail="Unauthorized")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/v1/quote")
def quote(body: QuoteRequest, authorization: str | None = Header(default=None)) -> dict[str, Any]:
    _require_auth(authorization)
    q = dict(body.query)
    if _INTEGRATOR:
        q.setdefault("integrator", _INTEGRATOR)
    if _FEE_BPS > 0:
        q.setdefault("fee", str(_FEE_BPS / 10_000))
    url = f"{_LIFI_BASE}/v1/quote?{urlencode(q)}"
    headers = {"User-Agent": _UA}
    if _API_KEY:
        headers["x-lifi-api-key"] = _API_KEY
    with httpx.Client(timeout=60.0) as client:
        resp = client.get(url, headers=headers)
        resp.raise_for_status()
        quote_json = resp.json()
    fee_disclosure = {
        "integrator": q.get("integrator"),
        "fee_bps": _FEE_BPS,
        "note": (
            "Route quote includes Aurey integrator fee; "
            "signing remains on user device via 1claw."
        ),
    }
    return {"quote": quote_json, "fee_disclosure": fee_disclosure}


def main() -> None:
    import uvicorn

    port = int(os.environ.get("PORT", "8091"))
    uvicorn.run("aurey_route_builder.app:app", host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
