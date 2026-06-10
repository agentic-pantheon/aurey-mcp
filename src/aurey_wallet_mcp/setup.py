"""One-command Aurey setup: 1Claw provision (1ck_…) + MCP install (any host)."""

from __future__ import annotations

import argparse
import getpass
import os
import sys

from pathlib import Path

from aurey_wallet_mcp.install_common import (
    DEFAULT_ALCHEMY_VAULT_PATH,
    DEFAULT_LIFI_VAULT_PATH,
    DEFAULT_ZERION_VAULT_PATH,
    HUMAN_API_KEY_ENV,
    LIFI_EARN_QUICKSTART_URL,
    LIFI_SETUP_HINT,
    ZERION_DEVELOPERS_URL,
    ZERION_SETUP_HINT,
    McpHost,
    ensure_aurey_toml_lifi_path,
    ensure_aurey_toml_zerion_path,
    load_mcp_env,
    secrets_from_ids,
)
from aurey_wallet_mcp.mcp_hosts import run_host_install
from aurey_wallet_mcp.oneclaw_provision import (
    OneClawProvisionError,
    provision_for_aurey,
)

HOST_CHOICES: tuple[McpHost, ...] = ("hermes", "cursor", "claude", "openclaw")


def _pick_human_api_key(cli: str | None, *, prompt: bool, from_env: bool) -> str:
    if cli and cli.strip():
        return cli.strip()
    if from_env:
        val = os.environ.get(HUMAN_API_KEY_ENV, "").strip()
        if val:
            return val
    if prompt:
        try:
            val = getpass.getpass("1Claw human API key (1ck_…): ").strip()
        except Exception:
            val = input("1Claw human API key (1ck_…): ").strip()
        return val
    return ""


def _pick_alchemy(cli: str | None, *, prompt: bool, skip: bool) -> str | None:
    if skip:
        return None
    if cli is not None:
        return cli.strip() or None
    if not prompt:
        return None
    try:
        val = getpass.getpass(
            f"Alchemy API key (Enter to skip; stored in 1Claw at {DEFAULT_ALCHEMY_VAULT_PATH}): "
        ).strip()
    except Exception:
        val = input(
            f"Alchemy API key (Enter to skip; stored in 1Claw at {DEFAULT_ALCHEMY_VAULT_PATH}): "
        ).strip()
    return val or None


def _pick_lifi(cli: str | None, *, prompt: bool, skip: bool) -> str | None:
    if skip:
        return None
    if cli is not None:
        return cli.strip() or None
    if not prompt:
        return None
    print(LIFI_SETUP_HINT, file=sys.stderr)
    try:
        val = getpass.getpass(
            f"LiFi API key (Enter to skip; stored in 1Claw at {DEFAULT_LIFI_VAULT_PATH}): "
        ).strip()
    except Exception:
        val = input(
            f"LiFi API key (Enter to skip; stored in 1Claw at {DEFAULT_LIFI_VAULT_PATH}): "
        ).strip()
    return val or None


