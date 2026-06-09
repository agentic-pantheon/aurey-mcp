"""Register Aurey Wallet MCP with Hermes Agent (~/.hermes/config.yaml + .env)."""

from __future__ import annotations

import argparse
import getpass
import os
import subprocess
import sys
from pathlib import Path

from aurey_wallet_mcp.install_common import (
    DEFAULT_ALCHEMY_VAULT_PATH,
    LEGACY_VAULT_API_KEY_ENV,
    SERVER_NAME,
    VAULT_API_KEY_ENV,
    ensure_aurey_toml_alchemy_path,
    maybe_dev_sync,
    mcp_wrapper_path,
    resolve_mcp_command,
    smoke_test,
    upsert_dotenv,
    write_mcp_env,
    write_mcp_wrapper,
)

MCP_ENV_TEMPLATE: dict[str, str] = {
    "AUREY_ONECLAW_VAULT_ID": "${AUREY_ONECLAW_VAULT_ID}",
    "AUREY_ONECLAW_VAULT_API_KEY": "${AUREY_ONECLAW_VAULT_API_KEY}",
    "AUREY_ONECLAW_AGENT_ID": "${AUREY_ONECLAW_AGENT_ID}",
}


def _hermes_home() -> Path:
    return Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes")).expanduser()


def _load_yaml(path: Path) -> dict:
    try:
        import yaml
    except ImportError as exc:
        raise SystemExit(
            "PyYAML is required for config.yaml updates. Run: uv sync --extra hermes"
        ) from exc
    if not path.is_file():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def _save_yaml(path: Path, data: dict) -> None:
    import yaml

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.dump(data, default_flow_style=False, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )


def patch_hermes_mcp_config(config_path: Path, *, command: str) -> None:
    data = _load_yaml(config_path)
    servers = data.setdefault("mcp_servers", {})
    if not isinstance(servers, dict):
        servers = {}
        data["mcp_servers"] = servers
    servers[SERVER_NAME] = {
        "command": command,
        "enabled": True,
        "env": dict(MCP_ENV_TEMPLATE),
    }
    _save_yaml(config_path, data)


def collect_secrets(
    *,
    vault_id: str | None,
    agent_id: str | None,
    vault_api_key: str | None,
    prompt: bool,
    from_env: bool,
) -> dict[str, str]:
    out: dict[str, str] = {}

    def _pick(name: str, cli: str | None, *, secret: bool) -> str:
        if cli:
            return cli.strip()
        if from_env:
            val = os.environ.get(name, "").strip()
            if val:
                return val
            if secret and name == VAULT_API_KEY_ENV:
                val = os.environ.get(LEGACY_VAULT_API_KEY_ENV, "").strip()
                if val:
                    return val
        if prompt:
            label = name
            if name == VAULT_API_KEY_ENV:
                label = f"{name} (1Claw agent API key, ocv_…)"
            if secret:
                try:
                    val = getpass.getpass(f"{label}: ").strip()
                except Exception:
                    val = input(f"{label}: ").strip()
            else:
                val = input(f"{label}: ").strip()
            return val
        return ""

    out["AUREY_ONECLAW_VAULT_ID"] = _pick("AUREY_ONECLAW_VAULT_ID", vault_id, secret=False)
    out["AUREY_ONECLAW_AGENT_ID"] = _pick("AUREY_ONECLAW_AGENT_ID", agent_id, secret=False)
    vault_key = _pick(VAULT_API_KEY_ENV, vault_api_key, secret=True)
    if vault_key:
        out[VAULT_API_KEY_ENV] = vault_key
    return out


