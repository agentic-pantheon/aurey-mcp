# Claude Desktop — Aurey Wallet MCP

Use the same **`aurey-setup`** command as Hermes and Cursor.

## Setup (terminal only)

```bash
cd /path/to/aurey-wallet-mcp
uv sync --group dev
uv run aurey-setup --host claude
```

**Prompts (masked):** 1Claw human `1ck_…`, optional Alchemy.

**Writes:**

| File | Purpose |
|------|---------|
| `~/.aurey/mcp.env` | Vault id, agent id, `ocv_…` |
| `~/.aurey/run-aurey-wallet-mcp.sh` | Wrapper script |
| Claude Desktop config | `mcpServers.aurey-wallet` → wrapper |

**Default Claude config paths:**

- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Linux: `~/.config/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`

Override:

```bash
uv run aurey-setup --host claude --config "/path/to/claude_desktop_config.json"
```

**Quit and reopen Claude Desktop** so MCP reloads.

## Verify

In Claude chat (with Aurey MCP connected): ask for **`get_agent_wallet_addresses`**, then a read-only balance. Load [skills](../SKILL.md).

## Re-install MCP only

```bash
uv run aurey-setup --host claude --skip-provision
```

See [install/hermes.md](hermes.md) for flags and troubleshooting.
