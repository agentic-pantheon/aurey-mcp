# 1Claw + Aurey Wallet — onboarding guide

For **people** setting up Aurey and **agents** helping on Hermes, OpenClaw, or Cursor. Official 1Claw: [docs.1claw.xyz](https://docs.1claw.xyz).

Aurey does **not** ask for a wallet address up front. Your **1Claw agent** gets an Ethereum signing key; use **`get_agent_wallet_addresses`** after MCP is running.

---

## One sentence

A **1Claw vault + Intents agent + Ethereum signing key + MCP config** so Aurey can read chain data (Alchemy via vault) and sign via Intents—without secrets in chat.

---

## Choose a path

| Path | Best for | Doc |
|------|----------|-----|
| **A — `aurey-setup`** | All MCP hosts; one `1ck_…` in terminal | [install/hermes.md](../install/hermes.md) (`--host`) |
| **B — Manual dashboard** | Existing 1Claw resources only | Steps below |
| **C — Platform / hosted product** | One agent per end user (operators) | [Platform API](https://docs.1claw.xyz/docs/guides/platform-api) |

---

## Path A — Super-easy (`aurey-setup`, any host)

**User (terminal only):**

```bash
cd /path/to/aurey-wallet-mcp
uv sync --group dev --extra hermes   # hermes only: needs PyYAML for config.yaml
uv run aurey-setup --host <hermes|cursor|claude|openclaw>
```

| `--host` | Install doc |
|----------|-------------|
| `hermes` (default) | [install/hermes.md](../install/hermes.md) |
| `cursor` | [install/cursor.md](../install/cursor.md) |
| `claude` | [install/claude.md](../install/claude.md) |
| `openclaw` | [install/openclaw.md](../install/openclaw.md) |

Shared artifacts: `~/.aurey/mcp.env`, `~/.aurey/run-aurey-wallet-mcp.sh`, `~/.aurey/config.toml`.

1. Create a [1Claw](https://1claw.xyz) account if needed.
2. Create a **personal API key** (`1ck_…`) in the dashboard.
3. At prompts: paste `1ck_…`; optionally Alchemy; optionally **LiFi API key** (Enter to skip).

**Provisioner behavior:**

- **Vault:** create `aurey-wallet` if you have no vaults; otherwise reuse (see [hermes.md](../install/hermes.md)).
- **Agent:** new Intents agent **Aurey Wallet MCP** + `ocv_…` (stored in `~/.hermes/.env`).
- **Policy:** agent read on `api-keys/**`.
- **Signing key:** Ethereum on that agent.
- **LiFi (optional):** stores API key at `api-keys/lifi` and sets `lifi_api_secret_path` in `~/.aurey/config.toml` when provided.

**LiFi key — optional:** By default, swaps, Composer deposits, and Earn vault tools use the hosted **aurey-route-builder** (no personal LiFi key). You only need your own key if you opt out with `AUREY_ROUTE_BUILDER_URL=` empty (direct `li.quest` + `earn.li.fi`). **How to get one:** [LiFi Earn quickstart](https://docs.li.fi/earn/quickstart) — [portal.li.fi/signup](https://portal.li.fi/signup). Paste at `aurey-setup` (terminal only) or store at `api-keys/lifi` in 1Claw.

Then reload MCP for your host (Hermes: `hermes mcp test aurey-wallet` + `/reload-mcp`; Cursor/Claude: restart app; OpenClaw: restart gateway) → `get_agent_wallet_addresses`.

**Agent coaching:** [skills/aurey-wallet-onboarding/SKILL.md](../skills/aurey-wallet-onboarding/SKILL.md) + [install/hermes.md](../install/hermes.md).

---

## Path B — Manual checklist (any MCP host)

### Step 1 — 1Claw account

[1claw.xyz](https://1claw.xyz) — sign up / log in.

**Done when:** dashboard loads.

### Step 2 — Vault

Create a vault; save **vault UUID** → `AUREY_ONECLAW_VAULT_ID`.

### Step 3 — Agent + Intents

Create an agent; enable **Intents API** ([guide](https://docs.1claw.xyz/docs/guides/intents-api)). Save **agent UUID** → `AUREY_ONECLAW_AGENT_ID`.

### Step 4 — Agent API key

Create agent API key (`ocv_…`, shown once) → `AUREY_ONECLAW_VAULT_API_KEY` in MCP host env (**not chat**). Legacy name: `AUREY_ONECLAW_BOOTSTRAP_API_KEY`.

### Step 5 — Ethereum signing key (**blocker**)

Provision **ethereum** signing key on that agent (dashboard or `POST /v1/agents/{id}/signing-keys`).

**If skipped:** MCP fails with *no EVM wallet on agent yet*.

### Step 6 — Alchemy (reads)

Preferred: store in vault at **`api-keys/alchemy`**; set `alchemy_secret_path` in `~/.aurey/config.toml`. Grant agent **read** policy on `api-keys/**`.

Optional: `AUREY_ALCHEMY_API_KEY` in env (not recommended on Hermes).

### Step 6b — LiFi API key (optional)

**For:** LiFi Earn vault discovery and portfolio reads (`earn_list_vaults`, etc.) and higher LiFi quote rate limits. **Not required** for basic onboarding or read-only wallet checks; **required** for Earn API calls (see [Earn quickstart](https://docs.li.fi/earn/quickstart)).

Preferred: store in vault at **`api-keys/lifi`**; set `lifi_api_secret_path = "api-keys/lifi"` under `[providers]` in `~/.aurey/config.toml` ( `aurey-setup` does this when you enter a key). Same `api-keys/**` read policy as Alchemy.

Get a key: [portal.li.fi/signup](https://portal.li.fi/signup) → API keys (documented in [Earn quickstart](https://docs.li.fi/earn/quickstart)).

Optional env alternative: `AUREY_LIFI_API_KEY` (avoid on shared hosts; vault path is preferred).

### Step 7 — Aurey MCP on host

**Hermes:** `uv run aurey-hermes-install --prompt-secrets` — see [install/hermes.md](../install/hermes.md).

**OpenClaw:** [install/openclaw.md](../install/openclaw.md).

**Cursor:** [install/cursor.md](../install/cursor.md).

Required env (signing mode and hosted flag are defaults in this repo):

- `AUREY_ONECLAW_VAULT_ID`
- `AUREY_ONECLAW_VAULT_API_KEY` (`ocv_…`)
- `AUREY_ONECLAW_AGENT_ID`

### Step 8 — Verify

`get_agent_wallet_addresses` → `ethereum` + `evm_source` = `oneclaw_signing_keys`. Use `refresh: true` if you just provisioned keys.

### Step 9 — Skills

Load [skills/aurey-wallet-onboarding/SKILL.md](../skills/aurey-wallet-onboarding/SKILL.md) and [skills/aurey-wallet/SKILL.md](../skills/aurey-wallet/SKILL.md) ([SKILL.md](../SKILL.md)).

---

## Path C — Platform (teams)

For products that provision **one agent per user**: Platform app, templates, claim URLs — see [Platform API](https://docs.1claw.xyz/docs/guides/platform-api). This repo’s default install is **one agent per MCP instance** (`AUREY_HOSTED_PLATFORM_ENABLED=false`).

---

## Key types (1Claw)

| Prefix | Role | Aurey setup |
|--------|------|-------------|
| `1ck_` | Human personal API key | **`aurey-setup` only** (terminal); not persisted in `mcp.env` |
| `ocv_` | Agent API key | MCP runtime (`~/.hermes/.env` or host `env`) |
| `plt_` | Platform operator | Not used in personal Hermes install |

---

## Instructions for the agent

When the user asks to **set up Aurey**, **connect 1Claw**, or **install wallet MCP**:

### Safety

- **Never** ask for private keys, mnemonics, `1ck_`, `ocv_`, Alchemy, or LiFi API keys in chat.
- UUIDs and tool output in chat are fine.
- Never invent `0x` addresses.

### Flow (Hermes)

1. Confirm Hermes + repo path.
2. Tell user to run **`uv run aurey-setup`** in terminal (link [install/hermes.md](../install/hermes.md)).
3. User runs `hermes mcp test aurey-wallet`; you help interpret errors (no secrets).
4. `/reload-mcp` → **`get_agent_wallet_addresses`** → read-only balance.
5. Point to **`aurey-wallet`** skill for swaps/sends (prepare → confirm → execute).

### Flow (manual / OpenClaw / Cursor)

Walk Path B steps one at a time; host-specific MCP snippet from `install/`.

### Tools during onboarding

| Question | Action |
|----------|--------|
| “What’s my address?” | `get_agent_wallet_addresses` |
| “Is 1Claw ready?” | `get_agent_wallet_addresses(refresh=true)` |
| “My balance?” | After address: `evm_get_native_balance` / portfolio |
| “Swap now” | Only after setup: prepare flow + **explicit confirmation** |

### Phrases

- “Your signing key stays in 1Claw; I only call MCP tools.”
- “Run `aurey-setup` in your terminal for the 1Claw human key—I won’t ask for it here.”
- “I’ll fetch your address with a tool after MCP is connected.”

### Escalate

- Intents / signing UI unclear → [Intents API](https://docs.1claw.xyz/docs/guides/intents-api), 1Claw support.
- MCP won’t start → fix **host env** / `.env`, not chat.

---

## Troubleshooting

| Symptom | What to do |
|--------|------------|
| *no EVM wallet on agent* | Finish Step 5 / re-provision ETH key; `get_agent_wallet_addresses(refresh=true)` |
| *requires oneclaw_intents* | Default in repo; set `AUREY_EVM_SIGNING_MODE=oneclaw_intents` if overridden |
| *Bootstrap API key unavailable* | MCP subprocess `env` / `~/.hermes/.env` |
| Balances fail | Alchemy at `api-keys/alchemy` + policy |
| Swaps fail | `AUREY_ROUTE_BUILDER_URL` or LiFi — [setup.md](setup.md) |
| Wrong `from_address` | Call `get_agent_wallet_addresses` first |

---

## Env quick reference

| Variable | Purpose |
|----------|---------|
| `AUREY_ONECLAW_VAULT_ID` | Vault UUID |
| `AUREY_ONECLAW_VAULT_API_KEY` | Agent `ocv_…` (legacy: `AUREY_ONECLAW_BOOTSTRAP_API_KEY`) |
| `AUREY_ONECLAW_AGENT_ID` | Agent UUID (Intents on) |
| `AUREY_ONECLAW_HUMAN_API_KEY` | Setup only (`aurey-setup --from-env` or shell for one run); **never** in `mcp.env` / MCP env — unset after provision |
| `AUREY_ROUTE_BUILDER_URL` | Default hosted swap quotes (25 bps fee); set empty to opt out — [setup.md](setup.md) |

Optional override: `AUREY_DEEP_AGENT_WALLET_ADDRESS`.

---

## Related

- [setup.md](setup.md) — route builder, dashboard  
- [install/hermes.md](../install/hermes.md) — Hermes + `aurey-setup`  
- [ONBOARDING_1CLAW.md](../ONBOARDING_1CLAW.md) — short agent playbook  
