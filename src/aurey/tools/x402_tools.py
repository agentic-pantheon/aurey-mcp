"""MCP tools for wallet-backed x402 V2 HTTP transport."""

from __future__ import annotations

import json
from typing import Any, Literal

from langchain_core.tools import BaseTool, tool
from pydantic import BaseModel, Field
from x402.mechanisms.evm.batch_settlement.client.storage import BatchSettlementClientContext

from aurey.custody.agent_wallet import effective_evm_wallet_address
from aurey.custody.errors import OneClawSigningError, SecretStoreUnavailableError
from aurey.graphs import build_read_graph
from aurey.graphs.read import ReadGraphInput
from aurey.known_addresses.book import lookup_known_token
from aurey.runtime import AureyRuntime
from aurey.x402.batch_storage import batch_storage_dir, list_batch_channel_files
from aurey.x402.catalog import (
    get_service,
    list_services,
    resolve_endpoint,
    service_to_detail,
    service_to_list_row,
)
from aurey.x402.client import AureyX402Transport, transport_for
from aurey.x402.errors import tool_error
from aurey.x402.policy import atomic_usdc_to_usd, host_allowed


class X402PreviewArgs(BaseModel):
    url: str = Field(description="HTTP(S) URL to probe for x402 payment requirements.")
    method: Literal["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD"] = "GET"
    json_body: dict[str, Any] | list[Any] | None = Field(
        default=None,
        description="Optional JSON body for POST/PUT/PATCH.",
    )
    headers: dict[str, str] | None = Field(default=None, description="Optional extra HTTP headers.")


class X402FetchArgs(X402PreviewArgs):
    confirm_payment: bool = Field(
        default=False,
        description="Set true after the user approves a quote above auto-approve cap.",
    )
    max_price_usd: float | None = Field(
        default=None,
        description=(
            "Per-call USD ceiling (≤ settings hard cap). When confirm_payment=true, "
            "bind to the quoted amount to detect price_changed."
        ),
    )


class X402BatchRefundArgs(BaseModel):
    url: str = Field(
        description=(
            "Resource URL for the batch-settlement channel to refund "
            "(same host as paid calls)."
        )
    )


class X402BatchChannelStatusArgs(BaseModel):
    channel_id: str | None = Field(
        default=None,
        description="Optional channel id (filename stem under batch storage). Omit to list all.",
    )


class X402ListServicesArgs(BaseModel):
    query: str | None = Field(
        default=None,
        description="Optional substring match on name, tags, id, or base URL.",
    )
    tag: str | None = Field(
        default=None,
        description="Optional exact tag filter (case-insensitive).",
    )


class X402GetServiceArgs(BaseModel):
    service_id: str = Field(
        description="Service id, provider UUID (or prefix), or primary host name.",
    )


class X402ResolveEndpointArgs(BaseModel):
    service_id: str = Field(description="Same as get_x402_service service_id.")
    endpoint_id: str = Field(description="Endpoint id from get_x402_service (e.g. exa-search).")


def _read_graph_payload(state: dict[str, Any]) -> dict[str, Any]:
    err = state.get("error")
    res = state.get("result")
    if err is not None:
        return {"ok": False, "error": err}
    return {"ok": True, "result": res}


def _usdc_balance_base(runtime: AureyRuntime) -> dict[str, Any] | None:
    wallet = (effective_evm_wallet_address(runtime) or "").strip()
    if not wallet:
        return None
    usdc = lookup_known_token("base", "USDC")
    if usdc is None:
        return None
    read_g = build_read_graph(runtime)
    state = read_g.invoke(
        {
            "input": ReadGraphInput(
                operation="erc20_balance",
                chain="base",
                wallet_address=wallet,
                token_address=usdc.address,
            ).model_dump()
        }
    )
    out = _read_graph_payload(state)
    if not out.get("ok"):
        return {"error": out.get("error")}
    result = out.get("result") or {}
    raw = str(result.get("balance_atomic") or result.get("balance") or "0")
    try:
        atomic = int(raw)
    except ValueError:
        atomic = 0
    return {
        "chain": "base",
        "token": "USDC",
        "balance_atomic": str(atomic),
        "balance_usd": atomic_usdc_to_usd(str(atomic)),
    }


