"""Resolve agent wallet addresses from 1Claw Intents signing-keys (no manual 0x required)."""

from __future__ import annotations

import logging
from typing import Any

from aurey.custody.signing_keys_parse import (
    ethereum_address_from_signing_keys_payload,
    solana_address_from_signing_keys_payload,
)
from aurey.graphs.evm_codec import to_checksum_evm_address
from aurey.runtime import AureyRuntime

_log = logging.getLogger(__name__)


def effective_evm_wallet_address(runtime: AureyRuntime) -> str | None:
    """Primary EVM wallet: optional settings override, else agent signing-keys cache."""

    override = (runtime.settings.deep_agent_wallet_address or "").strip()
    if override:
        try:
            return to_checksum_evm_address(override)
        except ValueError:
            _log.warning("Ignoring invalid deep_agent_wallet_address override.")
    cached = (runtime.agent_evm_wallet_address or "").strip()
    return cached or None


def fetch_agent_wallet_addresses_from_oneclaw(
    runtime: AureyRuntime,
) -> tuple[str | None, str | None]:
    """GET signing-keys for ``oneclaw_agent_id`` using bootstrap credential."""

    settings = runtime.settings
    aid = (settings.oneclaw_agent_id or "").strip()
    client = runtime.oneclaw_evm_signer
    if not aid or client is None:
        return None, None
    try:
        bootstrap = settings.resolve_oneclaw_bootstrap_api_key()
    except (KeyError, ValueError):
        return None, None
    get_json = getattr(client, "get_agent_signing_keys_json", None)
    if not callable(get_json):
        return None, None
    try:
        payload = get_json(aid, agent_api_key=bootstrap)
    except Exception as exc:
        _log.info(
            "Agent signing-keys lookup failed agent_id=%s (%s)",
            aid,
            type(exc).__name__,
        )
        return None, None
    eth = ethereum_address_from_signing_keys_payload(payload)
    sol = solana_address_from_signing_keys_payload(payload)
    return eth, sol


def hydrate_runtime_agent_wallets(runtime: AureyRuntime) -> AureyRuntime:
    """Attach signing-key addresses to runtime (immutable dataclass replace)."""

    eth, sol = fetch_agent_wallet_addresses_from_oneclaw(runtime)
    if eth is None and sol is None:
        return runtime
    return AureyRuntime(
        settings=runtime.settings,
        secret_store=runtime.secret_store,
        evm_rpc_factory=runtime.evm_rpc_factory,
        http=runtime.http,
        tx_pipeline=runtime.tx_pipeline,
        oneclaw_evm_signer=runtime.oneclaw_evm_signer,
        lifi_base_url=runtime.lifi_base_url,
        prepared_txs=runtime.prepared_txs,
        decimals_cache=runtime.decimals_cache,
        token_resolver=runtime.token_resolver,
        hosted_session_factory=runtime.hosted_session_factory,
        agent_evm_wallet_address=eth or runtime.agent_evm_wallet_address,
        agent_solana_wallet_address=sol or runtime.agent_solana_wallet_address,
    )


def agent_wallet_status(runtime: AureyRuntime) -> dict[str, Any]:
    """Tool/dashboard payload for agent-bound wallets."""

    evm = effective_evm_wallet_address(runtime)
    sol = (runtime.agent_solana_wallet_address or "").strip() or None
    override = bool((runtime.settings.deep_agent_wallet_address or "").strip())
    source = "settings_override" if override else ("oneclaw_signing_keys" if evm else "unset")
    return {
        "ethereum": evm,
        "solana": sol,
        "evm_source": source,
        "agent_id": (runtime.settings.oneclaw_agent_id or "").strip() or None,
        "signing_mode": runtime.settings.evm_signing_mode,
        "hint": (
            "Complete 1Claw agent setup (claim / provision Ethereum signing key) if addresses are unset."
            if not evm
            else None
        ),
    }


__all__ = [
    "agent_wallet_status",
    "effective_evm_wallet_address",
    "fetch_agent_wallet_addresses_from_oneclaw",
    "hydrate_runtime_agent_wallets",
]
