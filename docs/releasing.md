# Releasing `aurey-wallet-mcp`

## Version policy

- Bump `version` in `pyproject.toml` to match the git tag (e.g. tag `v0.1.1` → `0.1.1`).
- Push the tag `v*` to trigger the release workflow.

## One-time PyPI trusted publishing (OIDC)

1. Create a PyPI project named **`aurey-wallet-mcp`** (exact spelling).
2. On PyPI → **Publishing** → add a **trusted publisher**:
   - Owner: `agentic-pantheon`
   - Repository: `aurey-mcp`
   - Workflow: `release.yml`
   - Environment: (leave empty unless you add a GitHub environment)
3. No long-lived PyPI token is required in GitHub secrets when using OIDC.

## One-time GitHub Pages

1. Repo **Settings → Pages** → Source: **GitHub Actions**.
2. The `pages.yml` workflow builds install HTML from `install/*.md`, copies `install/install.sh` into `website/`, then deploys `website/`.
3. Triggers include `install/**`, `scripts/build_website_docs.py`, and `website/**` (see `.github/workflows/pages.yml`).
4. Generated files (`website/install.html`, `website/install/*.html`) are **not** committed; CI builds them on each deploy.

### Local Pages preview

```bash
uv sync --group dev
uv run python scripts/build_website_docs.py
cp install/install.sh website/install.sh
# open website/index.html or serve website/ with any static server
```

## Release checklist

1. Update `pyproject.toml` version and changelog notes in the GitHub release body if needed.
2. Refresh bundled LiFi tokens if the catalog changed: `uv run python scripts/sync_bundled_lifi_tokens.py --from-file …` or `--fetch`.
3. `uv run pytest` green locally.
4. After editing install docs, run `uv run python scripts/build_website_docs.py` locally to preview.
5. `git tag v0.1.1 && git push origin v0.1.1`
6. Watch **Actions → Release** for PyPI upload and GitHub Release assets.
7. Verify:
   - `pip install 'aurey-wallet-mcp[hermes]'==0.1.1`
   - `aurey-setup --help`
   - Pages: https://agentic-pantheon.github.io/aurey-mcp/install.html
   - Host pages: https://agentic-pantheon.github.io/aurey-mcp/install/cursor.html
   - `curl -fsSL https://agentic-pantheon.github.io/aurey-mcp/install.sh | bash` (dry run on a VM)

## Manual build (maintainers)

```bash
uv build
python -m twine check dist/*
```

Do not publish manually unless CI is broken; prefer tag-driven releases.
