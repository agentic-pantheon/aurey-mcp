"""Build :class:`~aurey.runtime.AureyRuntime` for standalone wallet plugin use."""

from __future__ import annotations

import os

from aurey.custody.agent_wallet import effective_evm_wallet_address, hydrate_runtime_agent_wallets
from aurey.custody.caching_secret_store import CachingSecretStore
from aurey.custody.secret_store import OneClawHttpClient, OneClawSecretStore
from aurey.graphs.evm_tx_pipeline import Web3TxPipeline
from aurey.runtime import AureyRuntime
from aurey.service.adapters import HttpxJsonClient, make_evm_rpc_factory, make_shared_httpx_client
from aurey.settings import AureySettings
from aurey.token_registry.lifi_file_repository import build_token_registry_repository
from aurey.token_registry.resolver import TokenResolver
from aurey.util.ttl_lru_cache import TtlLruCache


class AureyRuntimeBootstrapError(RuntimeError):
    """Mandatory runtime wiring failed; messages must not contain secret values."""

_HUMAN_SETUP_ENV = "AUREY_ONECLAW_HUMAN_API_KEY"
_VAULT_API_KEY_ENVS = ("AUREY_ONECLAW_VAULT_API_KEY", "AUREY_ONECLAW_BOOTSTRAP_API_KEY")


def _reject_setup_only_credentials_in_process_env() -> None:
    if os.environ.get(_HUMAN_SETUP_ENV, "").strip():
        raise AureyRuntimeBootstrapError(
            f"{_HUMAN_SETUP_ENV} must not be set when running MCP — it is for aurey-setup only. "
            "Unset it and use AUREY_ONECLAW_VAULT_API_KEY (ocv_…) from provisioning."
        )
    for name in _VAULT_API_KEY_ENVS:
        val = os.environ.get(name, "").strip()
        if val.startswith("1ck_"):
            raise AureyRuntimeBootstrapError(
                f"{name} must be the agent API key (ocv_…), not a human personal key (1ck_…). "
                "Re-run aurey-setup and keep the human key out of mcp.env."
            )


def bootstrap_aurey_runtime(settings: AureySettings | None = None) -> AureyRuntime:
    """Wire 1Claw secret store and EVM tooling for MCP / local dashboard (no hosted SaaS)."""

    s = settings or AureySettings()
    if s.hosted_platform_enabled:
        raise AureyRuntimeBootstrapError(
            "aurey-wallet-mcp runs in standalone mode only (set AUREY_HOSTED_PLATFORM_ENABLED=false)."
        )
    _reject_setup_only_credentials_in_process_env()
    vault_id = (s.oneclaw_vault_id or "").strip()
    if not vault_id:
        raise AureyRuntimeBootstrapError("1Claw vault id is not configured (AUREY_ONECLAW_VAULT_ID).")

    try:
        api_key = s.resolve_oneclaw_bootstrap_api_key()
    except KeyError:
        raise AureyRuntimeBootstrapError(
            "1Claw vault API key is unavailable (set AUREY_ONECLAW_VAULT_API_KEY or "
            "legacy AUREY_ONECLAW_BOOTSTRAP_API_KEY)."
        ) from None
    except ValueError:
        raise AureyRuntimeBootstrapError("Bootstrap 1Claw API key configuration is invalid.") from None

    if s.evm_signing_mode == "oneclaw_intents" and not str(s.oneclaw_agent_id or "").strip():
        raise AureyRuntimeBootstrapError(
            "oneclaw_intents signing requires AUREY_ONECLAW_AGENT_ID for standalone installs."
        )

    mode = s.evm_signing_mode
    if mode != "oneclaw_intents":
        raise AureyRuntimeBootstrapError(
            "aurey-wallet-mcp requires AUREY_EVM_SIGNING_MODE=oneclaw_intents (Intents-only onboarding)."
        )

    client = OneClawHttpClient(
        base_url=s.oneclaw_base_url.strip(),
        api_key=api_key,
        agent_token_expiry_skew_seconds=s.oneclaw_agent_token_expiry_skew_seconds,
        hosted_settings_for_ocv=None,
    )
    store = OneClawSecretStore(client=client, vault_id=vault_id, agent_id=s.oneclaw_agent_id)
    secret_store = store
    ttl = float(s.secret_cache_ttl_seconds)
    if ttl > 0:
        secret_store = CachingSecretStore(store, ttl_s=ttl)

    httpx_client = make_shared_httpx_client()
    http_adapter = HttpxJsonClient(httpx_client)

    decimals_cache = TtlLruCache[tuple[str, str], int](
        maxsize=s.token_decimals_cache_maxsize,
        ttl_s=max(s.token_decimals_cache_ttl_seconds, 1.0),
    )

    runtime = AureyRuntime(
        settings=s,
        secret_store=secret_store,
        evm_rpc_factory=make_evm_rpc_factory(httpx_client),
        http=http_adapter,
        tx_pipeline=Web3TxPipeline(settings=s, secret_store=secret_store),
        oneclaw_evm_signer=client,
        lifi_base_url=(s.lifi_base_url or "https://li.quest").strip(),
        hosted_session_factory=None,
        decimals_cache=decimals_cache,
    )

    runtime = hydrate_runtime_agent_wallets(runtime)
    if not effective_evm_wallet_address(runtime) and not (s.deep_agent_wallet_address or "").strip():
        raise AureyRuntimeBootstrapError(
            "No EVM wallet on agent yet. Complete 1Claw agent setup (claim / provision "
            "Ethereum signing key), then restart MCP. Optional override: AUREY_DEEP_AGENT_WALLET_ADDRESS."
        )

    repo = build_token_registry_repository(lifi_tokens_path=s.effective_lifi_tokens_path())
    token_resolver = TokenResolver(runtime=runtime, repository=repo)
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
        token_resolver=token_resolver,
        hosted_session_factory=None,
        agent_evm_wallet_address=runtime.agent_evm_wallet_address,
        agent_solana_wallet_address=runtime.agent_solana_wallet_address,
    )


__all__ = ["AureyRuntimeBootstrapError", "bootstrap_aurey_runtime"]
