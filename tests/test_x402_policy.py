from __future__ import annotations

from aurey.settings import AureySettings
from aurey.x402.policy import (
    QuoteView,
    build_quote,
    evaluate_fetch,
    host_allowed,
    select_requirement,
)
from x402.schemas import PaymentRequired, PaymentRequirements


def test_host_allowlist() -> None:
    s = AureySettings(x402_allowed_hosts="api.example.com, stable.io")
    assert host_allowed(s, "https://api.example.com/path")
    assert not host_allowed(s, "https://evil.example.com/")


def test_evaluate_auto_approve_and_confirm() -> None:
    s = AureySettings(x402_auto_approve_max_usd=0.25, x402_max_price_usd=5.0)
    quote = QuoteView(
        scheme="exact",
        network="eip155:8453",
        pay_to="0x0000000000000000000000000000000000000001",
        asset="0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
        amount_atomic="100000",
        amount_usd=0.1,
        is_usdc=True,
        extras={},
    )
    ok = evaluate_fetch(quote, s, confirm_payment=False, max_price_usd=None, bound_max_usd=None)
    assert ok.allowed

    high = QuoteView(
        scheme="exact",
        network="eip155:8453",
        pay_to="0x1",
        asset="0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
        amount_atomic="500000",
        amount_usd=0.5,
        is_usdc=True,
        extras={},
    )
    need = evaluate_fetch(high, s, confirm_payment=False, max_price_usd=None, bound_max_usd=None)
    assert not need.allowed
    assert need.code == "needs_confirmation"

    confirmed = evaluate_fetch(high, s, confirm_payment=True, max_price_usd=0.5, bound_max_usd=0.5)
    assert confirmed.allowed

    changed = evaluate_fetch(high, s, confirm_payment=True, max_price_usd=0.5, bound_max_usd=0.25)
    assert not changed.allowed
    assert changed.code == "price_changed"


def test_unsupported_asset() -> None:
    s = AureySettings()
    quote = QuoteView(
        scheme="exact",
        network="eip155:8453",
        pay_to="0x1",
        asset="0xdead",
        amount_atomic="1",
        amount_usd=0.0,
        is_usdc=False,
        extras={},
    )
    out = evaluate_fetch(quote, s, confirm_payment=False, max_price_usd=None, bound_max_usd=None)
    assert out.code == "unsupported_asset"


def test_select_require_preferred_network() -> None:
    pr = PaymentRequired(
        accepts=[
            PaymentRequirements(
                scheme="exact",
                network="eip155:1",
                asset="0xa",
                amount="1",
                pay_to="0xb",
                maxTimeoutSeconds=60,
            ),
            PaymentRequirements(
                scheme="exact",
                network="eip155:8453",
                asset="0xc",
                amount="2",
                pay_to="0xd",
                maxTimeoutSeconds=60,
            ),
        ]
    )
    req = select_requirement(pr, prefer_network="eip155:8453")
    assert req is not None
    assert req.network == "eip155:8453"


def test_build_quote_batch_deposit() -> None:
    s = AureySettings()
    req = PaymentRequirements(
        scheme="batch-settlement",
        network="eip155:8453",
        asset="0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
        amount="10000",
        pay_to="0x1",
        maxTimeoutSeconds=60,
        extra={},
    )
    quote = build_quote(req, s)
    assert quote.estimated_deposit_atomic is not None
