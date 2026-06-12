"""Print installed Aurey Wallet MCP package version."""

from __future__ import annotations

import argparse
import importlib.metadata
import sys

PACKAGE_NAME = "aurey-wallet-mcp"


def package_version() -> str:
    return importlib.metadata.version(PACKAGE_NAME)


def print_version(*, verbose: bool = False) -> None:
    print(package_version())
    if not verbose:
        return
    try:
        from aurey_wallet_mcp.install_common import resolve_mcp_command

        path = resolve_mcp_command()
        print(f"binary: {path}", file=sys.stderr)
    except SystemExit:
        print("binary: (not found on PATH)", file=sys.stderr)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Print installed aurey-wallet-mcp version.")
    p.add_argument("--verbose", "-v", action="store_true", help="Also print MCP binary path")
    p.add_argument(
        "--version",
        action="store_true",
        help="Print version and exit (same as default output)",
    )
    return p


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    print_version(verbose=args.verbose)


if __name__ == "__main__":
    main()
