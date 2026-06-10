"""Per-host MCP config writers for aurey-setup."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from aurey_wallet_mcp.install_common import (
    DEFAULT_ALCHEMY_VAULT_PATH,
    SERVER_NAME,
    ZERION_DEVELOPERS_URL,
    McpHost,
    ensure_aurey_toml_alchemy_path,
    ensure_aurey_toml_dashboard_enabled,
    ensure_aurey_toml_lifi_path,
    ensure_aurey_toml_zerion_path,
    host_reload_hint,
    load_json_object,
    maybe_dev_sync,
    missing_required,
    resolve_mcp_command,
    save_json_object,
    smoke_test,
    write_mcp_env,
    write_mcp_wrapper,
)


def default_cursor_mcp_path(*, project: Path | None) -> Path:
    if project is not None:
        return project / ".cursor" / "mcp.json"
    return Path.home() / ".cursor" / "mcp.json"


def default_claude_desktop_config() -> Path:
    home = Path.home()
    if sys.platform == "darwin":
        return home / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
    if os.name == "nt":
        appdata = os.environ.get("APPDATA", "")
        if appdata:
            return Path(appdata) / "Claude" / "claude_desktop_config.json"
    return home / ".config" / "Claude" / "claude_desktop_config.json"


def default_openclaw_config() -> Path:
    env = os.environ.get("OPENCLAW_CONFIG", "").strip()
    if env:
        return Path(env).expanduser()
    home_cfg = Path.home() / ".openclaw" / "openclaw.json"
    if home_cfg.is_file():
        return home_cfg
    return Path.home() / ".openclaw" / "openclaw.json"


def _patch_cursor_config(path: Path, *, command: str) -> None:
    data = load_json_object(path)
    servers = data.setdefault("mcpServers", {})
    if not isinstance(servers, dict):
        servers = {}
        data["mcpServers"] = servers
    servers[SERVER_NAME] = {"command": command, "args": []}
    save_json_object(path, data)


def _patch_claude_config(path: Path, *, command: str) -> None:
    data = load_json_object(path)
    servers = data.setdefault("mcpServers", {})
    if not isinstance(servers, dict):
        servers = {}
        data["mcpServers"] = servers
    servers[SERVER_NAME] = {"command": command}
    save_json_object(path, data)


def _patch_openclaw_config(path: Path, *, command: str) -> None:
    data = load_json_object(path)
    mcp = data.setdefault("mcp", {})
    if not isinstance(mcp, dict):
        mcp = {}
        data["mcp"] = mcp
    servers = mcp.setdefault("servers", {})
    if not isinstance(servers, dict):
        servers = {}
        mcp["servers"] = servers
    servers[SERVER_NAME] = {"command": command, "enabled": True}
    save_json_object(path, data)


def run_host_install(
    host: McpHost,
    *,
    repo: str | None = None,
    skip_sync: bool = False,
    secrets: dict[str, str],
    alchemy_vault_path: str = DEFAULT_ALCHEMY_VAULT_PATH,
    lifi_vault_path: str | None = None,
    zerion_vault_path: str | None = None,
    skip_portfolio_ui: bool = False,
    zerion_skipped: bool = False,
    skip_smoke_test: bool = False,
    hermes_home: str | None = None,
    cursor_project: str | None = None,
    config_path: str | None = None,
) -> dict[str, str]:
    """Write credentials + host MCP config. Returns secrets used."""

    from aurey_wallet_mcp.hermes_install import run_install as run_hermes_install

    maybe_dev_sync(repo, skip_sync=skip_sync)
    binary = resolve_mcp_command(repo)
    env_file = write_mcp_env(secrets)
    wrapper = write_mcp_wrapper(binary=binary, env_path=env_file)
    aurey_toml = Path.home() / ".aurey" / "config.toml"
    ensure_aurey_toml_alchemy_path(aurey_toml, secret_path=alchemy_vault_path.strip())
    if lifi_vault_path and str(lifi_vault_path).strip():
        ensure_aurey_toml_lifi_path(aurey_toml, secret_path=str(lifi_vault_path).strip())
    if zerion_vault_path and str(zerion_vault_path).strip():
        ensure_aurey_toml_zerion_path(aurey_toml, secret_path=str(zerion_vault_path).strip())
    if not skip_portfolio_ui:
        ensure_aurey_toml_dashboard_enabled(aurey_toml, enabled=True)
        ensure_aurey_toml_zerion_path(aurey_toml, secret_path="api-keys/zerion")

    missing = missing_required(secrets)
    if missing:
        print(
            "Warning: missing credentials (MCP will fail until set): " + ", ".join(missing),
            file=sys.stderr,
        )

    if host == "hermes":
        run_hermes_install(
            repo=repo,
            skip_sync=True,
            vault_id=secrets.get("AUREY_ONECLAW_VAULT_ID"),
            agent_id=secrets.get("AUREY_ONECLAW_AGENT_ID"),
            vault_api_key=secrets.get("AUREY_ONECLAW_VAULT_API_KEY"),
            alchemy_vault_path=alchemy_vault_path,
            skip_smoke_test=True,
            hermes_home=hermes_home,
            from_env=False,
            prompt_secrets=False,
            quiet=True,
            mcp_command=str(wrapper),
        )
        print("✓ Hermes MCP command → wrapper (sources ~/.aurey/mcp.env)")
        print("✓ Hermes config ~/.hermes/config.yaml + ~/.hermes/.env")
        print(f"✓ Shared credentials {env_file}")
    elif host == "cursor":
        cfg = Path(config_path).expanduser() if config_path else default_cursor_mcp_path(
            project=Path(cursor_project).resolve() if cursor_project else None
        )
        _patch_cursor_config(cfg, command=str(wrapper))
        print(f"✓ MCP server '{SERVER_NAME}' → {wrapper}")
        print(f"✓ Updated {cfg}")
        print(f"✓ Credentials {env_file}")
        print(f"✓ Alchemy path {alchemy_vault_path!r} in {aurey_toml}")
    elif host == "claude":
        cfg = Path(config_path).expanduser() if config_path else default_claude_desktop_config()
        _patch_claude_config(cfg, command=str(wrapper))
        print(f"✓ MCP server '{SERVER_NAME}' → {wrapper}")
        print(f"✓ Updated {cfg}")
        print(f"✓ Credentials {env_file}")
        print(f"✓ Alchemy path {alchemy_vault_path!r} in {aurey_toml}")
    elif host == "openclaw":
        cfg = Path(config_path).expanduser() if config_path else default_openclaw_config()
        _patch_openclaw_config(cfg, command=str(wrapper))
        print(f"✓ MCP server '{SERVER_NAME}' → {wrapper}")
        print(f"✓ Updated {cfg}")
        print(f"✓ Credentials {env_file}")
        print(f"✓ Alchemy path {alchemy_vault_path!r} in {aurey_toml}")
    else:
        raise SystemExit(f"Unknown host: {host}")

    print(f"  Next: {host_reload_hint(host)}")
    if not skip_portfolio_ui:
        print("  Portfolio UI: http://127.0.0.1:8765/ (after MCP reload)")
        if zerion_skipped or not (zerion_vault_path and str(zerion_vault_path).strip()):
            print(
                "  Portfolio UI needs a free Zerion API key for live data — "
                f"{ZERION_DEVELOPERS_URL}",
                file=sys.stderr,
            )

    if not skip_smoke_test and not missing:
        try:
            smoke_test(binary, secrets)
            print("✓ Smoke test: MCP process started (bootstrap OK)")
        except subprocess.TimeoutExpired:
            print("✓ Smoke test: process stayed up (stdio wait)")
        except SystemExit:
            raise
        except Exception as exc:
            print(f"✗ Smoke test failed: {exc}", file=sys.stderr)
            raise SystemExit(str(exc)) from exc

    return secrets
