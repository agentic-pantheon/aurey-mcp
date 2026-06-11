"""Tests for setup-only human key exclusion from MCP env files."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from aurey.service.bootstrap import AureyRuntimeBootstrapError, bootstrap_aurey_runtime
from aurey_wallet_mcp.install_common import (
    HUMAN_API_KEY_ENV,
    VAULT_API_KEY_ENV,
    load_mcp_env,
    sanitize_mcp_secrets,
    smoke_test,
    write_mcp_env,
)


def test_write_mcp_env_strips_human_key(tmp_path: Path) -> None:
    env_path = tmp_path / "mcp.env"
    write_mcp_env(
        {
            "AUREY_ONECLAW_VAULT_ID": "vault-1",
            "AUREY_ONECLAW_AGENT_ID": "agent-1",
            VAULT_API_KEY_ENV: "ocv_test",
            HUMAN_API_KEY_ENV: "1ck_must_not_persist",
        },
        path=env_path,
    )
    text = env_path.read_text(encoding="utf-8")
    assert HUMAN_API_KEY_ENV not in text
    assert "1ck_must_not_persist" not in text
    assert "AUREY_ONECLAW_VAULT_ID=vault-1" in text
    assert f"{VAULT_API_KEY_ENV}=ocv_test" in text


def test_load_mcp_env_sanitizes_polluted_file(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    env_path = tmp_path / "mcp.env"
    env_path.write_text(
        "\n".join(
            [
                "AUREY_ONECLAW_VAULT_ID=v1",
                "AUREY_ONECLAW_AGENT_ID=a1",
                f"{VAULT_API_KEY_ENV}=ocv_x",
                f"{HUMAN_API_KEY_ENV}=1ck_stale",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    loaded = load_mcp_env(path=env_path)
    assert HUMAN_API_KEY_ENV not in loaded
    assert loaded[VAULT_API_KEY_ENV] == "ocv_x"
    err = capsys.readouterr().err
    assert "setup-only" in err.lower()


def test_sanitize_mcp_secrets_allowlist() -> None:
    raw = {
        "AUREY_ONECLAW_VAULT_ID": "v",
        VAULT_API_KEY_ENV: "ocv_a",
        "AUREY_ONECLAW_AGENT_ID": "a",
        HUMAN_API_KEY_ENV: "1ck_x",
        "EXTRA": "nope",
    }
    assert sanitize_mcp_secrets(raw) == {
        "AUREY_ONECLAW_VAULT_ID": "v",
        VAULT_API_KEY_ENV: "ocv_a",
        "AUREY_ONECLAW_AGENT_ID": "a",
    }


def test_smoke_test_does_not_pass_human_env_to_child(tmp_path: Path) -> None:
    binary = tmp_path / "fake-mcp"
    binary.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    binary.chmod(0o755)
    captured: dict[str, str] = {}

    def fake_run(*args, **kwargs):  # type: ignore[no-untyped-def]
        captured.update(kwargs.get("env", {}))
        return subprocess.CompletedProcess(args=args, returncode=0)

    with patch("aurey_wallet_mcp.install_common.subprocess.run", side_effect=fake_run):
        smoke_test(
            binary,
            {
                VAULT_API_KEY_ENV: "ocv_x",
                "AUREY_ONECLAW_VAULT_ID": "v1",
                "AUREY_ONECLAW_AGENT_ID": "a1",
                HUMAN_API_KEY_ENV: "1ck_should_drop",
            },
        )
    assert HUMAN_API_KEY_ENV not in captured
    assert captured.get(VAULT_API_KEY_ENV) == "ocv_x"


def test_bootstrap_rejects_human_key_in_process_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUREY_HOSTED_PLATFORM_ENABLED", "false")
    monkeypatch.setenv("AUREY_ONECLAW_VAULT_ID", "vault-test")
    monkeypatch.setenv("AUREY_ONECLAW_VAULT_API_KEY", "ocv_test_key")
    monkeypatch.setenv("AUREY_ONECLAW_AGENT_ID", "00000000-0000-4000-8000-000000000001")
    monkeypatch.setenv(HUMAN_API_KEY_ENV, "1ck_bad")

    with pytest.raises(AureyRuntimeBootstrapError, match="must not be set when running MCP"):
        bootstrap_aurey_runtime()


def test_bootstrap_rejects_1ck_as_vault_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUREY_HOSTED_PLATFORM_ENABLED", "false")
    monkeypatch.setenv("AUREY_ONECLAW_VAULT_ID", "vault-test")
    monkeypatch.setenv("AUREY_ONECLAW_VAULT_API_KEY", "1ck_wrong_slot")
    monkeypatch.setenv("AUREY_ONECLAW_AGENT_ID", "00000000-0000-4000-8000-000000000001")
    monkeypatch.delenv(HUMAN_API_KEY_ENV, raising=False)

    with pytest.raises(AureyRuntimeBootstrapError, match="ocv_"):
        bootstrap_aurey_runtime()
