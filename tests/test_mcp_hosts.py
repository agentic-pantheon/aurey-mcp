"""Tests for multi-host MCP install helpers."""

from __future__ import annotations

import json
import stat
from pathlib import Path

from aurey_wallet_mcp.install_common import write_mcp_env, write_mcp_wrapper
from aurey_wallet_mcp.mcp_hosts import _patch_cursor_config, _patch_openclaw_config


def test_write_mcp_env_and_wrapper(tmp_path: Path) -> None:
    env_path = tmp_path / "mcp.env"
    binary = tmp_path / "bin" / "aurey-wallet-mcp"
    binary.parent.mkdir(parents=True)
    binary.write_text("#!/bin/sh\n", encoding="utf-8")
    write_mcp_env(
        {
            "AUREY_ONECLAW_VAULT_ID": "v1",
            "AUREY_ONECLAW_AGENT_ID": "a1",
            "AUREY_ONECLAW_VAULT_API_KEY": "ocv_x",
        },
        path=env_path,
    )
    assert "AUREY_ONECLAW_VAULT_ID=v1" in env_path.read_text(encoding="utf-8")
    mode = env_path.stat().st_mode
    assert mode & stat.S_IRWXG == 0
    wrapper = tmp_path / "run.sh"
    # monkeypatch wrapper path by writing directly
    body = (
        "#!/usr/bin/env sh\n"
        f'. "{env_path}"\n'
        f'exec "{binary}"\n'
    )
    wrapper.write_text(body, encoding="utf-8")
    assert "ocv_x" not in body or "mcp.env" in body


def test_patch_cursor_mcp_json(tmp_path: Path) -> None:
    cfg = tmp_path / "mcp.json"
    cfg.write_text(
        json.dumps({"mcpServers": {"other": {"command": "true"}}}),
        encoding="utf-8",
    )
    _patch_cursor_config(cfg, command="/home/user/.aurey/run-aurey-wallet-mcp.sh")
    data = json.loads(cfg.read_text(encoding="utf-8"))
    assert data["mcpServers"]["aurey-wallet"]["command"].endswith("run-aurey-wallet-mcp.sh")
    assert data["mcpServers"]["other"]["command"] == "true"


def test_patch_openclaw_mcp_section(tmp_path: Path) -> None:
    cfg = tmp_path / "openclaw.json"
    cfg.write_text("{}", encoding="utf-8")
    _patch_openclaw_config(cfg, command="/wrapper.sh")
    data = json.loads(cfg.read_text(encoding="utf-8"))
    assert data["mcp"]["servers"]["aurey-wallet"]["command"] == "/wrapper.sh"
