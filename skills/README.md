# Agent skills (Hermes, OpenClaw, Cursor)

These skills teach an agent how to **onboard users** (1Claw + MCP) and **use wallet tools** safely.

## Load into your host

| Host | What to do |
|------|------------|
| **Hermes** | Skills + `uv run aurey-setup` — [install/hermes.md](../install/hermes.md) |
| **Cursor** | Skills + `uv run aurey-setup --host cursor` — [install/cursor.md](../install/cursor.md) |
| **Claude Desktop** | `uv run aurey-setup --host claude` — [install/claude.md](../install/claude.md) |
| **OpenClaw** | Skills + `uv run aurey-setup --host openclaw`; channel allowlists |

```bash
mkdir -p .cursor/skills
ln -sf ../../skills/aurey-wallet-onboarding .cursor/skills/aurey-wallet-onboarding
ln -sf ../../skills/aurey-wallet .cursor/skills/aurey-wallet
```

## Skills

1. **`aurey-wallet-onboarding`** — Hermes `aurey-setup`, manual 1Claw, host-specific MCP, verification, troubleshooting.
2. **`aurey-wallet`** — `get_agent_wallet_addresses`; prepare → confirm → `tx_execute`; swaps.

Root [SKILL.md](../SKILL.md) is the index.

## Docs map

| Audience | Doc |
|----------|-----|
| Hermes install | [install/hermes.md](../install/hermes.md) |
| Full 1Claw + Aurey | [docs/1claw-onboarding-guide.md](../docs/1claw-onboarding-guide.md) |
| Short agent playbook | [ONBOARDING_1CLAW.md](../ONBOARDING_1CLAW.md) |
| Route builder / dashboard | [docs/setup.md](../docs/setup.md) |
