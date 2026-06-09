"""Tests for 1Claw Human API provisioning helper."""

from __future__ import annotations

import httpx
import pytest

from aurey_wallet_mcp import oneclaw_provision as provision_mod
from aurey_wallet_mcp.oneclaw_provision import (
    OneClawHumanClient,
    OneClawProvisionError,
    provision_for_aurey,
    resolve_vault_id,
)


def test_human_bearer_exchanges_1ck_key(monkeypatch: pytest.MonkeyPatch) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v1/auth/api-key-token":
            return httpx.Response(200, json={"access_token": "jwt-human", "expires_in": 900})
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    real_client = httpx.Client

    def factory(*args: object, **kwargs: object) -> httpx.Client:
        base = kwargs.get("base_url", "https://api.example")
        url = base.rstrip("/") if isinstance(base, str) else "https://api.example"
        kwargs = dict(kwargs)
        kwargs["transport"] = transport
        kwargs["base_url"] = url
        kwargs.setdefault("timeout", 30.0)
        return real_client(**kwargs)

    monkeypatch.setattr(provision_mod.httpx, "Client", factory)
    token = OneClawHumanClient.human_bearer_from_personal_api_key(
        "1ck_test", base_url="https://api.example"
    )
    assert token == "jwt-human"


def test_resolve_vault_id_uses_existing_single_vault() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v1/vaults":
            return httpx.Response(200, json={"vaults": [{"id": "vault-1", "name": "main"}]})
        return httpx.Response(404)

    client = OneClawHumanClient(
        base_url="https://api.example",
        bearer_token="jwt",
    )
    client._client = httpx.Client(
        transport=httpx.MockTransport(handler),
        base_url="https://api.example",
        headers=client._client.headers,
    )
    try:
        assert resolve_vault_id(client, vault_id=None, vault_name="aurey-wallet") == "vault-1"
    finally:
        client.close()


def test_provision_for_aurey_happy_path(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []
    agent_create_body: dict | None = None

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal agent_create_body
        calls.append(f"{request.method} {request.url.path}")
        if request.url.path == "/v1/auth/api-key-token":
            return httpx.Response(200, json={"access_token": "jwt-human"})
        if request.url.path == "/v1/vaults" and request.method == "GET":
            return httpx.Response(200, json={"vaults": [{"id": "v-uuid", "name": "aurey-wallet"}]})
        if request.url.path == "/v1/agents" and request.method == "POST":
            import json

            agent_create_body = json.loads(request.content.decode())
            return httpx.Response(
                201,
                json={
                    "agent": {"id": "a-uuid", "name": "Aurey Wallet MCP"},
                    "api_key": "ocv_secret",
                },
            )
        if request.url.path.endswith("/policies"):
            return httpx.Response(201, json={"id": "pol-1"})
        if "/secrets/" in request.url.path and request.method == "PUT":
            return httpx.Response(201, json={"path": "api-keys/alchemy"})
        if request.url.path.endswith("/signing-keys") and request.method == "GET":
            return httpx.Response(200, json={"signing_keys": []})
        if request.url.path.endswith("/signing-keys") and request.method == "POST":
            return httpx.Response(201, json={"address": "0xabc"})
        return httpx.Response(404, json={"detail": "not found"})

    transport = httpx.MockTransport(handler)
    real_client = httpx.Client

    def factory(*args: object, **kwargs: object) -> httpx.Client:
        base = kwargs.get("base_url", "https://api.example")
        url = base.rstrip("/") if isinstance(base, str) else "https://api.example"
        kwargs = dict(kwargs)
        kwargs["transport"] = transport
        kwargs["base_url"] = url
        kwargs.setdefault("timeout", 30.0)
        return real_client(**kwargs)

    monkeypatch.setattr(provision_mod.httpx, "Client", factory)
    result = provision_for_aurey(
        "1ck_test",
        base_url="https://api.example",
        alchemy_api_key="alchemy-plain",
    )

    assert result.vault_id == "v-uuid"
    assert result.agent_id == "a-uuid"
    assert result.agent_api_key == "ocv_secret"
    assert result.ethereum_address == "0xabc"
    assert result.alchemy_secret_path == "api-keys/alchemy"
    assert result.lifi_secret_path is None
    assert any("POST /v1/agents" in c for c in calls)
    assert agent_create_body is not None
    assert "scopes" not in agent_create_body


def test_provision_stores_lifi_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    secret_puts: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v1/auth/api-key-token":
            return httpx.Response(200, json={"access_token": "jwt-human"})
        if request.url.path == "/v1/vaults" and request.method == "GET":
            return httpx.Response(200, json={"vaults": [{"id": "v-uuid", "name": "aurey-wallet"}]})
        if request.url.path == "/v1/agents" and request.method == "POST":
            return httpx.Response(
                201,
                json={
                    "agent": {"id": "a-uuid", "name": "Aurey Wallet MCP"},
                    "api_key": "ocv_secret",
                },
            )
        if request.url.path.endswith("/policies"):
            return httpx.Response(201, json={"id": "pol-1"})
        if "/secrets/" in request.url.path and request.method == "PUT":
            secret_puts.append(request.url.path)
            return httpx.Response(201, json={"path": "ok"})
        if request.url.path.endswith("/signing-keys") and request.method == "GET":
            return httpx.Response(200, json={"signing_keys": []})
        if request.url.path.endswith("/signing-keys") and request.method == "POST":
            return httpx.Response(201, json={"address": "0xabc"})
        return httpx.Response(404, json={"detail": "not found"})

    transport = httpx.MockTransport(handler)
    real_client = httpx.Client

    def factory(*args: object, **kwargs: object) -> httpx.Client:
        base = kwargs.get("base_url", "https://api.example")
        url = base.rstrip("/") if isinstance(base, str) else "https://api.example"
        kwargs = dict(kwargs)
        kwargs["transport"] = transport
        kwargs["base_url"] = url
        kwargs.setdefault("timeout", 30.0)
        return real_client(**kwargs)

    monkeypatch.setattr(provision_mod.httpx, "Client", factory)
    result = provision_for_aurey(
        "1ck_test",
        base_url="https://api.example",
        lifi_api_key="lifi-plain",
    )
    assert result.lifi_secret_path == "api-keys/lifi"
    assert any("/secrets/api-keys/lifi" in p for p in secret_puts)


def test_provision_raises_on_agent_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v1/auth/api-key-token":
            return httpx.Response(200, json={"access_token": "jwt"})
        if request.url.path == "/v1/vaults":
            return httpx.Response(200, json={"vaults": [{"id": "v1", "name": "x"}]})
        if request.url.path == "/v1/agents":
            return httpx.Response(403, json={"detail": "forbidden"})
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    real_client = httpx.Client

    def factory(*args: object, **kwargs: object) -> httpx.Client:
        base = kwargs.get("base_url", "https://api.example")
        url = base.rstrip("/") if isinstance(base, str) else "https://api.example"
        kwargs = dict(kwargs)
        kwargs["transport"] = transport
        kwargs["base_url"] = url
        kwargs.setdefault("timeout", 30.0)
        return real_client(**kwargs)

    monkeypatch.setattr(provision_mod.httpx, "Client", factory)
    with pytest.raises(OneClawProvisionError, match="Create agent failed"):
        provision_for_aurey("1ck_x", base_url="https://api.example")
