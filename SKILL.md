---
name: aurey-wallet-mcp
description: >-
  Entry point for Aurey Wallet MCP in Hermes, OpenClaw, or Cursor. Load
  aurey-wallet-onboarding for 1Claw + MCP setup (Hermes: aurey-setup) and
  aurey-wallet for day-to-day EVM tools.
---

# Aurey Wallet MCP — skills index

Load **both** skills from this repo into your agent host:

| Skill | Path | When |
|-------|------|------|
| **Onboarding** | [skills/aurey-wallet-onboarding/SKILL.md](skills/aurey-wallet-onboarding/SKILL.md) | First-time 1Claw + MCP (guide user; Hermes: `aurey-setup` in terminal) |
| **Operations** | [skills/aurey-wallet/SKILL.md](skills/aurey-wallet/SKILL.md) | Balances, swaps, sends after MCP is live |

## Quick start (Hermes)

User terminal (not chat):

```bash
cd /path/to/aurey-wallet-mcp
uv sync --group dev
uv run aurey-setup --host hermes   # or cursor | claude | openclaw
```

Details: [install/hermes.md](install/hermes.md) · [cursor](install/cursor.md) · [claude](install/claude.md) · [openclaw](install/openclaw.md).

## Docs

| Doc | Purpose |
|-----|---------|
| [install/hermes.md](install/hermes.md) | Hermes MCP + `aurey-setup` + using Aurey |
| [docs/1claw-onboarding-guide.md](docs/1claw-onboarding-guide.md) | All hosts, manual 1Claw, agent instructions |
| [docs/setup.md](docs/setup.md) | Env reference, route builder, dashboard |
| [ONBOARDING_1CLAW.md](ONBOARDING_1CLAW.md) | One-page agent playbook |
| [install/cursor.md](install/cursor.md) / [install/claude.md](install/claude.md) / [install/openclaw.md](install/openclaw.md) | Same `aurey-setup`, different `--host` |

**Cursor:** [skills/README.md](skills/README.md) for symlinks.
