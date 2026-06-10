"""Resolve packaged vs dev-clone portfolio SPA static directory."""

from __future__ import annotations

import os
import re
from pathlib import Path

_PKG_ROOT = Path(__file__).resolve().parent
_PACKAGED_STATIC = _PKG_ROOT / "static" / "portfolio"
_JS_IN_INDEX = re.compile(r"/assets/(index-[^\"']+\.js)")


def _repo_miniapp_dist() -> Path:
    """``miniapp/dist`` at repository root (dev clone)."""

    return _PKG_ROOT.parents[1] / "miniapp" / "dist"


def resolve_portfolio_static_dir() -> Path | None:
    """Return directory with built SPA (``index.html``), or ``None`` if unavailable.

    Prefer packaged ``static/portfolio`` (wheel / editable install) over gitignored
    ``miniapp/dist`` so stale local builds never shadow the shipped local-agent UI.
    """

    override = (os.environ.get("AUREY_PORTFOLIO_STATIC_DIR") or "").strip()
    if override:
        path = Path(override).expanduser()
        if (path / "index.html").is_file():
            return path
    if (_PACKAGED_STATIC / "index.html").is_file():
        return _PACKAGED_STATIC
    dev = _repo_miniapp_dist()
    if (dev / "index.html").is_file():
        return dev
    return None


def read_portfolio_ui_bundle_id(static_dir: Path | None = None) -> str | None:
    """Parse hashed JS bundle name from ``index.html`` (for diagnostics)."""

    root = static_dir or resolve_portfolio_static_dir()
    if root is None:
        return None
    index = root / "index.html"
    if not index.is_file():
        return None
    text = index.read_text(encoding="utf-8")
    match = _JS_IN_INDEX.search(text)
    return match.group(1) if match else None


def portfolio_ui_display_host(bind_host: str) -> str:
    """Host string suitable for user-facing URLs (not ``0.0.0.0``)."""

    host = (bind_host or "127.0.0.1").strip()
    if host in ("0.0.0.0", "::", "[::]"):
        return "127.0.0.1"
    return host


__all__ = [
    "portfolio_ui_display_host",
    "read_portfolio_ui_bundle_id",
    "resolve_portfolio_static_dir",
]
