"""x402 V2 HTTP transport (preview + paid fetch) via 1Claw wallet."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

import requests
from x402 import prefer_network, x402ClientSync
from x402.http import x402HTTPClientSync
from x402.http.clients import wrapRequestsWithPayment
from x402.mechanisms.evm.batch_settlement.client import (
    BatchSettlementEvmScheme,
    BatchSettlementEvmSchemeOptions,
)
from x402.mechanisms.evm.exact.client import ExactEvmScheme
from x402.mechanisms.evm.upto import UptoEvmScheme
from x402.schemas import PaymentRequired
from x402.schemas.v1 import PaymentRequiredV1

from aurey.graphs.api_key_resolution import effective_alchemy_api_key
from aurey.graphs.chains import alchemy_rpc_url_for_chain
from aurey.runtime import AureyRuntime
from aurey.x402.batch_storage import make_batch_channel_storage
from aurey.x402.errors import tool_error
from aurey.x402.oneclaw_signer import OneClawEvmX402Signer, _network_to_chain_slug
from aurey.x402.policy import (
    PolicyDecision,
    build_quote,
    evaluate_fetch,
    host_allowed,
    quote_to_result_dict,
    select_requirement,
)

_HTTP_TIMEOUT_S = 60.0
_V2_HEADER_PARSE_MSG = "Could not parse V2 PAYMENT-REQUIRED header."
_NO_PAYMENT_REQ_MSG = "402 response had no acceptable payment requirements."


@dataclass
class _ProbeResult:
    status_code: int
    headers: dict[str, str]
    body_text: str
    payment_required: PaymentRequired | PaymentRequiredV1 | None


class AureyX402Transport:
    """Builds a V2-only x402 client and exposes preview/fetch helpers."""

    def __init__(self, runtime: AureyRuntime) -> None:
        self._runtime = runtime
        self._batch_scheme: BatchSettlementEvmScheme | None = None
        self._http_helper: x402HTTPClientSync | None = None
        self._paid_session: requests.Session | None = None
        self._build()

    def _prefer_network(self) -> str:
        return (self._runtime.settings.x402_prefer_network or "eip155:8453").strip()

    def _rpc_url(self) -> str | None:
        key, _err = effective_alchemy_api_key(self._runtime.settings, self._runtime.secret_store)
        if not key:
            return None
        slug = _network_to_chain_slug(self._prefer_network())
        return alchemy_rpc_url_for_chain(slug, key)

    def _build(self) -> None:
        signer_backend = self._runtime.oneclaw_evm_signer
        if signer_backend is None:
            raise RuntimeError("1Claw EVM signer is not configured.")
        prefer = self._prefer_network()
        try:
            chain_slug = _network_to_chain_slug(prefer)
        except ValueError:
            chain_slug = "base"
        oc_signer = OneClawEvmX402Signer(
            self._runtime,
            signer=signer_backend,
            chain_slug=chain_slug,
            rpc_url=self._rpc_url(),
        )
        client = x402ClientSync()
        client.register("eip155:*", ExactEvmScheme(oc_signer))
        client.register("eip155:*", UptoEvmScheme(oc_signer))
        batch_storage = make_batch_channel_storage(self._runtime.settings)
        batch_opts = BatchSettlementEvmSchemeOptions(
            storage=batch_storage,
            rpc_url=self._rpc_url(),
        )
        batch_scheme = BatchSettlementEvmScheme(oc_signer, batch_opts)
        client.register("eip155:*", batch_scheme)
        client.register_policy(prefer_network(prefer))
        self._batch_scheme = batch_scheme
        self._http_helper = x402HTTPClientSync(client)
        session = requests.Session()
        wrapRequestsWithPayment(session, client)
        self._paid_session = session

    @property
    def batch_scheme(self) -> BatchSettlementEvmScheme:
        if self._batch_scheme is None:
            raise RuntimeError("x402 batch scheme not initialized.")
        return self._batch_scheme

    def _probe(
        self,
        *,
        method: str,
        url: str,
        headers: dict[str, str] | None,
        json_body: dict[str, Any] | list[Any] | None,
    ) -> _ProbeResult:
        hdrs = dict(headers or {})
        hdrs.setdefault("Accept", "application/json")
        meth = method.upper()
        kwargs: dict[str, Any] = {"timeout": _HTTP_TIMEOUT_S, "headers": hdrs}
        if json_body is not None:
            kwargs["json"] = json_body
        resp = requests.request(meth, url, **kwargs)
        body_text = resp.text or ""
        payment_required: PaymentRequired | PaymentRequiredV1 | None = None
        if resp.status_code == 402 and self._http_helper is not None:

            def get_header(name: str) -> str | None:
                return resp.headers.get(name)

            try:
                body: Any = None
                if body_text:
                    try:
                        body = json.loads(body_text)
                    except json.JSONDecodeError:
                        body = None
                payment_required = self._http_helper.get_payment_required_response(get_header, body)
            except ValueError:
                payment_required = None
        header_map = {k: v for k, v in resp.headers.items()}
        return _ProbeResult(
            status_code=resp.status_code,
            headers=header_map,
            body_text=body_text,
            payment_required=payment_required,
        )

    def _parse_success_body(self, body_text: str) -> Any:
        if not body_text:
            return {}
        try:
            return json.loads(body_text)
        except json.JSONDecodeError:
            return {"text": body_text[:8000]}

    def preview(
        self,
        *,
        url: str,
        method: str = "GET",
        headers: dict[str, str] | None = None,
        json_body: dict[str, Any] | list[Any] | None = None,
    ) -> dict[str, Any]:
        if not host_allowed(self._runtime.settings, url):
            host = urlparse(url).hostname
            return tool_error("host_not_allowed", f"Host not allowed for x402: {host}")
        probe = self._probe(method=method, url=url, headers=headers, json_body=json_body)
        if probe.status_code != 402:
            return {
                "ok": True,
                "result": {
                    "payment_required": False,
                    "status_code": probe.status_code,
                    "body": self._parse_success_body(probe.body_text),
                },
            }
        if probe.payment_required is None:
            return tool_error("x402_v1_not_supported", _V2_HEADER_PARSE_MSG)
        if isinstance(probe.payment_required, PaymentRequiredV1):
            return tool_error("x402_v1_not_supported", "V1-only x402 resources are not supported.")
        req = select_requirement(
            probe.payment_required,
            prefer_network=self._prefer_network(),
        )
        if req is None:
            return tool_error("x402_payment_failed", _NO_PAYMENT_REQ_MSG)
        quote = build_quote(req, self._runtime.settings)
        return {
            "ok": True,
            "result": {
                "payment_required": True,
                "status_code": 402,
                "quote": quote_to_result_dict(quote),
            },
        }

    def fetch(
        self,
        *,
        url: str,
        method: str = "GET",
        headers: dict[str, str] | None = None,
        json_body: dict[str, Any] | list[Any] | None = None,
        confirm_payment: bool = False,
        max_price_usd: float | None = None,
        bound_max_usd: float | None = None,
    ) -> dict[str, Any]:
        if not host_allowed(self._runtime.settings, url):
            host = urlparse(url).hostname
            return tool_error("host_not_allowed", f"Host not allowed for x402: {host}")

        probe = self._probe(method=method, url=url, headers=headers, json_body=json_body)
        if probe.status_code != 402:
            return {
                "ok": True,
                "result": {
                    "payment_required": False,
                    "status_code": probe.status_code,
                    "body": self._parse_success_body(probe.body_text),
                },
            }

        if probe.payment_required is None:
            return tool_error("x402_v1_not_supported", _V2_HEADER_PARSE_MSG)
        if isinstance(probe.payment_required, PaymentRequiredV1):
            return tool_error("x402_v1_not_supported", "V1-only x402 resources are not supported.")

        req = select_requirement(probe.payment_required, prefer_network=self._prefer_network())
        if req is None:
            return tool_error("x402_payment_failed", _NO_PAYMENT_REQ_MSG)
        quote = build_quote(req, self._runtime.settings)
        decision = evaluate_fetch(
            quote,
            self._runtime.settings,
            confirm_payment=confirm_payment,
            max_price_usd=max_price_usd,
            bound_max_usd=bound_max_usd,
        )
        blocked = self._policy_block(decision)
        if blocked is not None:
            return blocked

        session = self._paid_session
        helper = self._http_helper
        if session is None or helper is None:
            return tool_error("internal_error", "x402 paid session is not initialized.")

        hdrs = dict(headers or {})
        hdrs.setdefault("Accept", "application/json")
        meth = method.upper()
        kwargs: dict[str, Any] = {"timeout": _HTTP_TIMEOUT_S, "headers": hdrs}
        if json_body is not None:
            kwargs["json"] = json_body
        paid_resp = session.request(meth, url, **kwargs)
        body_text = paid_resp.text or ""

        payment_meta: dict[str, Any] = {"status_code": paid_resp.status_code}
        if paid_resp.status_code == 402:
            return tool_error(
                "x402_payment_failed",
                "Payment was required but could not be completed.",
                status_code=402,
                body_preview=body_text[:500],
            )

        try:

            def get_header(name: str) -> str | None:
                return paid_resp.headers.get(name)

            settle = helper.get_payment_settle_response(get_header)
            payment_meta["payment_status"] = "settled"
            payment_meta["settlement"] = settle.model_dump(mode="json")
        except ValueError:
            payment_meta["payment_status"] = "none"

        if paid_resp.status_code >= 400:
            return tool_error(
                "http_error",
                f"Upstream HTTP {paid_resp.status_code}.",
                status_code=paid_resp.status_code,
                body_preview=body_text[:500],
            )

        return {
            "ok": True,
            "result": {
                "payment_required": True,
                "status_code": paid_resp.status_code,
                "body": self._parse_success_body(body_text),
                "payment": payment_meta,
                "quote": quote_to_result_dict(quote),
            },
        }

    @staticmethod
    def _policy_block(decision: PolicyDecision) -> dict[str, Any] | None:
        if decision.allowed:
            return None
        code = decision.code or "x402_payment_failed"
        message = decision.message or "Payment blocked by policy."
        extra: dict[str, Any] = {}
        if decision.quote is not None:
            extra["quote"] = quote_to_result_dict(decision.quote)
        if code == "needs_confirmation":
            extra["status"] = "needs_confirmation"
        return tool_error(code, message, **extra)


def transport_for(runtime: AureyRuntime) -> AureyX402Transport:
    return AureyX402Transport(runtime)


__all__ = ["AureyX402Transport", "transport_for"]
