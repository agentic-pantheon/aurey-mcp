"""Vault API key env resolution (preferred name + legacy bootstrap alias)."""

from __future__ import annotations

import pytest

from aurey.settings import AureySettings


def test_resolve_prefers_vault_api_key_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AUREY_ONECLAW_BOOTSTRAP_API_KEY", raising=False)
    monkeypatch.setenv("AUREY_ONECLAW_VAULT_API_KEY", "ocv_new")
    s = AureySettings()
    assert s.resolve_oneclaw_bootstrap_api_key() == "ocv_new"


def test_resolve_legacy_bootstrap_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AUREY_ONECLAW_VAULT_API_KEY", raising=False)
    monkeypatch.setenv("AUREY_ONECLAW_BOOTSTRAP_API_KEY", "ocv_legacy")
    s = AureySettings()
    assert s.resolve_oneclaw_bootstrap_api_key() == "ocv_legacy"