def _pick_zerion(cli: str | None, *, prompt: bool, skip: bool) -> str | None:
    if skip:
        return None
    if cli is not None:
        return cli.strip() or None
    if not prompt:
        return None
    print(ZERION_SETUP_HINT, file=sys.stderr)
    try:
        val = getpass.getpass(
            f"Zerion API key (Enter to skip; stored in 1Claw at {DEFAULT_ZERION_VAULT_PATH}): "
        ).strip()
    except Exception:
        val = input(
            f"Zerion API key (Enter to skip; stored in 1Claw at {DEFAULT_ZERION_VAULT_PATH}): "
        ).strip()
    return val or None


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Provision 1Claw (human 1ck_ key) and install Aurey Wallet MCP for your host.",
    )
    p.add_argument(
        "--host",
        choices=HOST_CHOICES,
        default="hermes",
        help="MCP harness (default: hermes)",
    )
    p.add_argument("--repo", help="Path to aurey-wallet-mcp clone")
    p.add_argument("--skip-sync", action="store_true", help="Skip uv sync --group dev")
    p.add_argument("--skip-smoke-test", action="store_true", help="Skip MCP bootstrap smoke test")
    p.add_argument("--hermes-home", help="Override Hermes home (default: ~/.hermes)")
    p.add_argument(
        "--config",
        help="Override host MCP config (Cursor mcp.json, Claude desktop, OpenClaw json)",
    )
    p.add_argument(
        "--cursor-project",
        help="Install Cursor MCP into <path>/.cursor/mcp.json instead of ~/.cursor/mcp.json",
    )
    p.add_argument("--human-api-key", help="1Claw personal API key (1ck_…); terminal only")
    p.add_argument("--from-env", action="store_true", help=f"Human key from {HUMAN_API_KEY_ENV}")
    p.add_argument("--prompt-secrets", action="store_true", default=True)
    p.add_argument("--no-prompt-secrets", action="store_false", dest="prompt_secrets")
    p.add_argument("--vault-id", help="Use this vault UUID instead of auto-picking/creating")
    p.add_argument("--alchemy-key", help="Alchemy key to store in 1Claw vault")
    p.add_argument("--skip-alchemy", action="store_true")
    p.add_argument("--alchemy-vault-path", default=DEFAULT_ALCHEMY_VAULT_PATH)
    p.add_argument("--lifi-key", help="LiFi API key to store in 1Claw vault (Earn + quote rate limits)")
    p.add_argument("--skip-lifi", action="store_true", help="Do not prompt for LiFi API key")
    p.add_argument("--lifi-vault-path", default=DEFAULT_LIFI_VAULT_PATH)
    p.add_argument(
        "--zerion-key",
        help="Zerion API key to store in 1Claw vault (Telegram Mini App portfolio)",
    )
    p.add_argument("--skip-zerion", action="store_true", help="Do not prompt for Zerion API key")
    p.add_argument("--zerion-vault-path", default=DEFAULT_ZERION_VAULT_PATH)
    p.add_argument(
        "--skip-provision",
        action="store_true",
        help="Skip 1Claw API; use existing ~/.aurey/mcp.env credentials",
    )
    p.add_argument(
        "--provision-only",
        action="store_true",
        help="Only provision 1Claw; write ~/.aurey/mcp.env (no host MCP config)",
    )
    p.add_argument(
        "--oneclaw-base-url",
        default=os.environ.get("AUREY_ONECLAW_BASE_URL", "https://api.1claw.xyz"),
    )
    return p


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    host: McpHost = args.host

    if args.skip_provision and args.provision_only:
        raise SystemExit("Use only one of --skip-provision or --provision-only.")

    secrets: dict[str, str] = {}
    lifi_configured_path: str | None = None
    zerion_configured_path: str | None = None

    if args.skip_provision:
        secrets = load_mcp_env()
        print(f"✓ Using credentials from {os.path.expanduser('~/.aurey/mcp.env')}")
    else:
        human_key = _pick_human_api_key(
            args.human_api_key,
            prompt=args.prompt_secrets,
            from_env=args.from_env,
        )
        if not human_key:
            raise SystemExit(
                f"Missing 1Claw human API key. Re-run with --prompt-secrets, "
                f"--from-env ({HUMAN_API_KEY_ENV}), or --human-api-key."
            )
        alchemy = _pick_alchemy(
            args.alchemy_key,
            prompt=args.prompt_secrets,
            skip=args.skip_alchemy,
        )
        lifi = _pick_lifi(
            args.lifi_key,
            prompt=args.prompt_secrets,
            skip=args.skip_lifi,
        )
        zerion = _pick_zerion(
            args.zerion_key,
            prompt=args.prompt_secrets,
            skip=args.skip_zerion,
        )
        print("Provisioning 1Claw (vault, Intents agent, policy, Ethereum signing key)…")
        try:
            result = provision_for_aurey(
                human_key,
                base_url=args.oneclaw_base_url.strip(),
                vault_id=args.vault_id,
                alchemy_api_key=alchemy,
                alchemy_secret_path=args.alchemy_vault_path.strip(),
                lifi_api_key=lifi,
                lifi_secret_path=args.lifi_vault_path.strip(),
                zerion_api_key=zerion,
                zerion_secret_path=args.zerion_vault_path.strip(),
            )
        except OneClawProvisionError as exc:
            raise SystemExit(str(exc)) from exc

        secrets = secrets_from_ids(
            vault_id=result.vault_id,
            agent_id=result.agent_id,
            vault_api_key=result.agent_api_key,
        )
        print(f"✓ Vault id: {result.vault_id}")
        print(f"✓ Agent id: {result.agent_id}")
        if result.ethereum_address:
            print(f"✓ Ethereum signing key: {result.ethereum_address}")
        else:
            print(
                "  Note: Ethereum address not returned yet; "
                "use get_agent_wallet_addresses(refresh=true).",
                file=sys.stderr,
            )
        if result.alchemy_secret_path:
            print(f"✓ Alchemy stored in 1Claw at {result.alchemy_secret_path!r}")
        elif not args.skip_alchemy:
            print(
                f"  Add Alchemy later at 1Claw path {args.alchemy_vault_path!r}.",
                file=sys.stderr,
            )
        lifi_configured_path = result.lifi_secret_path
        if result.lifi_secret_path:
            print(f"✓ LiFi API key stored in 1Claw at {result.lifi_secret_path!r}")
        elif not args.skip_lifi:
            print(
                f"  LiFi optional: add later for Earn vault discovery — {LIFI_EARN_QUICKSTART_URL}",
                file=sys.stderr,
            )
        zerion_configured_path = result.zerion_secret_path
        if result.zerion_secret_path:
            print(f"✓ Zerion API key stored in 1Claw at {result.zerion_secret_path!r}")
        elif not args.skip_zerion:
            print(
                f"  Zerion optional: add later for Mini App portfolio — {ZERION_DEVELOPERS_URL}",
                file=sys.stderr,
            )

        if args.provision_only:
            from aurey_wallet_mcp.install_common import write_mcp_env

            path = write_mcp_env(secrets)
            aurey_toml = Path.home() / ".aurey" / "config.toml"
            if lifi_configured_path:
                ensure_aurey_toml_lifi_path(aurey_toml, secret_path=lifi_configured_path)
            if zerion_configured_path:
                ensure_aurey_toml_zerion_path(aurey_toml, secret_path=zerion_configured_path)
            print(f"✓ Credentials written to {path}")
            print(f"  Install MCP later: uv run aurey-setup --host {host} --skip-provision")
            return

    if args.provision_only:
        return

    run_host_install(
        host,
        repo=args.repo,
        skip_sync=args.skip_sync,
        secrets=secrets,
        alchemy_vault_path=args.alchemy_vault_path.strip(),
        lifi_vault_path=lifi_configured_path,
        zerion_vault_path=zerion_configured_path,
        skip_smoke_test=args.skip_smoke_test,
        hermes_home=args.hermes_home,
        cursor_project=args.cursor_project,
        config_path=args.config,
    )


if __name__ == "__main__":
    main()
