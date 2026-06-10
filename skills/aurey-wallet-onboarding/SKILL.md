---
name: aurey-wallet-onboarding
description: >-
  Guides users through 1Claw and Aurey Wallet MCP on Hermes (aurey-setup),
  OpenClaw, or Cursor. Use when the user sets up Aurey, connects a wallet,
  onboards 1Claw, wires MCP, or asks how to use aurey-wallet-mcp.
---

# Aurey Wallet — onboarding (agent skill)

You help the user connect **Aurey Wallet MCP** with **1Claw Intents** custody. You do not handle private keys or API secrets in chat.

| Doc | Use |
|-----|-----|
| [Install site](https://agentic-pantheon.github.io/aurey-mcp/install.html) | curl / PyPI flow (default for users) |
| [llms.txt](https://agentic-pantheon.github.io/aurey-mcp/llms.txt) | Machine-oriented install spec |
| [install/hermes.md](../../install/hermes.md) | Hermes + **`aurey-setup`** (primary) |
| [docs/1claw-onboarding-guide.md](../../docs/1claw-onboarding-guide.md) | All hosts, manual 1Claw, troubleshooting |
| [ONBOARDING_1CLAW.md](../../ONBOARDING_1CLAW.md) | One-page reminder |

After MCP works, hand off to **[skills/aurey-wallet/SKILL.md](../aurey-wallet/SKILL.md)** for swaps and sends.

---

## Non-negotiables

1. **Never** ask in chat: private keys, mnemonics, **`1ck_`** (human), **`ocv_`** (agent), Alchemy, LiFi, or Zerion API keys.
2. **OK** in chat: repo path, vault/agent UUIDs (optional), smoke-test errors (redact secrets), tool JSON from `get_agent_wallet_addresses`.
3. **Hermes:** user runs **`aurey-setup`** (or `uv run aurey-setup` from a dev clone) in a **real terminal**—do not paste that command’s input from chat.
4. Prefer **curl install** or `pip install 'aurey-wallet-mcp[hermes]'`; do not `git clone` unless the user explicitly wants contributor mode.
5. Alchemy lives in **1Claw vault** `api-keys/alchemy` (see `~/.aurey/config.toml`); not Hermes MCP `env`.
6. **LiFi API key (optional):** stored at `api-keys/lifi` when set during `aurey-setup`; `lifi_api_secret_path` in `~/.aurey/config.toml`. Powers **LiFi Earn** vault discovery (`earn_list_vaults`, APY/TVL) and higher-rate LiFi quotes; basic swaps may work without it, but Earn (`earn.li.fi`) requires the key. User gets one via [LiFi Earn quickstart](https://docs.li.fi/earn/quickstart) ([Partner Portal signup](https://portal.li.fi/signup) → API key). User runs setup in terminal—do not ask for the key in chat.
7. **Zerion API key (optional):** stored at `api-keys/zerion` when set during `aurey-setup`; `zerion_api_secret_path` in `~/.aurey/config.toml`. Powers Telegram **Mini App** portfolio charts/balances; skip if the user does not use the Mini App. Get a key at [developers.zerion.io](https://developers.zerion.io/)—terminal only, not chat.
8. Never invent **`0x`** — use **`get_agent_wallet_addresses`** after MCP is connected.
9. No **`tx_execute`** during onboarding; verification is **read-only** only.

---

## Step 0 — Identify MCP host

| Host | Command |
|------|---------|
| **Install** | User terminal: `curl -fsSL https://agentic-pantheon.github.io/aurey-mcp/install.sh \| bash` |
| **Hermes** | `aurey-setup` (default) — [install/hermes.md](../../install/hermes.md) |
| **Cursor** | `aurey-setup --host cursor` — [install/cursor.md](../../install/cursor.md) |
| **Claude Desktop** | `aurey-setup --host claude` — [install/claude.md](../../install/claude.md) |
| **OpenClaw** | `aurey-setup --host openclaw` — [install/openclaw.md](../../install/openclaw.md) |

All hosts: same `1ck_…` + optional Alchemy + optional LiFi prompts; credentials in `~/.aurey/mcp.env` (never chat).

Re-wire MCP without re-provisioning: `aurey-setup --host <h> --skip-provision`.

Personal install = **one agent per MCP**. Multi-tenant Platform products → [Platform guide](https://docs.1claw.xyz/docs/guides/platform-api); defer to operator docs.

---

## Hermes path (recommended)

### Prerequisites (tell user)

1. [Hermes](https://hermes-agent.nousresearch.com/docs/) installed; model configured.
2. Hermes MCP extra: `cd ~/.hermes/hermes-agent && source venv/bin/activate && uv pip install -e ".[mcp]"`.
3. [1claw.xyz](https://1claw.xyz) account.
4. **Personal API key** `1ck_…` from 1Claw dashboard (API keys).
5. Package installed (`install.sh` or pip) on the Hermes machine—not required to clone the repo.
6. Optional: [Alchemy](https://www.alchemy.com/) key for balances.
7. Optional: [LiFi API key](https://docs.li.fi/earn/quickstart) for Earn vault discovery (and higher LiFi quote limits); Enter to skip at setup.

### Checklist (tick in chat)

```
Hermes + Aurey setup:
- [ ] User has 1ck_… ready (not pasted in chat)
- [ ] User ran install.sh or pip install, then aurey-setup --host <host> in terminal
- [ ] User reloaded MCP (Hermes: mcp test + /reload-mcp; Cursor/Claude: restart; OpenClaw: restart gateway)
- [ ] get_agent_wallet_addresses → ethereum + evm_source oneclaw_signing_keys
- [ ] Read-only balance on ethereum
- [ ] User loads aurey-wallet skill for trading
```

### What `aurey-setup` does (explain briefly)

Uses Human API with `1ck_…` to: pick or **create vault** (`aurey-wallet` if empty account), create **Intents agent**, policy on `api-keys/**`, optional Alchemy + optional LiFi secrets, **Ethereum signing key**, write `~/.hermes/.env` + `config.yaml`, set provider paths in `~/.aurey/config.toml`.

Flags user may need: `--vault-id`, `--skip-alchemy`, `--skip-lifi`, `--from-env` (`AUREY_ONECLAW_HUMAN_API_KEY`).

### Your role in chat

- Give the **exact terminal commands** from [install/hermes.md](../../install/hermes.md).
- Do **not** run interactive installers with secrets in the command line.
- After MCP is live: call **`get_agent_wallet_addresses`**; read `ethereum` and `evm_source` aloud.
- Suggest one **read-only** check (`evm_get_native_balance` on `ethereum`).
- When user wants swaps: switch to **aurey-wallet** skill.

### Starter user message (suggest)

```text
Help me install Aurey Wallet MCP on Hermes.
Repo: /path/to/aurey-wallet-mcp
I'll run aurey-setup in my terminal for 1ck_, Alchemy, and optional LiFi—I won't paste those keys here.
```

---

## Manual path (OpenClaw, Cursor, or existing 1Claw)

Walk [docs/1claw-onboarding-guide.md](../../docs/1claw-onboarding-guide.md) Path B **one step at a time**:

1. 1Claw account  
2. Vault UUID  
3. Agent + **Intents**  
4. `ocv_…` → host MCP env (`AUREY_ONECLAW_VAULT_API_KEY`) — user sets in UI/file, not chat  
5. **Ethereum** signing key (**blocker** if missing)  
6. Alchemy in vault `api-keys/alchemy` + read policy  
7. Optional LiFi in vault `api-keys/lifi` + `lifi_api_secret_path` in `~/.aurey/config.toml` ([Earn quickstart](https://docs.li.fi/earn/quickstart))  
8. MCP snippet from `install/openclaw.md` or `install/cursor.md`  
9. `get_agent_wallet_addresses`  

**Hermes manual:** `uv run aurey-hermes-install --prompt-secrets` instead of dashboard-heavy path if user already has UUIDs.

---

## 1Claw concepts (short answers)

| Topic | Answer |
|-------|--------|
| `1ck_` vs `ocv_` | Human provisions; agent runs MCP (`ocv_` in `~/.hermes/.env`) |
| Intents | Agent signs/broadcasts without raw private key in MCP |
| Wallet address | From signing keys API via `get_agent_wallet_addresses` |
| Vault auto-create | `aurey-setup` creates `aurey-wallet` only if account has **no** vaults |

---

## Troubleshooting (coach user to terminal)

| Symptom | Action |
|--------|--------|
| *no EVM wallet on agent* | Finish ETH signing key in 1Claw; `get_agent_wallet_addresses(refresh=true)` |
| *Bootstrap API key unavailable* | Fix `~/.hermes/.env` / MCP `env` |
| `aurey-setup` auth failed | New `1ck_` in dashboard |
| Balances fail | Alchemy at `api-keys/alchemy` + policy |
| `earn_list_vaults` HTTP 401 | Optional LiFi key at `api-keys/lifi` + `lifi_api_secret_path`; see [Earn quickstart](https://docs.li.fi/earn/quickstart) |
| `hermes mcp test` fails | [install/hermes.md](../../install/hermes.md) troubleshooting table |

---

## Phrases

- “Run `uv run aurey-setup` in your terminal—I won’t ask for your 1Claw keys here.”
- “Signing stays in 1Claw; I’ll use MCP tools only.”
- “I’ll read your address from `get_agent_wallet_addresses`, not from something you type.”

---

## Escalate

- 1Claw UI / Intents confusion → [Intents API](https://docs.1claw.xyz/docs/guides/intents-api), 1Claw support.  
- User wants zero server-side signing → explain Intents model vs air-gapped custody.
