"""Local dashboard HTTP API."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from aurey.miniapp.schemas import PortfolioSnapshot, PortfolioSummary, utc_now_iso
from aurey.settings import AureySettings
from aurey_wallet_mcp.dashboard import create_dashboard_app


def _minimal_snapshot() -> PortfolioSnapshot:
    return PortfolioSnapshot(
        wallet_address="0xabc",
        updated_at=utc_now_iso(),
        chains_queried=("ethereum",),
        chains_available=("ethereum",),
        summary=PortfolioSummary(total_usd="1.00", by_chain=[]),
        tokens=[],
        tokens_aggregated=[],
        defi=[],
        balance_chart=None,
        errors=[],
    )


@pytest.fixture
def dashboard_client() -> TestClient:
    settings = AureySettings(
        dashboard_enabled=True,
        dashboard_auth_token=None,
        oneclaw_vault_id="v",
        oneclaw_agent_id="a",
    )
    runtime = MagicMock()
    runtime.settings = settings
    runtime.prepared_txs = MagicMock()
    runtime.prepared_txs._lock = MagicMock()
    runtime.prepared_txs._records = {}

    with patch(
        "aurey.miniapp.wallet.resolve_wallet_for_dashboard",
        return_value=MagicMock(wallet_address="0xabc"),
    ):
        with patch(
            "aurey.miniapp.portfolio.aggregate_portfolio_snapshot",
            return_value=_minimal_snapshot(),
        ):
            app = create_dashboard_app(runtime, settings)
    return TestClient(app)


def test_dashboard_portfolio_tokenless(dashboard_client: TestClient) -> None:
    res = dashboard_client.post("/v1/dashboard/portfolio", json={"chart_period": "month"})
    assert res.status_code == 200
    assert res.json()["wallet_address"] == "0xabc"


def test_dashboard_portfolio_requires_auth_when_token_set() -> None:
    settings = AureySettings(
        dashboard_enabled=True,
        dashboard_auth_token="secret",
        oneclaw_vault_id="v",
        oneclaw_agent_id="a",
    )
    runtime = MagicMock()
    runtime.settings = settings
    runtime.prepared_txs = MagicMock()
    runtime.prepared_txs._lock = MagicMock()
    runtime.prepared_txs._records = {}

    with patch(
        "aurey.miniapp.wallet.resolve_wallet_for_dashboard",
        return_value=MagicMock(wallet_address="0xabc"),
    ):
        with patch(
            "aurey.miniapp.portfolio.aggregate_portfolio_snapshot",
            return_value=_minimal_snapshot(),
        ):
            app = create_dashboard_app(runtime, settings)
    client = TestClient(app)
    denied = client.post("/v1/dashboard/portfolio", json={})
    assert denied.status_code == 401
    ok = client.post(
        "/v1/dashboard/portfolio",
        json={},
        headers={"Authorization": "Bearer secret"},
    )
    assert ok.status_code == 200