def run_install(
    *,
    repo: str | None = None,
    skip_sync: bool = False,
    vault_id: str | None = None,
    agent_id: str | None = None,
    vault_api_key: str | None = None,
    alchemy_vault_path: str = DEFAULT_ALCHEMY_VAULT_PATH,
    skip_smoke_test: bool = False,
    hermes_home: str | None = None,
    from_env: bool = False,
    prompt_secrets: bool = False,
    quiet: bool = False,
    mcp_command: str | None = None,
) -> dict[str, str]:
    """Wire Hermes MCP config and ~/.hermes/.env; return secrets written."""

    if hermes_home:
        os.environ["HERMES_HOME"] = hermes_home

    home = _hermes_home()
    config_path = home / "config.yaml"
    env_path = home / ".env"
    aurey_toml = Path.home() / ".aurey" / "config.toml"

    maybe_dev_sync(repo, skip_sync=skip_sync)
    binary = resolve_mcp_command(repo)
    secrets = collect_secrets(
        vault_id=vault_id,
        agent_id=agent_id,
        vault_api_key=vault_api_key,
        prompt=prompt_secrets,
        from_env=from_env,
    )

    missing = [
        k
        for k in ("AUREY_ONECLAW_VAULT_ID", VAULT_API_KEY_ENV, "AUREY_ONECLAW_AGENT_ID")
        if not secrets.get(k, "").strip()
    ]
    if missing and not quiet:
        print(
            "Warning: missing in .env (MCP will fail until set): " + ", ".join(missing),
            file=sys.stderr,
        )
        print(
            "Re-run with --prompt-secrets, --from-env, or pass flags. "
            "Do not paste ocv_ keys into agent chat.",
            file=sys.stderr,
        )

    written = upsert_dotenv(
        env_path, secrets, comment="Aurey Wallet MCP (aurey-hermes-install)"
    )
    if secrets.get(VAULT_API_KEY_ENV, "").strip():
        env_file = write_mcp_env(secrets)
        wrapper = write_mcp_wrapper(binary=binary, env_path=env_file)
        launch = mcp_command or str(wrapper)
    else:
        launch = mcp_command or str(mcp_wrapper_path() if mcp_wrapper_path().is_file() else binary)
    patch_hermes_mcp_config(config_path, command=launch)
    ensure_aurey_toml_alchemy_path(aurey_toml, secret_path=alchemy_vault_path.strip())

    if not quiet:
        print(f"✓ MCP server '{SERVER_NAME}' → {launch}")
        print(f"✓ Updated {config_path}")
        print(f"✓ Wrote {', '.join(written) or '(no .env changes)'} in {env_path}")
        print(f"✓ Alchemy via 1Claw vault path {alchemy_vault_path!r} in {aurey_toml}")
        if not secrets.get(VAULT_API_KEY_ENV, "").strip():
            print("  Store your Alchemy key in 1Claw at that path (Human API or dashboard).")
        print("  Next: hermes mcp test aurey-wallet")
        print("  In Hermes chat: /reload-mcp")

    if not skip_smoke_test and not missing:
        try:
            smoke_test(binary, secrets)
            if not quiet:
                print("✓ Smoke test: MCP process started (bootstrap OK)")
        except subprocess.TimeoutExpired:
            if not quiet:
                print("✓ Smoke test: process stayed up (stdio wait)")
        except SystemExit as exc:
            if not quiet:
                print(f"✗ Smoke test failed: {exc}", file=sys.stderr)
            raise

    return secrets


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Install Aurey Wallet MCP into Hermes (~/.hermes/config.yaml + .env).",
    )
    p.add_argument("--repo", help="Path to aurey-wallet-mcp clone")
    p.add_argument("--skip-sync", action="store_true")
    p.add_argument("--vault-id", help="1Claw vault UUID")
    p.add_argument("--agent-id", help="1Claw agent UUID (Intents enabled)")
    p.add_argument("--vault-api-key", help="1Claw agent API key (ocv_…)")
    p.add_argument("--alchemy-vault-path", default=DEFAULT_ALCHEMY_VAULT_PATH)
    p.add_argument("--from-env", action="store_true")
    p.add_argument("--prompt-secrets", action="store_true")
    p.add_argument("--skip-smoke-test", action="store_true")
    p.add_argument("--hermes-home", help="Override Hermes home (default: ~/.hermes)")
    return p


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    run_install(
        repo=args.repo,
        skip_sync=args.skip_sync,
        vault_id=args.vault_id,
        agent_id=args.agent_id,
        vault_api_key=args.vault_api_key,
        alchemy_vault_path=args.alchemy_vault_path,
        skip_smoke_test=args.skip_smoke_test,
        hermes_home=args.hermes_home,
        from_env=args.from_env,
        prompt_secrets=args.prompt_secrets,
    )


if __name__ == "__main__":
    main()
