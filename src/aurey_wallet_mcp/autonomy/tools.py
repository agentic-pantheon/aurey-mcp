"""Local autonomy policy and MCP tools (dry-run first)."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from aurey.runtime import AureyRuntime


@dataclass
class AutonomyPolicy:
    armed: bool = False
    allowed_chains: list[str] = field(default_factory=lambda: ["ethereum", "base"])
    allowed_symbols: list[str] = field(default_factory=lambda: ["USDC", "ETH", "WETH"])
    max_trade_usd: float = 250.0
    daily_cap_usd: float = 500.0
    slippage_max: float = 0.01
    stablecoin_reserve_usd: float = 50.0
    commission_bps: int = 25


@dataclass
class AutonomyState:
    policy: AutonomyPolicy = field(default_factory=AutonomyPolicy)
    decision_log: list[dict[str, Any]] = field(default_factory=list)
    spent_usd_today: float = 0.0
    day: str = field(default_factory=lambda: datetime.now(UTC).strftime("%Y-%m-%d"))


_STATE = AutonomyState()


def _policy_path(runtime: AureyRuntime) -> Path | None:
    raw = (runtime.settings.autonomy_policy_path or "").strip()
    if raw:
        return Path(raw).expanduser()
    return Path.home() / ".aurey" / "autonomy_policy.json"


def load_policy(runtime: AureyRuntime) -> AutonomyPolicy:
    path = _policy_path(runtime)
    if not path.is_file():
        return _STATE.policy
    data = json.loads(path.read_text(encoding="utf-8"))
    _STATE.policy = AutonomyPolicy(**{**AutonomyPolicy().__dict__, **data})
    return _STATE.policy


def save_policy(runtime: AureyRuntime, policy: AutonomyPolicy) -> None:
    path = _policy_path(runtime)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(policy.__dict__, indent=2), encoding="utf-8")
    _STATE.policy = policy


def append_decision(entry: dict[str, Any]) -> None:
    today = datetime.now(UTC).strftime("%Y-%m-%d")
    if _STATE.day != today:
        _STATE.day = today
        _STATE.spent_usd_today = 0.0
    _STATE.decision_log.append(entry)
    if len(_STATE.decision_log) > 500:
        _STATE.decision_log = _STATE.decision_log[-500:]


class ConfigurePolicyArgs(BaseModel):
    armed: bool | None = None
    max_trade_usd: float | None = Field(default=None, gt=0)
    daily_cap_usd: float | None = Field(default=None, gt=0)
    slippage_max: float | None = Field(default=None, ge=0, le=1)
    allowed_chains: list[str] | None = None
    allowed_symbols: list[str] | None = None


class DryRunArgs(BaseModel):
    chain: str
    symbol: str
    notional_usd: float = Field(gt=0)


class TickArgs(BaseModel):
    chain: str
    symbol: str
    notional_usd: float = Field(gt=0)


def build_autonomy_tools(runtime: AureyRuntime) -> list[Any]:
    @tool(args_schema=ConfigurePolicyArgs)
    def autonomy_configure_policy(
        armed: bool | None = None,
        max_trade_usd: float | None = None,
        daily_cap_usd: float | None = None,
        slippage_max: float | None = None,
        allowed_chains: list[str] | None = None,
        allowed_symbols: list[str] | None = None,
    ) -> dict[str, Any]:
        """Set local autonomy guardrails (persisted JSON on disk). Does not sign transactions."""
        policy = load_policy(runtime)
        updates = {
            "armed": armed,
            "max_trade_usd": max_trade_usd,
            "daily_cap_usd": daily_cap_usd,
            "slippage_max": slippage_max,
            "allowed_chains": allowed_chains,
            "allowed_symbols": allowed_symbols,
        }
        for key, val in updates.items():
            if val is None:
                continue
            setattr(policy, key, val)
        policy.commission_bps = int(runtime.settings.autonomy_commission_bps)
        save_policy(runtime, policy)
        return {"ok": True, "result": policy.__dict__}

    @tool(args_schema=DryRunArgs)
    def autonomy_dry_run(chain: str, symbol: str, notional_usd: float) -> dict[str, Any]:
        """Evaluate whether a trade would pass local policy (no signing)."""
        policy = load_policy(runtime)
        reasons: list[str] = []
        if not policy.armed:
            reasons.append("policy_not_armed")
        if chain.strip().lower() not in {c.lower() for c in policy.allowed_chains}:
            reasons.append("chain_not_allowed")
        if symbol.strip().upper() not in {s.upper() for s in policy.allowed_symbols}:
            reasons.append("symbol_not_allowed")
        if notional_usd > policy.max_trade_usd:
            reasons.append("max_trade_exceeded")
        if _STATE.spent_usd_today + notional_usd > policy.daily_cap_usd:
            reasons.append("daily_cap_exceeded")
        decision = {
            "ts": datetime.now(UTC).isoformat(),
            "kind": "dry_run",
            "chain": chain,
            "symbol": symbol,
            "notional_usd": notional_usd,
            "allowed": not reasons,
            "reasons": reasons,
        }
        append_decision(decision)
        return {"ok": True, "result": decision}

    @tool(args_schema=TickArgs)
    def autonomy_tick(chain: str, symbol: str, notional_usd: float) -> dict[str, Any]:
        """Fetch x402 recommendation (if configured) and re-check policy. No execute."""
        dry = autonomy_dry_run(chain=chain, symbol=symbol, notional_usd=notional_usd)
        result = dry.get("result", {})
        if not result.get("allowed"):
            return dry
        base = (runtime.settings.autonomy_x402_url or "").strip().rstrip("/")
        signal: dict[str, Any] | None = None
        if base:
            try:
                from urllib.parse import urlencode

                qs = urlencode(
                    {
                        "chain": chain,
                        "symbol": symbol,
                        "notional_usd": str(notional_usd),
                    }
                )
                signal = runtime.http.request_json(
                    method="GET",
                    url=f"{base}/v1/recommendation?{qs}",
                    headers={"Accept": "application/json"},
                    json_body=None,
                )
            except Exception as exc:
                return {
                    "ok": False,
                    "error": {"code": "x402_unavailable", "message": str(exc)[:400]},
                }
        entry = {
            "ts": datetime.now(UTC).isoformat(),
            "kind": "tick",
            "chain": chain,
            "symbol": symbol,
            "notional_usd": notional_usd,
            "signal": signal,
            "commission_bps": load_policy(runtime).commission_bps,
            "next_step": (
                "Call swap_prepare then tx_execute manually until autonomous execution is enabled."
            ),
        }
        append_decision(entry)
        return {"ok": True, "result": entry}

    @tool
    def autonomy_status() -> dict[str, Any]:
        """Return armed state, policy snapshot, and recent decision log tail."""
        policy = load_policy(runtime)
        return {
            "ok": True,
            "result": {
                "policy": policy.__dict__,
                "spent_usd_today": _STATE.spent_usd_today,
                "recent_decisions": _STATE.decision_log[-20:],
            },
        }

    @tool
    def autonomy_pause() -> dict[str, Any]:
        """Disarm autonomous trading immediately."""
        policy = load_policy(runtime)
        policy.armed = False
        save_policy(runtime, policy)
        append_decision({"ts": datetime.now(UTC).isoformat(), "kind": "pause"})
        return {"ok": True, "result": {"armed": False}}

    return [
        autonomy_configure_policy,
        autonomy_dry_run,
        autonomy_tick,
        autonomy_status,
        autonomy_pause,
    ]


__all__ = ["AutonomyPolicy", "build_autonomy_tools", "load_policy"]
