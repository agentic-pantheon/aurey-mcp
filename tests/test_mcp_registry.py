
import pytest

from aurey.settings import AureySettings
from aurey_wallet_mcp.tools import build_mcp_tool_registry
from tests.fakes.secret_store import fake_oneclaw_secret_store


@pytest.fixture
def minimal_settings(monkeypatch: pytest.MonkeyPatch) -> AureySettings:
    monkeypatch.setenv("AUREY_HOSTED_PLATFORM_ENABLED", "false")
    monkeypatch.setenv("AUREY_ONECLAW_VAULT_ID", "vault-test")
    monkeypatch.setenv("AUREY_ONECLAW_BOOTSTRAP_API_KEY", "ocv_test_key")
    monkeypatch.setenv("AUREY_ONECLAW_AGENT_ID", "00000000-0000-4000-8000-000000000001")
    monkeypatch.setenv("AUREY_EVM_SIGNING_MODE", "oneclaw_intents")
    monkeypatch.setenv("AUREY_ALCHEMY_API_KEY", "alchemy_test")
    return AureySettings()


def test_mcp_registry_includes_core_tools(minimal_settings: AureySettings) -> None:
    from aurey.graphs.evm_tx_pipeline import Web3TxPipeline
    from aurey.runtime import AureyRuntime
    from aurey.service.adapters import (
        HttpxJsonClient,
        make_evm_rpc_factory,
        make_shared_httpx_client,
    )

    httpx_client = make_shared_httpx_client()
    store = fake_oneclaw_secret_store()
    runtime = AureyRuntime(
        settings=minimal_settings,
        secret_store=store,
        evm_rpc_factory=make_evm_rpc_factory(httpx_client),
        http=HttpxJsonClient(httpx_client),
        tx_pipeline=Web3TxPipeline(settings=minimal_settings, secret_store=store),
        oneclaw_evm_signer=None,
    )
    registry = build_mcp_tool_registry(runtime)
    names = set(registry.keys())
    assert "evm_get_native_balance" in names
    assert "swap_prepare" in names
    assert "tx_execute" in names
    assert "get_agent_wallet_addresses" in names
    assert "resolve_hosted_recipient_by_handle" not in names
    assert "autonomy_configure_policy" not in names
    assert "x402_preview" not in names
    assert "x402_fetch" not in names


def test_mcp_registry_includes_x402_when_oneclaw_signer(minimal_settings: AureySettings) -> None:
    from aurey.custody import FakeOneClawClient
    from aurey.graphs.evm_tx_pipeline import Web3TxPipeline
    from aurey.runtime import AureyRuntime
    from aurey.service.adapters import (
        HttpxJsonClient,
        make_evm_rpc_factory,
        make_shared_httpx_client,
    )
    from tests.fakes.secret_store import fake_oneclaw_secret_store

    httpx_client = make_shared_httpx_client()
    store = fake_oneclaw_secret_store()
    signer = FakeOneClawClient({})
    runtime = AureyRuntime(
        settings=minimal_settings,
        secret_store=store,
        evm_rpc_factory=make_evm_rpc_factory(httpx_client),
        http=HttpxJsonClient(httpx_client),
        tx_pipeline=Web3TxPipeline(settings=minimal_settings, secret_store=store),
        oneclaw_evm_signer=signer,
        agent_evm_wallet_address="0x00000000000000000000000000000000000000aa",
    )
    registry = build_mcp_tool_registry(runtime)
    names = set(registry.keys())
    assert "x402_preview" in names
    assert "x402_fetch" in names
    assert "list_x402_services" in names
    assert "get_x402_service" in names
    assert "resolve_x402_endpoint" in names
