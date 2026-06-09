"""Resolve Mini App / dashboard user's EVM wallet from 1Claw agent signing-keys."""

from __future__ import annotations

from dataclasses import dataclass

from aurey.custody.agent_wallet import effective_evm_wallet_address
from aurey.runtime import AureyRuntime


@dataclass(frozen=True)
class ResolvedMiniappUser:
    has_row: bool
    onboarding_state: str | None
    wallet_address: str | None


def resolve_wallet_for_dashboard(runtime: AureyRuntime) -> ResolvedMiniappUser:
    """Return agent-bound EVM wallet for read-only portfolio views."""

    evm = effective_evm_wallet_address(runtime)
    if not evm:
        return ResolvedMiniappUser(has_row=False, onboarding_state=None, wallet_address=None)
    return ResolvedMiniappUser(has_row=True, onboarding_state="ready", wallet_address=evm)


__all__ = ["ResolvedMiniappUser", "resolve_wallet_for_dashboard"]
