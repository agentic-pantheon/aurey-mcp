#!/usr/bin/env python3
"""Generate GitHub Pages install HTML from install/*.md.

Link policy:
- install/foo.md -> install/foo.html (or foo.html when output is under install/)
- ../docs/*.md, ../SKILL.md, ../skills/* -> GitHub blob URLs (repo not fully on Pages)
- https://... unchanged

Run: uv run python scripts/build_website_docs.py
"""

# ruff: noqa: E501 — embedded CSS literals are kept on one line per rule block.

from __future__ import annotations

import re
import sys
from pathlib import Path

import markdown

REPO_ROOT = Path(__file__).resolve().parents[1]
INSTALL_DIR = REPO_ROOT / "install"
WEBSITE_DIR = REPO_ROOT / "website"
GITHUB_BLOB = "https://github.com/agentic-pantheon/aurey-mcp/blob/main"

HOST_PAGES = ("hermes", "cursor", "claude", "openclaw")

PAGE_CSS = """
    :root { font-family: system-ui, sans-serif; line-height: 1.55; color: #111; max-width: 46rem; margin: 2rem auto; padding: 0 1rem; }
    code, pre { background: #f4f4f5; padding: 0.15rem 0.35rem; border-radius: 4px; font-size: 0.9em; }
    pre { padding: 1rem; overflow-x: auto; }
    pre code { background: none; padding: 0; }
    table { border-collapse: collapse; width: 100%; margin: 1rem 0; }
    th, td { border: 1px solid #ddd; padding: 0.5rem; text-align: left; }
    blockquote { background: #fff8e6; padding: 0.75rem 1rem; border-radius: 6px; margin: 1rem 0; border-left: none; }
    nav.site { margin: 1rem 0 1.5rem; }
    nav.site a { margin-right: 1rem; }
"""

NAV = """
  <nav class="site">
    <a href="index.html">Home</a>
    <a href="install.html">Install</a>
    <a href="install/cursor.html">Cursor</a>
    <a href="install/hermes.html">Hermes</a>
    <a href="install/claude.html">Claude</a>
    <a href="install/openclaw.html">OpenClaw</a>
    <a href="llms.txt">llms.txt</a>
    <a href="https://github.com/agentic-pantheon/aurey-mcp">GitHub</a>
  </nav>
"""

NAV_INSTALL_SUB = """
  <nav class="site">
    <a href="../index.html">Home</a>
    <a href="../install.html">Install</a>
    <a href="cursor.html">Cursor</a>
    <a href="hermes.html">Hermes</a>
    <a href="claude.html">Claude</a>
    <a href="openclaw.html">OpenClaw</a>
    <a href="../llms.txt">llms.txt</a>
    <a href="https://github.com/agentic-pantheon/aurey-mcp">GitHub</a>
  </nav>
"""


def _github_path(rel: str) -> str:
    rel = rel.lstrip("./")
    return f"{GITHUB_BLOB}/{rel}"


def rewrite_links(text: str, *, source: Path, out_under_install: bool) -> str:
    """Rewrite markdown link targets for GitHub Pages."""

    def sub_link(match: re.Match[str]) -> str:
        label, dest = match.group(1), match.group(2)
        if dest.startswith(("http://", "https://", "mailto:")):
            return match.group(0)
        if dest.startswith("#"):
            return match.group(0)

        dest_path = dest.split("#", 1)[0]
        anchor = ""
        if "#" in dest:
            anchor = "#" + dest.split("#", 1)[1]

        if dest_path.startswith("../"):
            rest = dest_path.removeprefix("../")
            if rest.startswith("docs/") or rest == "SKILL.md" or rest.startswith("skills/"):
                return f"[{label}]({_github_path(rest)}{anchor})"
            if rest == "install/index.md" or rest == "install/index":
                href = "../install.html" if out_under_install else "install.html"
                return f"[{label}]({href}{anchor})"
            return f"[{label}]({_github_path(rest)}{anchor})"

        if dest_path == "index.md":
            href = "../install.html" if out_under_install else "install.html"
            return f"[{label}]({href}{anchor})"

        if dest_path.endswith(".md"):
            name = Path(dest_path).stem
            if name in HOST_PAGES or dest_path in {f"{h}.md" for h in HOST_PAGES}:
                if out_under_install:
                    href = f"{name}.html"
                else:
                    href = f"install/{name}.html"
                return f"[{label}]({href}{anchor})"
            return f"[{label}]({_github_path(f'install/{dest_path}')}{anchor})"

        return match.group(0)

    return re.sub(r"\[([^\]]+)\]\(([^)]+)\)", sub_link, text)


def md_to_html_body(text: str) -> str:
    text = re.sub(r"\s+\{#([a-zA-Z0-9_-]+)\}\s*$", r"", text, flags=re.MULTILINE)
    body = markdown.markdown(
        text,
        extensions=["fenced_code", "tables", "nl2br"],
    )
    body = body.replace(
        "<h2>2 — Configure 1Claw and MCP</h2>",
        '<h2 id="hosts">2 — Configure 1Claw and MCP</h2>',
    )
    return body


def wrap_page(*, title: str, body: str, nav: str, home_href: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{title}</title>
  <style>{PAGE_CSS}</style>
</head>
<body>
  <p><a href="{home_href}">← Home</a></p>
{nav}
  <main>
{body}
  </main>
</body>
</html>
"""


def build(*, website_dir: Path | None = None) -> list[Path]:
    out_root = website_dir or WEBSITE_DIR
    install_out = out_root / "install"
    install_out.mkdir(parents=True, exist_ok=True)

    written: list[Path] = []

    index_src = INSTALL_DIR / "index.md"
    if not index_src.is_file():
        raise SystemExit(f"Missing {index_src}")
    index_raw = index_src.read_text(encoding="utf-8")
    index_md = rewrite_links(index_raw, source=index_src, out_under_install=False)
    index_html = wrap_page(
        title="Install — Aurey Wallet MCP",
        body=md_to_html_body(index_md),
        nav=NAV,
        home_href="index.html",
    )
    install_html_path = out_root / "install.html"
    install_html_path.write_text(index_html, encoding="utf-8")
    written.append(install_html_path)

    for host in HOST_PAGES:
        src = INSTALL_DIR / f"{host}.md"
        if not src.is_file():
            raise SystemExit(f"Missing {src}")
        md = rewrite_links(src.read_text(encoding="utf-8"), source=src, out_under_install=True)
        page = wrap_page(
            title=f"{host.title()} — Aurey Wallet MCP",
            body=md_to_html_body(md),
            nav=NAV_INSTALL_SUB,
            home_href="../index.html",
        )
        dest = install_out / f"{host}.html"
        dest.write_text(page, encoding="utf-8")
        written.append(dest)

    return written


def main() -> None:
    paths = build()
    for p in paths:
        print(f"wrote {p.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
    sys.exit(0)
