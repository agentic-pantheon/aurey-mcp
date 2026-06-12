from __future__ import annotations

import base64
import json
from unittest.mock import MagicMock, patch

import pytest
from x402.schemas import PaymentRequired, PaymentRequirements

from aurey.custody import FakeOneClawClient, OneClawSecretStore
from aurey.runtime import AureyRuntime
from aurey.settings import AureySettings
from aurey.x402.client import AureyX402Transport
from tests.fakes.secret_store import TEST_VAULT_ID


def _payment_required_header() -> str:
    pr = PaymentRequired(
        accepts=[
            PaymentRequirements(
                scheme="exact",
                network="eip155:8453",
                asset="0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
                amount="10000",
                pay_to="0x0000000000000000000000000000000000000001",
                maxTimeoutSeconds=60,
            )
        ]
    )
    raw = json.dumps(pr.model_dump(mode="json", by_alias=True)).encode()
    return base64.b64encode(raw).decode()


@pytest.fixture
def x402_runtime(monkeypatch: pytest.MonkeyPatch) -> AureyRuntime:
    monkeypatch.setenv("AUREY_HOSTED_PLATFORM_ENABLED", "false")
    monkeypatch.setenv("AUREY_ONECLAW_VAULT_ID", "vault-test")
    monkeypatch.setenv("AUREY_ONECLAW_AGENT_ID", "00000000-0000-4000-8000-000000000001")
    monkeypatch.setenv("AUREY_ALCHEMY_API_KEY", "alchemy_test")
    settings = AureySettings()
    client = FakeOneClawClient({})
    store = OneClawSecretStore(client=client, vault_id=TEST_VAULT_ID, agent_id=settings.oneclaw_agent_id)
    return AureyRuntime(
        settings=settings,
        secret_store=store,
        evm_rpc_factory=MagicMock(),
        http=MagicMock(),
        tx_pipeline=MagicMock(),
        oneclaw_evm_signer=client,
        agent_evm_wallet_address="0x00000000000000000000000000000000000000aa",
    )


def test_preview_parses_v2_payment_required(x402_runtime: AureyRuntime) -> None:
    header_val = _payment_required_header()

    class FakeResp:
        status_code = 402
        text = ""
        headers = {"PAYMENT-REQUIRED": header_val}

    with patch("aurey.x402.client.requests.request", return_value=FakeResp()):
        out = AureyX402Transport(x402_runtime).preview(url="https://api.example.com/resource")
    assert out["ok"] is True
    assert out["result"]["payment_required"] is True
    assert out["result"]["quote"]["scheme"] == "exact"
