"""Aurey wallet MCP plugin — self-hosted wallet tools for Hermes, OpenClaw, and other MCP hosts."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("aurey-wallet-mcp")
except PackageNotFoundError:
    __version__ = "0.0.0"
