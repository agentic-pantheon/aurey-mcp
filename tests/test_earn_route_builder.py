"""Earn graph routing via hosted route-builder."""

from __future__ import annotations

import pytest

from aurey.graphs.earn import _earn_api_url, build_earn_graph
from aurey.graphs.evm_tx_pipeline import Web3TxPipeline
from aurey.runtime import AureyRuntime
from aurey.service.adapters import make_evm_rpc_factory, make_shared_httpx_client
from aurey.settings import AureySettings
from tests.fakes.http_client import ScriptedHttpClient
from tests.fakes.secret_store import fake_oneclaw_secret_store


def test_earn_api_url_proxy_vs_direct() -> None:
    assert (
        _earn_api_url(
            proxy_base="https://rb.example/v1/earn",
            direct_base="https://earn.li.fi",
            relative="chains",
        )
        == "https://rb.example/v1/earn/chains"
    )
    assert (
        _earn_api_url(
            proxy_base=None,
            direct_base="https://earn.li.fi",
            relative="chains",
        )
        == "https://earn.li.fi/v1/chains"
    )


def _minimal_runtime(
    monkeypatch: pytest.MonkeyPatch,
    *,
    route_builder_url: str | None,
    route_builder_api_key: str | None,
    http: ScriptedHttpClient,
) -> AureyRuntime:
    monkeypatch.setenv("AUREY_HOSTED_PLATFORM_ENABLED", "false")
    monkeypatch.setenv("AUREY_ONECLAW_VAULT_ID", "vault-test")
    monkeypatch.setenv("AUREY_ONECLAW_BOOTSTRAP_API_KEY", "ocv_test_key")
    monkeypatch.setenv("AUREY_ONECLAW_AGENT_ID", "00000000-0000-4000-8000-000000000001")
    monkeypatch.setenv("AUREY_ALCHEMY_API_KEY", "alchemy_test")
    if route_builder_url is None:
        monkeypatch.delenv("AUREY_ROUTE_BUILDER_URL", raising=False)
    else:
        monkeypatch.setenv("AUREY_ROUTE_BUILDER_URL", route_builder_url)
    if route_builder_api_key is None:
        monkeypatch.delenv("AUREY_ROUTE_BUILDER_API_KEY", raising=False)
    else:
        monkeypatch.setenv("AUREY_ROUTE_BUILDER_API_KEY", route_builder_api_key)
    settings = AureySettings()
    store = fake_oneclaw_secret_store()
    httpx_client = make_shared_httpx_client()
    return AureyRuntime(
        settings=settings,
        secret_store=store,
        evm_rpc_factory=make_evm_rpc_factory(httpx_client),
        http=http,
        tx_pipeline=Web3TxPipeline(settings=settings, secret_store=store),
        oneclaw_evm_signer=None,
    )


def test_earn_list_chains_uses_route_builder(monkeypatch: pytest.MonkeyPatch) -> None:
    http = ScriptedHttpClient(
        [
            (
                lambda *, method, url, headers, json_body: method == "GET"
                and url == "https://rb.test/v1/earn/chains",
                [{"chainId": 8453, "name": "Base"}],
            )
        ]
    )
    runtime = _minimal_runtime(
        monkeypatch,
        route_builder_url="https://rb.test",
        route_builder_api_key="rb-secret",
        http=http,
    )
    out = build_earn_graph(runtime).invoke({"input": {"operation": "list_chains"}})
    assert out["result"]["chains"][0]["chain_id"] == 8453
    call = http.calls[0]
    assert call["headers"]["Authorization"] == "Bearer rb-secret"
    assert "x-lifi-api-key" not in (call["headers"] or {})


def test_earn_direct_when_route_builder_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    http = ScriptedHttpClient(
        [
            (
                lambda *, method, url, headers, json_body: method == "GET"
                and url == "https://earn.li.fi/v1/chains",
                [{"chainId": 1, "name": "Ethereum"}],
            )
        ]
    )
    runtime = _minimal_runtime(
        monkeypatch,
        route_builder_url="",
        route_builder_api_key=None,
        http=http,
    )
    out = build_earn_graph(runtime).invoke({"input": {"operation": "list_chains"}})
    assert out["result"]["chains"][0]["chain_id"] == 1
    assert http.calls[0]["url"] == "https://earn.li.fi/v1/chains"
