# OpenClaw — Aurey Wallet MCP

Same **one-command** flow: `aurey-setup` provisions 1Claw and patches OpenClaw MCP config.

## Setup (terminal only)

```bash
cd /path/to/aurey-wallet-mcp
uv sync --group dev
uv run aurey-setup --host openclaw
```

**Default config file:** `~/.openclaw/openclaw.json` (created if missing). Override with `OPENCLAW_CONFIG` or `--config`.

**Prompts (masked):** 1Claw human `1ck_…`, optional Alchemy.

**Writes:**

| File | Purpose |
|------|---------|
| `~/.aurey/mcp.env` | Credentials (mode 600) |
| `~/.aurey/run-aurey-wallet-mcp.sh` | Wrapper (no secrets in OpenClaw JSON) |
| `openclaw.json` | `mcp.servers.aurey-wallet` → wrapper |
| `~/.aurey/config.toml` | Alchemy vault path |

Example merged shape:

```json
{
  "mcp": {
    "servers": {
      "aurey-wallet": {
        "command": "/Users/you/.aurey/run-aurey-wallet-mcp.sh",
        "enabled": true
      }
    }
  }
}
```

**Project config:**

```bash
export OPENCLAW_CONFIG=/path/to/openclaw.json
uv run aurey-setup --host openclaw
# or
uv run aurey-setup --host openclaw --config /path/to/openclaw.json
```

**Restart the OpenClaw gateway** after install.

## Security

- Use **channel allowlists** so only trusted users can trigger wallet tools.
- Skills: `skills/aurey-wallet-onboarding/SKILL.md`, `skills/aurey-wallet/SKILL.md` ([SKILL.md](../SKILL.md)).

## Re-install MCP only

```bash
uv run aurey-setup --host openclaw --skip-provision
```

## Docs

- [install/hermes.md](hermes.md) — full `aurey-setup` reference (all `--host` values)
- [docs/1claw-onboarding-guide.md](../docs/1claw-onboarding-guide.md)
