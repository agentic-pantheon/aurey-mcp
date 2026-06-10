"""Install helpers for local portfolio UI config."""

from __future__ import annotations

from pathlib import Path

from aurey_wallet_mcp.install_common import ensure_aurey_toml_dashboard_enabled


def test_ensure_dashboard_enabled_adds_section(tmp_path: Path) -> None:
    cfg = tmp_path / "config.toml"
    ensure_aurey_toml_dashboard_enabled(cfg, enabled=True)
    text = cfg.read_text(encoding="utf-8")
    assert "[dashboard]" in text
    assert "enabled = true" in text


def test_ensure_dashboard_enabled_idempotent(tmp_path: Path) -> None:
    cfg = tmp_path / "config.toml"
    cfg.write_text("[dashboard]\nenabled = true\n", encoding="utf-8")
    ensure_aurey_toml_dashboard_enabled(cfg, enabled=True)
    assert cfg.read_text(encoding="utf-8").count("enabled") == 1


def test_ensure_dashboard_respects_existing_false(tmp_path: Path) -> None:
    cfg = tmp_path / "config.toml"
    cfg.write_text("[dashboard]\nenabled = false\n", encoding="utf-8")
    ensure_aurey_toml_dashboard_enabled(cfg, enabled=True)
    assert "enabled = false" in cfg.read_text(encoding="utf-8")
