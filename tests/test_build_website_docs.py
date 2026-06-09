"""Tests for GitHub Pages install doc generation."""

from __future__ import annotations

import re
from pathlib import Path

from scripts.build_website_docs import build


def test_build_website_docs_outputs(tmp_path: Path) -> None:
    website = tmp_path / "website"
    written = build(website_dir=website)

    names = {p.name for p in written}
    assert "install.html" in names
    assert (website / "install" / "cursor.html").is_file()

    cursor_html = (website / "install" / "cursor.html").read_text(encoding="utf-8")
    assert "aurey-setup --host cursor" in cursor_html
    assert re.search(r"\]\(\.\./", cursor_html) is None

    install_html = (website / "install.html").read_text(encoding="utf-8")
    assert 'href="install/cursor.html"' in install_html
    assert "[hermes]" in install_html
