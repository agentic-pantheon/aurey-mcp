"""Curated x402 service catalog (bundled, local override, optional remote refresh)."""

from __future__ import annotations

import json
import logging
import time
from importlib.resources import files
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlparse

import requests
from pydantic import BaseModel, Field, ValidationError

from aurey.settings import AureySettings

_log = logging.getLogger(__name__)

CatalogSource = Literal["local", "remote", "cache", "bundled"]
_REMOTE_FETCH_TIMEOUT_S = 5.0

_memo: dict[str, Any] = {
    "doc": None,
    "source": None,
    "loaded_at": 0.0,
}


class X402Endpoint(BaseModel):
    id: str
    method: str
    url: str
    description: str = ""
    price_usd_min: float | None = None
    price_note: str | None = None


class X402ServiceEntry(BaseModel):
    id: str
    provider_id: str
    name: str
    description: str = ""
    tags: list[str] = Field(default_factory=list)
    network: str = "eip155:8453"
    discover_url: str = ""
    base_url: str = ""
    agent_notes: str | None = None
    endpoints: list[X402Endpoint] = Field(default_factory=list)


class X402ServicesDocument(BaseModel):
    version: str
    services: list[X402ServiceEntry]


def reload_x402_catalog_for_tests() -> None:
    """Clear in-process catalog memo (tests only)."""

    _memo["doc"] = None
    _memo["source"] = None
    _memo["loaded_at"] = 0.0


def _default_cache_path(settings: AureySettings) -> Path:
    raw = (settings.x402_services_cache_path or "").strip()
    if raw:
        return Path(raw).expanduser()
    return Path.home() / ".aurey" / "cache" / "x402_services.json"


def _read_bundled_json() -> dict[str, Any]:
    raw = files("aurey.data").joinpath("x402_services.json").read_text(encoding="utf-8")
    return json.loads(raw)


def _parse_document(data: dict[str, Any]) -> X402ServicesDocument:
    return X402ServicesDocument.model_validate(data)


def _load_json_file(path: Path) -> X402ServicesDocument:
    return _parse_document(json.loads(path.read_text(encoding="utf-8")))


def _fetch_remote(url: str) -> X402ServicesDocument | None:
    try:
        resp = requests.get(url, timeout=_REMOTE_FETCH_TIMEOUT_S)
        resp.raise_for_status()
        doc = _parse_document(resp.json())
    except (requests.RequestException, json.JSONDecodeError, ValidationError) as exc:
        _log.warning("x402 catalog remote fetch failed: %s", exc)
        return None
    return doc


def _try_stale_cache(cache_path: Path) -> X402ServicesDocument | None:
    if not cache_path.is_file():
        return None
    try:
        return _load_json_file(cache_path)
    except (OSError, json.JSONDecodeError, ValidationError):
        return None


def _resolve_catalog(settings: AureySettings) -> tuple[X402ServicesDocument, CatalogSource]:
    override = (settings.x402_services_path or "").strip()
    if override:
        path = Path(override).expanduser()
        return _load_json_file(path), "local"

    cache_path = _default_cache_path(settings)
    remote_url = settings.effective_x402_services_url()
    ttl = float(settings.x402_services_ttl_seconds)
    now = time.monotonic()
    cached_doc = _memo.get("doc")
    cached_source = _memo.get("source")
    loaded_at = float(_memo.get("loaded_at") or 0.0)
    if cached_doc is not None and cached_source is not None and (now - loaded_at) < ttl:
        return cached_doc, cached_source

    if remote_url:
        fresh = _fetch_remote(remote_url)
        if fresh is not None:
            try:
                cache_path.parent.mkdir(parents=True, exist_ok=True)
                cache_path.write_text(
                    fresh.model_dump_json(indent=2),
                    encoding="utf-8",
                )
            except OSError as exc:
                _log.warning("x402 catalog cache write failed: %s", exc)
            return fresh, "remote"
        stale = _try_stale_cache(cache_path)
        if stale is not None:
            return stale, "cache"

    try:
        bundled = _parse_document(_read_bundled_json())
        return bundled, "bundled"
    except (FileNotFoundError, json.JSONDecodeError, ValidationError) as exc:
        stale = _try_stale_cache(cache_path)
        if stale is not None:
            return stale, "cache"
        raise RuntimeError("x402 services catalog unavailable") from exc


