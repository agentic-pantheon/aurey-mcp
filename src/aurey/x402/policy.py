"""x402 spend policy: caps, host allowlist, USDC quotes, confirm gate."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

from x402.mechanisms.evm.batch_settlement.client.config import deposit_amount_for_request
from x402.schemas import PaymentRequired, PaymentRequirements
from x402.schemas.v1 import PaymentRequiredV1

from aurey.graphs.chains import chain_name_for_id
from aurey.graphs.evm_codec import normalize_evm_address
from aurey.known_addresses.book import lookup_known_token
from aurey.settings import AureySettings


USDC_DECIMALS = 6


@dataclass(frozen=True)
class QuoteView:
    scheme: str
    network: str
    pay_to: str
    asset: str
    amount_atomic: str
    amount_usd: float
    is_usdc: bool
    extras: dict[str, Any]
    estimated_deposit_atomic: str | None = None
    estimated_deposit_usd: float | None = None


@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    code: str | None = None
    message: str | None = None
    quote: QuoteView | None = None


def _chain_slug_from_network(network: str) -> str | None:
    net = (network or "").strip()
    if not net.startswith("eip155:"):
        return None
    try:
        cid = int(net.split(":", 1)[1])
    except (IndexError, ValueError):
        return None
    return chain_name_for_id(cid)


def is_known_usdc_on_network(asset: str, network: str) -> bool:
    slug = _chain_slug_from_network(network)
    if slug is None:
        return False
    usdc = lookup_known_token(slug, "USDC")
    if usdc is None:
        return False
    try:
        return normalize_evm_address(asset) == normalize_evm_address(usdc.address)
    except ValueError:
        return False


def atomic_usdc_to_usd(amount_atomic: str) -> float:
    return int(amount_atomic) / (10**USDC_DECIMALS)


def host_allowed(settings: AureySettings, url: str) -> bool:
    raw = (settings.x402_allowed_hosts or "").strip()
    if not raw:
        return True
    host = (urlparse(url).hostname or "").lower()
    if not host:
        return False
    allowed = {h.strip().lower() for h in raw.split(",") if h.strip()}
    return host in allowed


def select_requirement(
    payment_required: PaymentRequired | PaymentRequiredV1,
    *,
    prefer_network: str,
) -> PaymentRequirements | None:
    if isinstance(payment_required, PaymentRequiredV1):
        return None
    accepts = list(payment_required.accepts or [])
    if not accepts:
        return None
    pref = prefer_network.strip()
    for req in accepts:
        if req.network == pref:
            return req
    for req in accepts:
        if str(req.network).startswith("eip155:"):
            return req
    first = accepts[0]
    return first if isinstance(first, PaymentRequirements) else None


def build_quote(req: PaymentRequirements, settings: AureySettings) -> QuoteView:
    amount = str(req.amount)
    is_usdc = is_known_usdc_on_network(str(req.asset), str(req.network))
    amount_usd = atomic_usdc_to_usd(amount) if is_usdc else 0.0
    deposit_atomic: str | None = None
    deposit_usd: float | None = None
    if req.scheme == "batch-settlement":
        deposit_atomic = deposit_amount_for_request(None, int(amount))
        if is_usdc:
            deposit_usd = atomic_usdc_to_usd(deposit_atomic)
    extra = dict(req.extra or {})
    return QuoteView(
        scheme=str(req.scheme),
        network=str(req.network),
        pay_to=str(req.pay_to),
        asset=str(req.asset),
        amount_atomic=amount,
        amount_usd=amount_usd,
        is_usdc=is_usdc,
        extras=extra,
        estimated_deposit_atomic=deposit_atomic,
        estimated_deposit_usd=deposit_usd,
    )


def quote_to_result_dict(quote: QuoteView) -> dict[str, Any]:
    out: dict[str, Any] = {
        "scheme": quote.scheme,
        "network": quote.network,
        "pay_to": quote.pay_to,
        "asset": quote.asset,
        "amount_atomic": quote.amount_atomic,
        "quoted_max_usd": quote.amount_usd if quote.is_usdc else None,
        "extras": quote.extras,
    }
    if quote.scheme == "upto":
        out["note"] = "You authorize up to this maximum; the charged amount may be lower."
    if quote.estimated_deposit_atomic is not None:
        out["estimated_deposit_atomic"] = quote.estimated_deposit_atomic
        out["estimated_deposit_usd"] = quote.estimated_deposit_usd
        out["note"] = (
            "Batch-settlement may lock USDC in a channel; later calls can reuse balance (vouchers only)."
        )
    return out


def _cap_compare_usd(
    exposure_usd: float,
    *,
    settings: AureySettings,
    per_call_max: float | None,
) -> PolicyDecision | None:
    hard = float(settings.x402_max_price_usd)
    if exposure_usd > hard:
        return PolicyDecision(
            allowed=False,
            code="price_too_high",
            message=f"Quoted exposure ${exposure_usd:.4f} exceeds hard cap ${hard:.4f}.",
        )
    if per_call_max is not None and exposure_usd > per_call_max:
        return PolicyDecision(
            allowed=False,
            code="price_too_high",
            message=f"Quoted exposure ${exposure_usd:.4f} exceeds per-call max ${per_call_max:.4f}.",
        )
    return None


def evaluate_fetch(
    quote: QuoteView,
    settings: AureySettings,
    *,
    confirm_payment: bool,
    max_price_usd: float | None,
    bound_max_usd: float | None,
) -> PolicyDecision:
    if not quote.is_usdc:
        return PolicyDecision(
            allowed=False,
            code="unsupported_asset",
            message="Only known USDC on this chain is supported for automatic payment in v1.",
            quote=quote,
        )

    voucher_usd = quote.amount_usd
    deposit_usd = quote.estimated_deposit_usd or 0.0
    exposure = max(voucher_usd, deposit_usd) if quote.scheme == "batch-settlement" else voucher_usd

    if quote.scheme == "batch-settlement" and deposit_usd > 0:
        batch_cap = float(settings.x402_batch_max_deposit_usd)
        if deposit_usd > batch_cap:
            return PolicyDecision(
                allowed=False,
                code="price_too_high",
                message=f"Estimated deposit ${deposit_usd:.4f} exceeds batch deposit cap ${batch_cap:.4f}.",
                quote=quote,
            )

    cap_err = _cap_compare_usd(exposure, settings=settings, per_call_max=max_price_usd)
    if cap_err is not None:
        cap_err = PolicyDecision(
            allowed=cap_err.allowed,
            code=cap_err.code,
            message=cap_err.message,
            quote=quote,
        )
        return cap_err

    auto_cap = float(settings.x402_auto_approve_max_usd)
    if confirm_payment:
        if bound_max_usd is not None and exposure > bound_max_usd + 1e-9:
            return PolicyDecision(
                allowed=False,
                code="price_changed",
                message=(
                    f"Quote exposure ${exposure:.4f} exceeds bound max_price_usd ${bound_max_usd:.4f}."
                ),
                quote=quote,
            )
        return PolicyDecision(allowed=True, quote=quote)

    if exposure <= auto_cap:
        return PolicyDecision(allowed=True, quote=quote)

    return PolicyDecision(
        allowed=False,
        code="needs_confirmation",
        message=(
            f"Exposure ${exposure:.4f} exceeds auto-approve ${auto_cap:.4f}. "
            "Re-call x402_fetch with confirm_payment=true and max_price_usd set to the quoted amount."
        ),
        quote=quote,
    )


__all__ = [
    "PolicyDecision",
    "QuoteView",
    "build_quote",
    "evaluate_fetch",
    "host_allowed",
    "quote_to_result_dict",
    "select_requirement",
]
