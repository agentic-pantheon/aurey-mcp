from __future__ import annotations

from pathlib import Path

import pytest

from aurey.settings import AureySettings
from aurey.x402.catalog import (
    get_service,
    list_services,
    reload_x402_catalog_for_tests,
    resolve_endpoint,
)


@pytest.fixture(autouse=True)
def _catalog_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUREY_X402_SERVICES_URL", "")
    reload_x402_catalog_for_tests()


@pytest.fixture
def catalog_settings() -> AureySettings:
    return AureySettings()


def test_bundled_catalog_has_twelve_services(catalog_settings: AureySettings) -> None:
    rows, doc, source = list_services(catalog_settings)
    assert source == "bundled"
    assert len(rows) == 12
    assert doc.version


def test_list_filter_tag(catalog_settings: AureySettings) -> None:
    rows, _, _ = list_services(catalog_settings, tag="storage")
    ids = {s.id for s in rows}
    assert "pinata-x402" in ids


def test_get_service_by_id(catalog_settings: AureySettings) -> None:
    svc, _, _ = get_service(catalog_settings, "stableenrich")
    assert svc is not None
    assert svc.name == "StableEnrich"
    assert len(svc.endpoints) >= 8


def test_resolve_endpoint(catalog_settings: AureySettings) -> None:
    ep, svc, source = resolve_endpoint(catalog_settings, "stableenrich", "exa-search")
    assert svc is not None and ep is not None
    assert source == "bundled"
    assert ep.url.endswith("/api/exa/search")
    assert ep.method == "POST"


def test_local_override_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "x402_services.json"
    path.write_text(
        '{"version":"test","services":[{"id":"demo","provider_id":"x","name":"Demo",'
        '"endpoints":[{"id":"e1","method":"GET","url":"https://example.com/x"}]}]}',
        encoding="utf-8",
    )
    monkeypatch.setenv("AUREY_X402_SERVICES_PATH", str(path))
    reload_x402_catalog_for_tests()
    rows, _, source = list_services(AureySettings())
    assert source == "local"
    assert len(rows) == 1
    assert rows[0].id == "demo"
