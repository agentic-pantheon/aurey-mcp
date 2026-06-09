"""Token registry row model (standalone; no Postgres ORM)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TokenRow:
    chain_slug: str
    chain_id: int | None
    symbol: str
    name: str
    address: str
    decimals: int | None
    coingecko_id: str | None
    source: str
    trust_tier: str
    verified_onchain: bool
    cg_recognized: bool
    lifi_supported: bool = False
    ecosystem: str = "evm"


__all__ = ["TokenRow"]
