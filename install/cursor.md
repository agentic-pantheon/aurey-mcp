# Cursor — Aurey Wallet MCP

Same **one-command** flow as Hermes: provision 1Claw with a human `1ck_…` key, then patch Cursor MCP config.

## Setup (terminal only)

```bash
cd /path/to/aurey-wallet-mcp
uv sync --group dev
uv run aurey-setup --host cursor
```

**Prompts (masked):** 1Claw human `1ck_…`, optional Alchemy.

**Writes:**

| File | Purpose |
|------|---------|
| `~/.aurey/mcp.env` | Vault id, agent id, `ocv_…` (mode 600) |
| `~/.aurey/run-aurey-wallet-mcp.sh` | Sources `mcp.env`, runs MCP binary |
| `~/.cursor/mcp.json` | Adds `mcpServers.aurey-wallet` → wrapper script |
| `~/.aurey/config.toml` | `alchemy_secret_path = "api-keys/alchemy"` |

**Project-scoped MCP** (this repo only):

```bash
uv run aurey-setup --host cursor --cursor-project /path/to/your/project
```

**Custom config path:**

```bash
uv run aurey-setup --host cursor --config ~/.cursor/mcp.json
```

Then **restart Cursor** or reload MCP from Settings.

## Verify in chat

Load skills ([SKILL.md](../SKILL.md)). Ask the agent to call **`get_agent_wallet_addresses`**, then a read-only balance. Never paste `1ck_`/`ocv_` in chat.

## Re-install MCP only

If 1Claw is already provisioned:

```bash
uv run aurey-setup --host cursor --skip-provision
```

## Manual fallback

See [docs/1claw-onboarding-guide.md](../docs/1claw-onboarding-guide.md) Path B.

Hermes reference: [install/hermes.md](hermes.md).
