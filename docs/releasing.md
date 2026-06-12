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
2. The `pages.yml` workflow deploys the `website/` directory on pushes to `main`.

## Release checklist

1. Update `pyproject.toml` version and changelog notes in the GitHub release body if needed.
2. Refresh bundled LiFi tokens if the catalog changed: `uv run python scripts/sync_bundled_lifi_tokens.py --from-file …` or `--fetch`.
3. Refresh curated x402 services when Ampersend listings change:
   - Regenerate seed: `python3 scripts/build_x402_services_seed.py` (curated tables), or scrape:
     `uv run --with playwright scripts/sync_x402_services_from_ampersend.py`
   - Commit `src/aurey/data/x402_services.json`. **No PyPI release needed** for catalog-only edits:
     push to `main` on `agentic-pantheon/aurey-mcp`; MCP clients refetch from the default GitHub raw URL after TTL.
4. After install doc changes, preview Pages HTML: `uv run python scripts/build_website_docs.py` (CI runs this before deploy; output is not committed).
5. `uv run pytest` (or `pytest`) green locally.
6. `git tag v0.1.1 && git push origin v0.1.1`
7. Watch **Actions → Release** for PyPI upload and GitHub Release assets.
8. Verify:
   - `pip install 'aurey-wallet-mcp[hermes]'==0.1.1`
   - `aurey-version`
   - `aurey-setup --help`
   - Pages: https://agentic-pantheon.github.io/aurey-mcp/install.html
   - `curl -fsSL https://agentic-pantheon.github.io/aurey-mcp/install.sh | bash` (dry run on a VM)

## Manual build (maintainers)

```bash
uv build
python -m twine check dist/*
```

Do not publish manually unless CI is broken; prefer tag-driven releases.
