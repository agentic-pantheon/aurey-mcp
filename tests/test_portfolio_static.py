"""Portfolio SPA static directory resolution."""

from __future__ import annotations

from pathlib import Path

from aurey_wallet_mcp.portfolio_static import resolve_portfolio_static_dir

_PKG_STATIC = (
    Path(__file__).resolve().parents[1] / "src" / "aurey_wallet_mcp" / "static" / "portfolio"
)


def test_packaged_portfolio_index_exists() -> None:
    assert (_PKG_STATIC / "index.html").is_file()


def test_resolve_prefers_packaged_over_miniapp_dist() -> None:
    repo_dist = Path(__file__).resolve().parents[1] / "miniapp" / "dist"
    resolved = resolve_portfolio_static_dir()
    assert resolved is not None
    assert (resolved / "index.html").is_file()
    if (_PKG_STATIC / "index.html").is_file():
        assert resolved == _PKG_STATIC
    elif (repo_dist / "index.html").is_file():
        assert resolved == repo_dist