def _channel_summary(path: Any, data: dict[str, Any]) -> dict[str, Any]:
    channel_id = path.stem
    ctx = BatchSettlementClientContext.from_dict(data)
    balance_atomic = ctx.balance
    balance_usd = None
    if balance_atomic is not None:
        try:
            balance_usd = atomic_usdc_to_usd(balance_atomic)
        except ValueError:
            balance_usd = None
    host = ctx.extra.get("host") or ctx.extra.get("url")
    return {
        "channel_id": channel_id,
        "balance_atomic": balance_atomic,
        "balance_usd": balance_usd,
        "charged_cumulative_amount": ctx.charged_cumulative_amount,
        "host": host,
    }


def build_x402_tools(runtime: AureyRuntime) -> list[BaseTool]:
    if runtime.settings.evm_signing_mode != "oneclaw_intents":
        return []
    if runtime.oneclaw_evm_signer is None:
        return []

    transport_holder: dict[str, AureyX402Transport | None] = {"t": None}

    def _transport() -> AureyX402Transport:
        if transport_holder["t"] is None:
            transport_holder["t"] = transport_for(runtime)
        return transport_holder["t"]

    @tool(args_schema=X402PreviewArgs)
    def x402_preview(
        url: str,
        method: Literal["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD"] = "GET",
        json_body: dict[str, Any] | list[Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Probe an HTTP API for x402 V2 payment requirements (never signs or spends).

        Use before paid calls when cost is unknown.
        For on-chain swaps use swap_prepare, not x402."""
        try:
            return _transport().preview(
                url=url.strip(),
                method=method,
                headers=headers,
                json_body=json_body,
            )
        except (OneClawSigningError, SecretStoreUnavailableError, ValueError) as exc:
            return tool_error("oneclaw_signing_error", str(exc)[:800])

    @tool(args_schema=X402FetchArgs)
    def x402_fetch(
        url: str,
        method: Literal["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD"] = "GET",
        json_body: dict[str, Any] | list[Any] | None = None,
        headers: dict[str, str] | None = None,
        confirm_payment: bool = False,
        max_price_usd: float | None = None,
    ) -> dict[str, Any]:
        """Call an x402-gated HTTP API with automatic 402 → sign → retry when policy allows.

        Call x402_preview first when price is unknown. Above auto-approve cap, retry with
        confirm_payment=true and max_price_usd bound to the quoted amount."""
        bound = max_price_usd if confirm_payment else None
        try:
            return _transport().fetch(
                url=url.strip(),
                method=method,
                headers=headers,
                json_body=json_body,
                confirm_payment=confirm_payment,
                max_price_usd=max_price_usd,
                bound_max_usd=bound,
            )
        except (OneClawSigningError, SecretStoreUnavailableError, ValueError) as exc:
            return tool_error("oneclaw_signing_error", str(exc)[:800])

    @tool
    def x402_payment_status() -> dict[str, Any]:
        """Show agent EVM address, x402 policy caps, Base USDC balance, and batch channel count."""
        settings = runtime.settings
        wallet = (effective_evm_wallet_address(runtime) or "").strip() or None
        usdc = _usdc_balance_base(runtime)
        channels = list_batch_channel_files(settings)
        return {
            "ok": True,
            "result": {
                "evm_address": wallet,
                "caps": {
                    "max_price_usd": float(settings.x402_max_price_usd),
                    "auto_approve_max_usd": float(settings.x402_auto_approve_max_usd),
                    "batch_max_deposit_usd": float(settings.x402_batch_max_deposit_usd),
                    "prefer_network": settings.x402_prefer_network,
                    "allowed_hosts": settings.x402_allowed_hosts or None,
                },
                "usdc_base": usdc,
                "batch_channel_count": len(channels),
                "batch_storage_path": str(batch_storage_dir(settings)),
            },
        }

    @tool(args_schema=X402BatchChannelStatusArgs)
    def x402_batch_channel_status(channel_id: str | None = None) -> dict[str, Any]:
        """List or read persisted batch-settlement channels (balance, channel_id, host hints)."""
        settings = runtime.settings
        files = list_batch_channel_files(settings)
        if channel_id:
            needle = channel_id.strip().lower()
            files = [p for p in files if p.stem.lower() == needle]
        channels: list[dict[str, Any]] = []
        for path in files:
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if isinstance(data, dict):
                channels.append(_channel_summary(path, data))
        return {"ok": True, "result": {"channels": channels}}

    @tool(args_schema=X402BatchRefundArgs)
    def x402_batch_refund(url: str) -> dict[str, Any]:
        """Withdraw unused USDC from a batch-settlement channel (protocol delay may apply)."""
        try:
            settle = _transport().batch_scheme.refund(url.strip())
            return {
                "ok": True,
                "result": {
                    "settlement": settle.model_dump(mode="json"),
                    "note": "Batch refunds may take time per x402 batch-settlement rules.",
                },
            }
        except (OneClawSigningError, SecretStoreUnavailableError, ValueError) as exc:
            return tool_error("oneclaw_signing_error", str(exc)[:800])

    @tool(args_schema=X402ListServicesArgs)
    def list_x402_services(
        query: str | None = None,
        tag: str | None = None,
    ) -> dict[str, Any]:
        """List curated x402-gated APIs (compact rows).

        Use get_x402_service for full endpoint tables.
        Flow: list or get service → resolve_x402_endpoint → x402_preview → x402_fetch."""
        settings = runtime.settings
        rows, doc, source = list_services(settings, query=query, tag=tag)
        return {
            "ok": True,
            "result": {
                "catalog_version": doc.version,
                "catalog_source": source,
                "services": [service_to_list_row(s) for s in rows],
            },
        }

    @tool(args_schema=X402GetServiceArgs)
    def get_x402_service(service_id: str) -> dict[str, Any]:
        """Return one curated x402 service with all endpoints and agent_notes.

        Then resolve_x402_endpoint → x402_preview → x402_fetch."""
        settings = runtime.settings
        svc, doc, source = get_service(settings, service_id)
        if svc is None:
            return tool_error("not_found", f"No x402 service matching {service_id!r}.")
        detail = service_to_detail(svc)
        allowed_raw = (settings.x402_allowed_hosts or "").strip()
        if allowed_raw:
            hosts = detail.get("endpoints") or []
            for row in hosts:
                url = str(row.get("url") or "")
                row["host_allowed"] = host_allowed(settings, url)
        return {
            "ok": True,
            "result": {
                "catalog_version": doc.version,
                "catalog_source": source,
                "service": detail,
            },
        }

    @tool(args_schema=X402ResolveEndpointArgs)
    def resolve_x402_endpoint(service_id: str, endpoint_id: str) -> dict[str, Any]:
        """Resolve a catalog endpoint to method + URL before x402_preview / x402_fetch."""
        settings = runtime.settings
        ep, svc, source = resolve_endpoint(settings, service_id, endpoint_id)
        if svc is None:
            return tool_error("not_found", f"No x402 service matching {service_id!r}.")
        if ep is None:
            return tool_error(
                "not_found",
                f"No endpoint {endpoint_id!r} on service {svc.id!r}.",
            )
        return {
            "ok": True,
            "result": {
                "catalog_source": source,
                "service_id": svc.id,
                "endpoint_id": ep.id,
                "method": ep.method,
                "url": ep.url,
                "description": ep.description,
                "price_usd_min": ep.price_usd_min,
                "price_note": ep.price_note,
                "host_allowed": host_allowed(settings, ep.url),
            },
        }

    return [
        x402_preview,
        x402_fetch,
        x402_payment_status,
        x402_batch_channel_status,
        x402_batch_refund,
        list_x402_services,
        get_x402_service,
        resolve_x402_endpoint,
    ]


__all__ = ["build_x402_tools"]
