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
2. `uv run pytest` (or `pytest`) green locally.
3. `git tag v0.1.1 && git push origin v0.1.1`
4. Watch **Actions → Release** for PyPI upload and GitHub Release assets.
5. Verify:
   - `pip install 'aurey-wallet-mcp[hermes]'==0.1.1`
   - `aurey-setup --help`
   - Pages: https://agentic-pantheon.github.io/aurey-mcp/install.html
   - `curl -fsSL https://agentic-pantheon.github.io/aurey-mcp/install.sh | bash` (dry run on a VM)

## Manual build (maintainers)

```bash
uv build
python -m twine check dist/*
```

Do not publish manually unless CI is broken; prefer tag-driven releases.
