"""x402-metered autonomy recommendation API (stub for local dev)."""

from __future__ import annotations

import os
from typing import Any

from fastapi import FastAPI, Query

app = FastAPI(title="Aurey Autonomy Signals", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/v1/recommendation")
def recommendation(
    chain: str = Query(...),
    symbol: str = Query(...),
    notional_usd: str = Query(...),
) -> dict[str, Any]:
    """Return structured trade hint. Production: gate with x402 USDC payment."""
    return {
        "chain": chain.strip().lower(),
        "symbol": symbol.strip().upper(),
        "notional_usd": notional_usd,
        "action": "hold",
        "confidence": 0.42,
        "rationale": "Stub signal — replace with paid x402 data layer.",
        "x402": {
            "required": os.environ.get("AUREY_X402_ENFORCE", "false").lower() == "true",
            "price_usdc": os.environ.get("AUREY_X402_PRICE_USDC", "0.01"),
        },
    }


def main() -> None:
    import uvicorn

    port = int(os.environ.get("PORT", "8092"))
    uvicorn.run("aurey_autonomy_api.app:app", host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
