"""Tests for aurey-version CLI."""

from __future__ import annotations

from aurey_wallet_mcp import __version__
from aurey_wallet_mcp.version_cli import package_version


def test_package_version_matches_metadata() -> None:
    assert package_version() == __version__
