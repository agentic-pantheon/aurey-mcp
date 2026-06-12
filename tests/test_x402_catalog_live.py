from __future__ import annotations

import os

import pytest
import requests

from aurey.settings import AureySettings
from aurey.x402.catalog import get_service, list_services, reload_x402_catalog_for_tests

pytestmark = pytest.mark.integration

# One cheap probe per curated service (no payment).
LIVE_PROBES: list[tuple[str, str, str]] = [
    ("blackswan", "POST", "https://x402.blackswan.wtf/smart-agents/flare"),
    ("einstein-ai", "POST", "https://emc2ai.io/x402/einstein/report"),
    ("limitless-exchange", "POST", "https://server-production-d471.up.railway.app/place-bet"),
    ("zapper", "POST", "https://public.zapper.xyz/x402/token-price"),
    ("stableenrich", "POST", "https://stableenrich.dev/api/exa/search"),
    ("auor-io", "GET", "https://api.auor.io/all-rates-today/v1/rates"),
    ("twit-sh", "GET", "https://x402.twit.sh/tweets/by/id"),
    ("laso-finance", "GET", "https://laso.finance/auth"),
    ("asterpay", "GET", "https://x402.asterpay.io/v2/x402/crypto/prices"),
    ("grove-api", "POST", "https://api.grove.city/v1/fund"),
    ("pinata-x402", "POST", "https://402.pinata.cloud/v1/pin/public"),
    (
        "cybercentry",
        "POST",
        "https://x402-cybercentry-cyber-security-consultant.up.railway.app/query",
    ),
]


def _live_enabled() -> bool:
    return os.environ.get("AUREY_RUN_LIVE_X402") == "1"


@pytest.fixture(autouse=True)
def _skip_unless_live() -> None:
    if not _live_enabled():
        pytest.skip("Set AUREY_RUN_LIVE_X402=1 to run live x402 catalog probes")


@pytest.fixture(autouse=True)
def _catalog_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUREY_X402_SERVICES_URL", "")
    reload_x402_catalog_for_tests()


def test_catalog_probe_urls_match_services() -> None:
    settings = AureySettings()
    for service_id, _method, url in LIVE_PROBES:
        svc, _, _ = get_service(settings, service_id)
        assert svc is not None
        assert any(ep.url.split("{")[0] in url or ep.url == url for ep in svc.endpoints)


@pytest.mark.parametrize("service_id,method,url", LIVE_PROBES)
def test_live_endpoint_returns_402_or_reachable(service_id: str, method: str, url: str) -> None:
    kwargs: dict = {"timeout": 20, "headers": {"Accept": "application/json"}}
    if method == "POST":
        kwargs["json"] = {}
    resp = requests.request(method, url, **kwargs)
    if resp.status_code >= 500:
        pytest.skip(f"{service_id} upstream {resp.status_code}")
    assert resp.status_code in (402, 401, 403, 405, 400), (
        f"{service_id} expected payment gate or validation error, got {resp.status_code}"
    )
    if resp.status_code == 402:
        header_val = None
        for key, val in resp.headers.items():
            if key.lower() == "payment-required":
                header_val = val
                break
        assert header_val or "x402" in resp.text.lower()


def test_list_services_twelve() -> None:
    rows, _, _ = list_services(AureySettings())
    assert len(rows) == 12
