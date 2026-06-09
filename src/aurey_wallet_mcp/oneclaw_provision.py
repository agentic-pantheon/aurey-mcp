"""Provision 1Claw vault + Intents agent for Aurey using a human API key (1ck_…)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote

import httpx

DEFAULT_ONECLAW_BASE_URL = "https://api.1claw.xyz"
DEFAULT_VAULT_NAME = "aurey-wallet"
DEFAULT_AGENT_NAME = "Aurey Wallet MCP"
DEFAULT_AGENT_DESCRIPTION = "Aurey Wallet MCP — Intents signing and vault reads"


class OneClawProvisionError(RuntimeError):
    """1Claw Human API step failed; messages must not contain secret values."""


@dataclass(frozen=True)
class ProvisionResult:
    vault_id: str
    agent_id: str
    agent_api_key: str
    ethereum_address: str | None
    alchemy_secret_path: str | None


def _problem_detail(resp: httpx.Response) -> str:
    try:
        data = resp.json()
    except json.JSONDecodeError:
        return (resp.text or "")[:240]
    if isinstance(data, dict):
        for key in ("detail", "title", "message", "error"):
            val = data.get(key)
            if isinstance(val, str) and val.strip():
                return val.strip()[:240]
        if isinstance(data.get("errors"), list) and data["errors"]:
            first = data["errors"][0]
            if isinstance(first, dict) and isinstance(first.get("message"), str):
                return first["message"][:240]
    return f"HTTP {resp.status_code}"


def _collection_items(payload: Any, *keys: str) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [x for x in payload if isinstance(x, dict)]
    if not isinstance(payload, dict):
        return []
    for key in keys:
        raw = payload.get(key)
        if isinstance(raw, list):
            return [x for x in raw if isinstance(x, dict)]
    return []


def _secret_path_url(vault_id: str, path: str) -> str:
    segments = [s for s in path.strip().split("/") if s]
    if not segments:
        raise OneClawProvisionError("Secret path must not be empty.")
    suffix = "/".join(quote(part, safe="") for part in segments)
    return f"/v1/vaults/{quote(vault_id.strip(), safe='')}/secrets/{suffix}"


class OneClawHumanClient:
    """Minimal Human API client (Bearer JWT or 1ck_ personal key)."""

    def __init__(
        self,
        *,
        base_url: str = DEFAULT_ONECLAW_BASE_URL,
        bearer_token: str,
        timeout_s: float = 30.0,
    ) -> None:
        token = bearer_token.strip()
        if not token:
            raise ValueError("bearer_token must be non-empty.")
        self._base = base_url.rstrip("/")
        self._client = httpx.Client(
            base_url=self._base,
            timeout=timeout_s,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
            },
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> OneClawHumanClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    @staticmethod
    def human_bearer_from_personal_api_key(
        api_key: str,
        *,
        base_url: str = DEFAULT_ONECLAW_BASE_URL,
    ) -> str:
        """Return a Bearer token for Human API calls (JWT exchange or 1ck_ passthrough)."""

        key = api_key.strip()
        if not key:
            raise ValueError("api_key must be non-empty.")
        if key.startswith("eyJ"):
            return key
        with httpx.Client(base_url=base_url.rstrip("/"), timeout=30.0) as client:
            exchange_error: str | None = None
            if key.startswith("1ck_"):
                resp = client.post(
                    "/v1/auth/api-key-token",
                    json={"api_key": key},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    token = data.get("access_token") if isinstance(data, dict) else None
                    if isinstance(token, str) and token.strip():
                        return token.strip()
                exchange_error = _problem_detail(resp)
            probe = client.get(
                "/v1/vaults",
                headers={"Authorization": f"Bearer {key}"},
            )
            if probe.status_code == 200:
                return key
            if exchange_error:
                raise OneClawProvisionError(
                    f"Could not exchange personal API key for JWT ({exchange_error})."
                )
        raise OneClawProvisionError(
            "Invalid 1Claw human credential. Use a personal API key (1ck_…) from the dashboard."
        )

    def _raise(self, resp: httpx.Response, context: str) -> None:
        raise OneClawProvisionError(f"{context}: {_problem_detail(resp)}")

    def list_vaults(self) -> list[dict[str, Any]]:
        resp = self._client.get("/v1/vaults")
        if resp.status_code != 200:
            self._raise(resp, "List vaults failed")
        return _collection_items(resp.json(), "vaults", "items")

    def create_vault(self, name: str) -> dict[str, Any]:
        resp = self._client.post("/v1/vaults", json={"name": name.strip()})
        if resp.status_code not in (200, 201):
            self._raise(resp, "Create vault failed")
        data = resp.json()
        if isinstance(data, dict) and isinstance(data.get("vault"), dict):
            return data["vault"]
        if isinstance(data, dict) and data.get("id"):
            return data
        raise OneClawProvisionError("Create vault returned an unexpected response shape.")

    def create_agent(
        self,
        *,
        name: str,
        description: str,
        intents_api_enabled: bool = True,
    ) -> tuple[str, str]:
        body: dict[str, Any] = {
            "name": name.strip(),
            "description": description.strip(),
            "intents_api_enabled": intents_api_enabled,
            "scopes": ["vaults:read"],
        }
        resp = self._client.post("/v1/agents", json=body)
        if resp.status_code not in (200, 201):
            self._raise(resp, "Create agent failed")
        data = resp.json()
        if not isinstance(data, dict):
            raise OneClawProvisionError("Create agent returned an unexpected response shape.")
        agent = data.get("agent") if isinstance(data.get("agent"), dict) else data
        api_key = data.get("api_key")
        if not isinstance(agent, dict):
            raise OneClawProvisionError("Create agent response missing agent record.")
        agent_id = agent.get("id")
        if not isinstance(agent_id, str) or not agent_id.strip():
            raise OneClawProvisionError("Create agent response missing agent id.")
        if not isinstance(api_key, str) or not api_key.strip():
            raise OneClawProvisionError(
                "Create agent response missing api_key (ocv_…). Rotate key in 1Claw if reusing an agent."
            )
        return agent_id.strip(), api_key.strip()

    def create_policy(
        self,
        *,
        vault_id: str,
        agent_id: str,
        secret_path_pattern: str,
        permissions: list[str] | None = None,
    ) -> None:
        perms = permissions or ["read"]
        resp = self._client.post(
            f"/v1/vaults/{quote(vault_id.strip(), safe='')}/policies",
            json={
                "secret_path_pattern": secret_path_pattern,
                "principal_type": "agent",
                "principal_id": agent_id.strip(),
                "permissions": perms,
            },
        )
        if resp.status_code in (200, 201):
            return
        if resp.status_code == 409:
            return
        self._raise(resp, "Create vault policy failed")

    def put_secret(self, *, vault_id: str, path: str, value: str) -> None:
        resp = self._client.put(
            _secret_path_url(vault_id, path),
            json={"type": "api_key", "value": value},
        )
        if resp.status_code not in (200, 201):
            self._raise(resp, f"Store secret at {path!r} failed")

    def provision_signing_key(self, *, agent_id: str, chain: str = "ethereum") -> str | None:
        ag = agent_id.strip()
        list_resp = self._client.get(f"/v1/agents/{quote(ag, safe='')}/signing-keys")
        if list_resp.status_code == 200:
            for item in _collection_items(list_resp.json(), "signing_keys", "keys", "items"):
                if (item.get("chain") or "").lower() == chain.lower():
                    addr = item.get("address")
                    if isinstance(addr, str) and addr.strip():
                        return addr.strip()
        resp = self._client.post(
            f"/v1/agents/{quote(ag, safe='')}/signing-keys",
            json={"chain": chain},
        )
        if resp.status_code in (200, 201):
            data = resp.json()
            if isinstance(data, dict):
                addr = data.get("address")
                if isinstance(addr, str) and addr.strip():
                    return addr.strip()
                inner = data.get("signing_key")
                if isinstance(inner, dict):
                    addr2 = inner.get("address")
                    if isinstance(addr2, str) and addr2.strip():
                        return addr2.strip()
            return None
        if resp.status_code == 409:
            return None
        self._raise(resp, f"Provision {chain} signing key failed")
        return None


def resolve_vault_id(
    client: OneClawHumanClient,
    *,
    vault_id: str | None,
    vault_name: str,
) -> str:
    if vault_id and vault_id.strip():
        return vault_id.strip()
    vaults = client.list_vaults()
    if not vaults:
        created = client.create_vault(vault_name)
        vid = created.get("id")
        if isinstance(vid, str) and vid.strip():
            return vid.strip()
        raise OneClawProvisionError("Created vault but response had no id.")
    target = vault_name.strip().lower()
    for v in vaults:
        name = (v.get("name") or "").strip().lower()
        vid = v.get("id")
        if name == target and isinstance(vid, str) and vid.strip():
            return vid.strip()
    if len(vaults) == 1:
        only = vaults[0].get("id")
        if isinstance(only, str) and only.strip():
            return only.strip()
    first = vaults[0].get("id")
    if isinstance(first, str) and first.strip():
        return first.strip()
    raise OneClawProvisionError("Could not determine a vault id from your 1Claw account.")


def provision_for_aurey(
    human_api_key: str,
    *,
    base_url: str = DEFAULT_ONECLAW_BASE_URL,
    vault_id: str | None = None,
    vault_name: str = DEFAULT_VAULT_NAME,
    agent_name: str = DEFAULT_AGENT_NAME,
    agent_description: str = DEFAULT_AGENT_DESCRIPTION,
    alchemy_api_key: str | None = None,
    alchemy_secret_path: str = "api-keys/alchemy",
) -> ProvisionResult:
    """Create (or reuse) vault, agent, policies, optional Alchemy secret, Ethereum signing key."""

    bearer = OneClawHumanClient.human_bearer_from_personal_api_key(
        human_api_key, base_url=base_url
    )
    alchemy_path: str | None = None
    with OneClawHumanClient(base_url=base_url, bearer_token=bearer) as client:
        vid = resolve_vault_id(client, vault_id=vault_id, vault_name=vault_name)
        agent_id, ocv = client.create_agent(
            name=agent_name,
            description=agent_description,
            intents_api_enabled=True,
        )
        client.create_policy(
            vault_id=vid,
            agent_id=agent_id,
            secret_path_pattern="api-keys/**",
        )
        if alchemy_api_key and alchemy_api_key.strip():
            path = alchemy_secret_path.strip() or "api-keys/alchemy"
            client.put_secret(vault_id=vid, path=path, value=alchemy_api_key.strip())
            alchemy_path = path
        eth_address = client.provision_signing_key(agent_id=agent_id, chain="ethereum")

    return ProvisionResult(
        vault_id=vid,
        agent_id=agent_id,
        agent_api_key=ocv,
        ethereum_address=eth_address,
        alchemy_secret_path=alchemy_path,
    )


__all__ = [
    "DEFAULT_AGENT_NAME",
    "DEFAULT_VAULT_NAME",
    "OneClawHumanClient",
    "OneClawProvisionError",
    "ProvisionResult",
    "provision_for_aurey",
]
