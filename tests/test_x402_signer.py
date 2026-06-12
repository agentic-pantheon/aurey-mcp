from __future__ import annotations

from typing import Any

import pytest
from eth_utils import to_checksum_address
from x402.mechanisms.evm.types import TypedDataDomain, TypedDataField

from aurey.custody import FakeOneClawClient, OneClawSecretStore
from aurey.runtime import AureyRuntime
from aurey.settings import AureySettings
from aurey.x402.oneclaw_signer import OneClawEvmX402Signer
from tests.fakes.secret_store import TEST_VAULT_ID


class _RecordingFake(FakeOneClawClient):
    def __init__(self) -> None:
        super().__init__({})
        self.last_typed: dict[str, Any] | None = None

    def sign_typed_data(
        self,
        *,
        agent_id: str,
        chain: str,
        typed_data: dict[str, Any],
        signing_key_path: str | None = None,
        authorization_bearer: str | None = None,
    ) -> Any:
        self.last_typed = {"agent_id": agent_id, "chain": chain, "typed_data": typed_data}
        from aurey.custody.secret_store import OneClawTypedDataSignResult

        return OneClawTypedDataSignResult(
            signature="0x" + "11" * 65,
            signer_address="0x00000000000000000000000000000000000000aa",
        )


def test_oneclaw_signer_typed_data_bytes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUREY_HOSTED_PLATFORM_ENABLED", "false")
    monkeypatch.setenv("AUREY_ONECLAW_VAULT_ID", "vault-test")
    monkeypatch.setenv("AUREY_ONECLAW_AGENT_ID", "agent-1")
    settings = AureySettings()
    client = _RecordingFake()
    store = OneClawSecretStore(client=client, vault_id=TEST_VAULT_ID, agent_id="agent-1")

    runtime = AureyRuntime(
        settings=settings,
        secret_store=store,
        evm_rpc_factory=lambda _c: None,
        http=None,  # type: ignore[arg-type]
        tx_pipeline=None,  # type: ignore[arg-type]
        oneclaw_evm_signer=client,
        agent_evm_wallet_address="0x00000000000000000000000000000000000000aa",
    )
    signer = OneClawEvmX402Signer(runtime, signer=client, chain_slug="base")
    domain = TypedDataDomain(
        name="Test",
        version="1",
        chain_id=8453,
        verifying_contract=to_checksum_address("0x0000000000000000000000000000000000000001"),
    )
    types = {"Mail": [TypedDataField(name="contents", type="string")]}
    sig = signer.sign_typed_data(domain, types, "Mail", {"contents": "hello"})
    assert isinstance(sig, bytes)
    assert len(sig) == 65
    assert client.last_typed is not None
    assert client.last_typed["chain"] == "base"
    assert client.last_typed["typed_data"]["primaryType"] == "Mail"


def test_typed_data_json_safe_bytes_nonce(monkeypatch: pytest.MonkeyPatch) -> None:
    import json

    from x402.mechanisms.evm.types import TypedDataField

    from aurey.x402.oneclaw_signer import _typed_data_to_eip712_json

    out = _typed_data_to_eip712_json(
        {"name": "T", "version": "1", "chainId": 8453, "verifyingContract": "0x" + "1" * 40},
        {"Mail": [TypedDataField(name="nonce", type="bytes32")]},
        "Mail",
        {"nonce": b"\x01" * 32},
    )
    json.dumps(out)
    assert out["message"]["nonce"] == "0x" + "01" * 32
    assert "EIP712Domain" in out["types"]
