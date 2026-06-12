"""Upgrade aurey-wallet-mcp from PyPI and optionally re-wire MCP host config."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys

from aurey_wallet_mcp.install_common import (
    McpHost,
    host_reload_hint,
    load_mcp_env,
    mcp_env_path,
)
from aurey_wallet_mcp.mcp_hosts import run_host_install
from aurey_wallet_mcp.version_cli import package_version, print_version

DEFAULT_PACKAGE = "aurey-wallet-mcp[hermes]"
HOST_CHOICES: tuple[McpHost, ...] = ("hermes", "cursor", "claude", "openclaw")


def package_spec(*, package: str, pin: str | None) -> str:
    if pin:
        return f"{package}=={pin}"
    return package


def upgrade_installed_package(spec: str, *, method: str) -> None:
    if method == "auto":
        if shutil.which("uv") is not None:
            method = "uv"
        else:
            method = "pip"

    if method == "uv":
        if shutil.which("uv") is None:
            raise SystemExit("`uv` not on PATH. Install uv or use --method pip.")
        subprocess.run(["uv", "tool", "install", "--force", spec], check=True)
        return

    if method == "pip":
        if shutil.which("pipx") is not None:
            subprocess.run(["pipx", "install", "--force", spec], check=True)
            return
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "--user", "--upgrade", spec],
            check=True,
        )
        return

    raise SystemExit(f"Unknown install method: {method!r} (use auto, uv, or pip)")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Upgrade aurey-wallet-mcp from PyPI and optionally refresh MCP host wiring.",
    )
    p.add_argument(
        "--version",
        action="store_true",
        help="Print installed version and exit",
    )
    p.add_argument(
        "--pin-version",
        dest="pin_version",
        metavar="X.Y.Z",
        help="Install this PyPI version instead of latest",
    )
    p.add_argument(
        "--method",
        choices=("auto", "uv", "pip"),
        default="auto",
        help="Install tool (default: auto — uv if available, else pip)",
    )
    p.add_argument(
        "--package",
        default=DEFAULT_PACKAGE,
        help=f"Package spec to install (default: {DEFAULT_PACKAGE})",
    )
    p.add_argument(
        "--host",
        choices=HOST_CHOICES,
        help="After upgrade, re-wire MCP config from ~/.aurey/mcp.env (--skip-provision)",
    )
    p.add_argument(
        "--skip-rewire",
        action="store_true",
        help="Upgrade only; do not touch MCP config",
    )
    p.add_argument("--repo", help="Dev repo path for resolve_mcp_command during re-wire")
    p.add_argument("--hermes-home", help="Override Hermes home when re-wiring")
    p.add_argument("--config", help="Override host MCP config path when re-wiring")
    p.add_argument("--cursor-project", help="Cursor project .cursor/mcp.json when re-wiring")
    p.add_argument(
        "--skip-smoke-test",
        action="store_true",
        help="Skip MCP bootstrap smoke test after re-wire",
    )
    return p


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    if args.version:
        print_version()
        return

    before = package_version()
    print(f"Current version: {before}")

    spec = package_spec(package=args.package, pin=args.pin_version)
    print(f"→ Installing {spec} ({args.method}) …")
    upgrade_installed_package(spec, method=args.method)

    after = package_version()
    print(f"✓ Upgraded to {after}")

    if args.skip_rewire or not args.host:
        if args.host is None and not args.skip_rewire:
            print(
                "Tip: pass --host hermes (or cursor/claude/openclaw) "
                "to refresh MCP config after upgrade.",
                file=sys.stderr,
            )
        return

    env_path = mcp_env_path()
    if not env_path.is_file():
        raise SystemExit(
            f"Missing {env_path}. Run aurey-setup first, or use --skip-rewire to upgrade only."
        )

    secrets = load_mcp_env(env_path)
    host: McpHost = args.host
    print(f"→ Re-wiring MCP for host {host!r} …")
    run_host_install(
        host,
        repo=args.repo,
        skip_sync=True,
        secrets=secrets,
        skip_smoke_test=args.skip_smoke_test,
        hermes_home=args.hermes_home,
        cursor_project=args.cursor_project,
        config_path=args.config,
        skip_portfolio_ui=True,
        zerion_skipped=True,
    )
    print(f"✓ {host_reload_hint(host)}")


if __name__ == "__main__":
    main()