def get_catalog(settings: AureySettings) -> tuple[X402ServicesDocument, CatalogSource]:
    doc, source = _resolve_catalog(settings)
    _memo["doc"] = doc
    _memo["source"] = source
    _memo["loaded_at"] = time.monotonic()
    return doc, source


def _service_hosts(service: X402ServiceEntry) -> set[str]:
    hosts: set[str] = set()
    base = (service.base_url or "").strip()
    if base:
        h = urlparse(base).hostname
        if h:
            hosts.add(h.lower())
    for ep in service.endpoints:
        h = urlparse(ep.url).hostname
        if h:
            hosts.add(h.lower())
    return hosts


def _matches_query(service: X402ServiceEntry, query: str) -> bool:
    q = query.strip().lower()
    if not q:
        return True
    hay = " ".join(
        [
            service.id,
            service.provider_id,
            service.name,
            service.description,
            " ".join(service.tags),
            service.base_url,
        ]
    ).lower()
    return q in hay or any(q in t.lower() for t in service.tags)


def list_services(
    settings: AureySettings,
    *,
    query: str | None = None,
    tag: str | None = None,
) -> tuple[list[X402ServiceEntry], X402ServicesDocument, CatalogSource]:
    doc, source = get_catalog(settings)
    rows: list[X402ServiceEntry] = []
    tag_needle = (tag or "").strip().lower()
    for svc in doc.services:
        if tag_needle and not any(t.lower() == tag_needle for t in svc.tags):
            continue
        if query and not _matches_query(svc, query):
            continue
        rows.append(svc)
    return rows, doc, source


def get_service(
    settings: AureySettings,
    service_id: str,
) -> tuple[X402ServiceEntry | None, X402ServicesDocument, CatalogSource]:
    doc, source = get_catalog(settings)
    needle = service_id.strip().lower()
    for svc in doc.services:
        if svc.id.lower() == needle:
            return svc, doc, source
        if svc.provider_id.lower() == needle:
            return svc, doc, source
        if svc.provider_id.lower().startswith(needle) and len(needle) >= 8:
            return svc, doc, source
        for host in _service_hosts(svc):
            if host == needle or host.startswith(needle):
                return svc, doc, source
    return None, doc, source


def resolve_endpoint(
    settings: AureySettings,
    service_id: str,
    endpoint_id: str,
) -> tuple[X402Endpoint | None, X402ServiceEntry | None, CatalogSource]:
    svc, _, source = get_service(settings, service_id)
    if svc is None:
        return None, None, source
    eid = endpoint_id.strip().lower()
    for ep in svc.endpoints:
        if ep.id.lower() == eid:
            return ep, svc, source
        if ep.url.lower().endswith(eid) or eid in ep.url.lower():
            return ep, svc, source
    return None, svc, source


def service_min_price_usd(service: X402ServiceEntry) -> float | None:
    prices = [p for p in (ep.price_usd_min for ep in service.endpoints) if p is not None]
    return min(prices) if prices else None


def service_to_list_row(service: X402ServiceEntry) -> dict[str, Any]:
    hosts = sorted(_service_hosts(service))
    return {
        "id": service.id,
        "provider_id": service.provider_id,
        "name": service.name,
        "tags": service.tags,
        "base_url": service.base_url or None,
        "hosts": hosts,
        "endpoint_count": len(service.endpoints),
        "min_price_usd": service_min_price_usd(service),
    }


def service_to_detail(service: X402ServiceEntry) -> dict[str, Any]:
    return {
        "id": service.id,
        "provider_id": service.provider_id,
        "name": service.name,
        "description": service.description,
        "tags": service.tags,
        "network": service.network,
        "discover_url": service.discover_url,
        "base_url": service.base_url,
        "agent_notes": service.agent_notes,
        "endpoints": [ep.model_dump() for ep in service.endpoints],
    }


__all__ = [
    "CatalogSource",
    "X402Endpoint",
    "X402ServiceEntry",
    "X402ServicesDocument",
    "get_catalog",
    "get_service",
    "list_services",
    "reload_x402_catalog_for_tests",
    "resolve_endpoint",
    "service_min_price_usd",
    "service_to_detail",
    "service_to_list_row",
]
