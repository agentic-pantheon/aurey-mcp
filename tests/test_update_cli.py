"""Tests for aurey-update CLI."""

from __future__ import annotations

from pathlib import Path

import pytest

from aurey_wallet_mcp.update_cli import package_spec, upgrade_installed_package


def test_package_spec_with_pin() -> None:
    assert package_spec(package="aurey-wallet-mcp[hermes]", pin="0.1.7") == (
        "aurey-wallet-mcp[hermes]==0.1.7"
    )


def test_package_spec_latest() -> None:
    assert package_spec(package="aurey-wallet-mcp", pin=None) == "aurey-wallet-mcp"


def test_upgrade_uv_invocation(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str]] = []

    def fake_run(cmd: list[str], *, check: bool) -> None:
        calls.append(cmd)

    monkeypatch.setattr(
        "aurey_wallet_mcp.update_cli.shutil.which",
        lambda name: "/usr/bin/uv" if name == "uv" else None,
    )
    monkeypatch.setattr("aurey_wallet_mcp.update_cli.subprocess.run", fake_run)

    upgrade_installed_package("aurey-wallet-mcp[hermes]", method="uv")
    assert calls == [["uv", "tool", "install", "--force", "aurey-wallet-mcp[hermes]"]]


def test_main_rewires_when_host_and_mcp_env(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setattr(Path, "home", lambda: home)

    aurey_dir = home / ".aurey"
    aurey_dir.mkdir()
    env_file = aurey_dir / "mcp.env"
    env_file.write_text(
        "AUREY_ONECLAW_VAULT_ID=v1\n"
        "AUREY_ONECLAW_AGENT_ID=a1\n"
        "AUREY_ONECLAW_VAULT_API_KEY=ocv_x\n",
        encoding="utf-8",
    )

    upgrade_calls: list[str] = []
    host_calls: list[str] = []

    monkeypatch.setattr(
        "aurey_wallet_mcp.update_cli.package_version",
        lambda: "0.1.7",
    )
    monkeypatch.setattr(
        "aurey_wallet_mcp.update_cli.upgrade_installed_package",
        lambda spec, method: upgrade_calls.append(spec),
    )
    monkeypatch.setattr(
        "aurey_wallet_mcp.update_cli.run_host_install",
        lambda host, **kwargs: host_calls.append(host),
    )

    from aurey_wallet_mcp.update_cli import main

    main(["--host", "cursor", "--method", "pip", "--skip-smoke-test"])

    assert upgrade_calls == ["aurey-wallet-mcp[hermes]"]
    assert host_calls == ["cursor"]
