# Troubleshooting — Aurey Wallet MCP

Shared fixes for all MCP hosts. Install flow: [install/index.md](../install/index.md).

## `aurey-setup` or `aurey-wallet-mcp` not found

- After `pip install --user`, add Python’s user `bin` directory to `PATH`.
- After `uv tool install`, ensure `~/.local/bin` (or `uv tool dir`) is on `PATH`.
- From a git clone, use `uv run aurey-setup` so the project venv is used.

## MCP server shows error / red in the host UI

1. Confirm `~/.aurey/mcp.env` exists and is mode **600**.
2. Confirm `~/.aurey/run-aurey-wallet-mcp.sh` is executable and points at a valid `aurey-wallet-mcp` binary.
3. Run the wrapper manually in a terminal (secrets stay local):

   ```bash
   ~/.aurey/run-aurey-wallet-mcp.sh
   ```

   Fix any missing env vars reported in stderr (`AUREY_ONECLAW_VAULT_ID`, `AUREY_ONECLAW_AGENT_ID`, `AUREY_ONECLAW_VAULT_API_KEY`).

4. Reload the host (Cursor Settings → MCP, Hermes `/reload-mcp`, etc.).

## Cursor: global vs project MCP config

| Scope | Config file |
|-------|-------------|
| Global | `~/.cursor/mcp.json` |
| Project | `<project>/.cursor/mcp.json` |

Re-wire without re-provisioning:

```bash
aurey-setup --host cursor --skip-provision
aurey-setup --host cursor --cursor-project /path/to/project
aurey-setup --host cursor --config ~/.cursor/mcp.json
```

## Re-provision vs re-wire only

| Flag | Effect |
|------|--------|
| `--provision-only` | 1Claw + `~/.aurey/mcp.env` only; no host JSON/YAML |
| `--skip-provision` | Patch host MCP config from existing `~/.aurey/mcp.env` |

## Balance reads fail / Alchemy errors

- Alchemy is stored in the 1Claw vault at `api-keys/alchemy`, not in MCP host JSON.
- Re-run setup with an Alchemy key, or add the secret in the 1Claw dashboard and ensure `~/.aurey/config.toml` has `alchemy_secret_path = "api-keys/alchemy"`.

## Host config locations

| Host | Config |
|------|--------|
| Hermes | `~/.hermes/config.yaml`, `~/.hermes/.env` |
| Cursor | `~/.cursor/mcp.json` or project `.cursor/mcp.json` |
| Claude Desktop | macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`; Linux: `~/.config/Claude/claude_desktop_config.json` |
| OpenClaw | `~/.openclaw/openclaw.json` or `OPENCLAW_CONFIG` |

## Manual 1Claw setup

See [1claw-onboarding-guide.md](1claw-onboarding-guide.md) Path B.

## Still stuck

Open an issue with host name, redacted error text (no `1ck_` / `ocv_`), and whether `get_agent_wallet_addresses` was attempted.
