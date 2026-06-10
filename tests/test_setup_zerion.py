"""Tests for Zerion-related aurey-setup CLI and host install wiring."""

from __future__ import annotations

from pathlib import Path

import pytest

from aurey_wallet_mcp.mcp_hosts import run_host_install
from aurey_wallet_mcp.setup import _pick_zerion, build_parser


def test_pick_zerion_skip() -> None:
    assert _pick_zerion(None, prompt=True, skip=True) is None


def test_pick_zerion_cli_value() -> None:
    assert _pick_zerion("zerion-plain", prompt=True, skip=False) == "zerion-plain"


def test_parser_zerion_flags() -> None:
    parser = build_parser()
    args = parser.parse_args(
        [
            "--host",
            "cursor",
            "--zerion-key",
            "key-from-cli",
            "--zerion-vault-path",
            "custom/zerion",
        ]
    )
    assert args.zerion_key == "key-from-cli"
    assert args.zerion_vault_path == "custom/zerion"
    skip_args = parser.parse_args(["--skip-zerion"])
    assert skip_args.skip_zerion is True


def test_run_host_install_writes_zerion_path(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setattr(Path, "home", lambda: home)

    binary = tmp_path / "aurey-wallet-mcp"
    binary.write_text("#!/bin/sh\n", encoding="utf-8")
    env_file = home / ".aurey" / "mcp.env"
    wrapper = home / ".aurey" / "run-aurey-wallet-mcp.sh"

    monkeypatch.setattr("aurey_wallet_mcp.mcp_hosts.maybe_dev_sync", lambda *a, **k: None)
    monkeypatch.setattr("aurey_wallet_mcp.mcp_hosts.resolve_mcp_command", lambda repo=None: binary)
    monkeypatch.setattr(
        "aurey_wallet_mcp.mcp_hosts.write_mcp_env",
        lambda secrets, path=None: env_file,
    )
    monkeypatch.setattr(
        "aurey_wallet_mcp.mcp_hosts.write_mcp_wrapper",
        lambda binary, env_path: wrapper,
    )

    project = tmp_path / "proj"
    project.mkdir()

    run_host_install(
        "cursor",
        skip_sync=True,
        secrets={
            "AUREY_ONECLAW_VAULT_ID": "vault-1",
            "AUREY_ONECLAW_AGENT_ID": "agent-1",
            "AUREY_ONECLAW_VAULT_API_KEY": "ocv_test",
        },
        zerion_vault_path="api-keys/zerion-custom",
        skip_portfolio_ui=True,
        skip_smoke_test=True,
        cursor_project=str(project),
    )

    config = (home / ".aurey" / "config.toml").read_text(encoding="utf-8")
    assert 'zerion_api_secret_path = "api-keys/zerion-custom"' in config
