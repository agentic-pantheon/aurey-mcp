"""Tests for package-first MCP binary resolution."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from aurey_wallet_mcp import install_common


def test_resolve_mcp_command_from_path(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    fake = tmp_path / "fake-aurey-wallet-mcp"
    fake.write_text("#!/bin/sh\n", encoding="utf-8")
    fake.chmod(0o755)

    monkeypatch.setattr(shutil, "which", lambda name: str(fake) if name == "aurey-wallet-mcp" else None)
    assert install_common.resolve_mcp_command(repo=None) == fake.resolve()


def test_resolve_mcp_command_dev_venv(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(shutil, "which", lambda _name: None)
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "pyproject.toml").write_text("[project]\nname = 'x'\n", encoding="utf-8")
    binary = repo / ".venv" / "bin" / "aurey-wallet-mcp"
    binary.parent.mkdir(parents=True)
    binary.write_text("#!/bin/sh\n", encoding="utf-8")

    assert install_common.resolve_mcp_command(repo=str(repo)) == binary.resolve()


def test_resolve_mcp_command_fails_without_install(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(shutil, "which", lambda _name: None)
    cwd = tmp_path / "empty"
    cwd.mkdir()
    monkeypatch.chdir(cwd)

    with pytest.raises(SystemExit) as exc:
        install_common.resolve_mcp_command(repo=None)
    assert "aurey-wallet-mcp" in str(exc.value)


def test_dev_repo_root_none_without_pyproject(tmp_path: Path) -> None:
    assert install_common.dev_repo_root(str(tmp_path)) is None


def test_dev_repo_root_from_cwd(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("[project]\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    assert install_common.dev_repo_root(None) == tmp_path.resolve()
