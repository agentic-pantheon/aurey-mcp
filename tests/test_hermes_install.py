"""Tests for Hermes install helper."""

from __future__ import annotations

from pathlib import Path

from aurey_wallet_mcp.install_common import upsert_dotenv


def test_upsert_dotenv_merges_and_updates(tmp_path: Path) -> None:
    env = tmp_path / ".env"
    env.write_text("FOO=bar\nAUREY_ONECLAW_VAULT_ID=old\n", encoding="utf-8")
    written = upsert_dotenv(
        env,
        {
            "AUREY_ONECLAW_VAULT_ID": "new-vault",
            "AUREY_EVM_SIGNING_MODE": "oneclaw_intents",
        },
        comment="test",
    )
    text = env.read_text(encoding="utf-8")
    assert "FOO=bar" in text
    assert "AUREY_ONECLAW_VAULT_ID=new-vault" in text
    assert "AUREY_ONECLAW_VAULT_ID=old" not in text
    assert "oneclaw_intents" in text
    assert "AUREY_ONECLAW_VAULT_ID" in written
