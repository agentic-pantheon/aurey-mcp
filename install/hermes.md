# Hermes Agent — Aurey Wallet MCP

Install **Aurey Wallet MCP** on [Hermes](https://hermes-agent.nousresearch.com/docs/) so your agent can read EVM balances, prepare swaps, and sign via **1Claw Intents** (no private keys in chat or MCP env).

**How this doc is used:** humans follow the steps; **agents** load [skills/aurey-wallet-onboarding/SKILL.md](../skills/aurey-wallet-onboarding/SKILL.md) and use this file as the Hermes-specific reference.

---

## What you are building

```text
You (human)          1Claw                    Hermes + Aurey MCP
    │                  │                              │
    │  1ck_… (once)    │  vault + agent + ocv_…       │
    ├─────────────────►│  Intents + ETH signing key   │
    │  (terminal)      │  Alchemy in vault (optional)   │
    │                  │                              │
    │                  │◄──── agent JWT + Intents ──────┤ wallet tools
    │                  │                              │
```

- **Human key (`1ck_…`)** — creates/configures 1Claw (one-time, terminal only).
- **Agent key (`ocv_…`)** — what Aurey MCP uses at runtime (written to `~/.hermes/.env`, never chat).
- **Wallet address** — comes from 1Claw signing keys; fetch with `get_agent_wallet_addresses`, do not type `0x` manually.

Official 1Claw docs: [docs.1claw.xyz](https://docs.1claw.xyz).

---

## Secrets: what goes where

| Secret / ID | Paste in Hermes chat? | Where it lives |
|-------------|----------------------|----------------|
| 1Claw **human** API key (`1ck_…`) | **No** | `aurey-setup` terminal prompt only |
| Vault UUID | **Yes** (optional) | `~/.hermes/.env` → `AUREY_ONECLAW_VAULT_ID` |
| Agent UUID | **Yes** (optional) | `~/.hermes/.env` → `AUREY_ONECLAW_AGENT_ID` |
| Agent API key (`ocv_…`) | **No** | `~/.hermes/.env` → `AUREY_ONECLAW_VAULT_API_KEY` |
| Alchemy API key | **No** | 1Claw vault path `api-keys/alchemy` (not MCP `env`) |
| Zerion API key (optional) | **No** | 1Claw vault path `api-keys/zerion` (portfolio UI / Mini App) |

Hermes may retain chat in memory and logs. **Never** ask the user to paste `1ck_`, `ocv_`, Alchemy, or Zerion keys in chat. **Never** pipe chat text into `aurey-setup` or `aurey-hermes-install --prompt-secrets`.

**Naming:** `AUREY_ONECLAW_VAULT_API_KEY` is the per-agent **`ocv_…`** key (agent-token + vault reads). Legacy alias: `AUREY_ONECLAW_BOOTSTRAP_API_KEY`. Not `plt_` (Platform).

**Built-in defaults** (omit from MCP `env`): `AUREY_HOSTED_PLATFORM_ENABLED=false`, `AUREY_EVM_SIGNING_MODE=oneclaw_intents`.

---

## Prerequisites

1. **Hermes** installed and a model configured (`hermes setup` / `hermes model`).
2. **Hermes MCP extra** (once):

   ```bash
   cd ~/.hermes/hermes-agent && source venv/bin/activate && uv pip install -e ".[mcp]"
   ```

   Hermes uses `venv/`, not `.venv/`.

3. **1Claw account** at [1claw.xyz](https://1claw.xyz) with a **personal API key** (`1ck_…`): dashboard → API keys → create (or [Human API](https://docs.1claw.xyz/docs/human-api/authentication)).
4. **Aurey Wallet MCP** installed on the Hermes machine (PyPI/curl—no clone required). See [install site](https://agentic-pantheon.github.io/aurey-mcp/install.html).
5. **[Alchemy](https://www.alchemy.com/)** API key (optional at setup; needed for balances/portfolio reads).

**Skills** (load in Hermes so the agent can guide you):

- `skills/aurey-wallet-onboarding/SKILL.md` — setup
- `skills/aurey-wallet/SKILL.md` — swaps/sends after MCP is live

Index: [SKILL.md](../SKILL.md).

---

## Recommended: one-command setup (`aurey-setup`)

Run in **your terminal** (not Hermes chat). Default host is Hermes; same command works for Cursor, Claude Desktop, and OpenClaw with `--host`.

**Install package** (once):

```bash
curl -fsSL https://agentic-pantheon.github.io/aurey-mcp/install.sh | bash
# or: pip install 'aurey-wallet-mcp[hermes]'
```

**Configure** (masked prompts):

```bash
aurey-setup                  # Hermes (default)
aurey-setup --host cursor    # ~/.cursor/mcp.json
aurey-setup --host claude    # Claude Desktop config
aurey-setup --host openclaw  # ~/.openclaw/openclaw.json (or OPENCLAW_CONFIG)
```

**Contributors** from a git clone: `uv sync --group dev --extra hermes` then `uv run aurey-setup …`.

**Prompts (masked):**

1. **1Claw human API key** (`1ck_…`)
2. **Alchemy API key** (Enter to skip; stored in 1Claw if provided)
3. **LiFi API key** (optional; Enter to skip) — Earn vault discovery + higher LiFi quote limits; see [Earn quickstart](https://docs.li.fi/earn/quickstart) / [portal.li.fi/signup](https://portal.li.fi/signup)
4. **Zerion API key** (optional; Enter to skip) — local portfolio UI at `http://127.0.0.1:8765/` and Telegram Mini App live data; see [developers.zerion.io](https://developers.zerion.io/)

**What `aurey-setup` does automatically:**

| Step | 1Claw / local action |
|------|----------------------|
| Auth | Human API with your `1ck_…` |
| Vault | Uses `--vault-id` if set; else picks existing vault (prefers name `aurey-wallet`, or your only vault); **creates** vault `aurey-wallet` if you have none |
| Agent | Creates **Aurey Wallet MCP** agent with `intents_api_enabled: true`; returns one-time `ocv_…` |
| Policy | Grants agent **read** on `api-keys/**` |
| Alchemy | `PUT` secret at `api-keys/alchemy` when you entered a key |
| LiFi | `PUT` secret at `api-keys/lifi` when you entered a key; sets `lifi_api_secret_path` in `~/.aurey/config.toml` |
| Zerion | `PUT` secret at `api-keys/zerion` when you entered a key; sets `zerion_api_secret_path` in `~/.aurey/config.toml` |
| Signing key | Provisions **Ethereum** signing key on the agent |
| Hermes | Writes `~/.hermes/.env`, patches `~/.hermes/config.yaml` |
| All hosts | Writes `~/.aurey/mcp.env` (chmod 600) + wrapper `~/.aurey/run-aurey-wallet-mcp.sh` |
| Cursor / Claude / OpenClaw | MCP config points at the **wrapper** (secrets stay out of JSON) |
| `~/.aurey/config.toml` | `alchemy_secret_path`; `lifi_api_secret_path` / `zerion_api_secret_path` when keys provided |
| Verify | Optional MCP bootstrap smoke test |

**Useful flags:**

```bash
uv run aurey-setup --vault-id '<existing-vault-uuid>'   # do not create/pick another vault
uv run aurey-setup --skip-alchemy                     # add Alchemy in dashboard later
uv run aurey-setup --skip-lifi                        # skip LiFi prompt (Earn vault list needs key later)
uv run aurey-setup --skip-zerion                      # skip Zerion prompt (portfolio UI needs key later)
uv run aurey-setup --zerion-key '<key>'               # non-interactive Zerion key
uv run aurey-setup --zerion-vault-path api-keys/zerion  # custom 1Claw vault path
uv run aurey-setup --from-env                         # human key in AUREY_ONECLAW_HUMAN_API_KEY
uv run aurey-setup --provision-only                   # 1Claw + ~/.aurey/mcp.env only
uv run aurey-setup --host cursor --skip-provision     # Re-wire MCP using saved mcp.env
uv run aurey-setup --host cursor --cursor-project .   # Project .cursor/mcp.json
uv run aurey-setup --config /path/to/mcp.json         # Override config file path
```

After success:

```bash
hermes mcp test aurey-wallet
```

In Hermes chat: `/reload-mcp`, then ask the agent to call `get_agent_wallet_addresses`.

---

## Agent-guided flow (chat + terminal)

Use this when the user starts in Hermes chat and you (the agent) coach them.

### 1 — Open with a safe prompt (user)

```text
Help me install Aurey Wallet MCP on Hermes.
Repo: /path/to/aurey-wallet-mcp
I will run aurey-setup in my terminal for 1ck_ and Alchemy.
I will NOT paste 1ck_, ocv_, or Alchemy in this chat.
```

### 2 — Agent checklist (copy in chat)

```text
Setup:
- [ ] Hermes + MCP extra installed
- [ ] 1Claw account + human API key (1ck_…) ready
- [ ] User ran: uv sync --group dev --extra hermes && uv run aurey-setup
- [ ] hermes mcp test aurey-wallet OK
- [ ] /reload-mcp
- [ ] get_agent_wallet_addresses → ethereum + evm_source oneclaw_signing_keys
- [ ] Read-only balance test (no tx_execute yet)
- [ ] User loaded skills/aurey-wallet/SKILL.md
```

### 3 — What the agent does in chat

- Explain **one terminal command** (`aurey-setup`); do not request secrets.
- Answer questions about 1Claw (vault, Intents, signing keys) using [docs/1claw-onboarding-guide.md](../docs/1claw-onboarding-guide.md).
- After MCP is up: call **`get_agent_wallet_addresses`**; read back `ethereum` and `evm_source`.
- First live action: **read-only** (e.g. native balance on `ethereum`).
- **No `tx_execute`** during onboarding.

### 4 — What the user does in terminal only

- `uv run aurey-setup` (or manual path below).
- `hermes mcp test aurey-wallet`
- Fix `~/.hermes/.env` if smoke test fails (never paste fixes into chat).

---

## Manual path (dashboard 1Claw + `aurey-hermes-install`)

Use if you already created vault/agent in the [1Claw dashboard](https://1claw.xyz) or need fine-grained control.

**1Claw (dashboard):**

1. Vault → copy vault UUID.
2. Agent with **Intents API** enabled → copy agent UUID.
3. Create / rotate agent API key → `ocv_…` (shown once).
4. Provision **Ethereum** signing key on that agent.
5. Store **Alchemy** at `api-keys/alchemy`; policy allowing agent read on `api-keys/**`.

**Hermes (terminal):**

```bash
cd /path/to/aurey-wallet-mcp
uv sync --group dev --extra hermes
uv run aurey-hermes-install --repo "$(pwd)" --prompt-secrets
```

Type vault UUID, agent UUID, and masked `ocv_` in the terminal.

Or UUIDs from chat + secrets in shell:

```bash
export AUREY_ONECLAW_VAULT_API_KEY='ocv_...'
uv run aurey-hermes-install --repo "$(pwd)" \
  --vault-id '<vault-uuid>' \
  --agent-id '<agent-uuid>' \
  --from-env
```

---

## What gets written on disk

| File | Purpose |
|------|---------|
| `~/.hermes/config.yaml` | `mcp_servers.aurey-wallet` → `<repo>/.venv/bin/aurey-wallet-mcp` with `${AUREY_*}` env |
| `~/.hermes/.env` | `AUREY_ONECLAW_VAULT_ID`, `AUREY_ONECLAW_AGENT_ID`, `AUREY_ONECLAW_VAULT_API_KEY` |
| `~/.aurey/config.toml` | `[providers] alchemy_secret_path = "api-keys/alchemy"` |

Do **not** use `hermes mcp add` with `uv run --directory …` — Hermes CLI misparses `--directory`. The installer uses the venv binary path.

**Manual `config.yaml` snippet:**

```yaml
mcp_servers:
  aurey-wallet:
    enabled: true
    command: /path/to/aurey-wallet-mcp/.venv/bin/aurey-wallet-mcp
    env:
      AUREY_ONECLAW_VAULT_ID: ${AUREY_ONECLAW_VAULT_ID}
      AUREY_ONECLAW_VAULT_API_KEY: ${AUREY_ONECLAW_VAULT_API_KEY}
      AUREY_ONECLAW_AGENT_ID: ${AUREY_ONECLAW_AGENT_ID}
```

---

## Verify and first use

**Terminal:**

```bash
hermes mcp test aurey-wallet
```

**Chat:**

```text
/reload-mcp
```

```text
Call get_agent_wallet_addresses and show my ethereum address and evm_source.
Then evm_get_native_balance for ethereum using that address.
```

When the user wants to swap or send, follow [skills/aurey-wallet/SKILL.md](../skills/aurey-wallet/SKILL.md): **prepare → show summary → explicit confirm → `tx_execute(prepared_id=…)`**.

---

## Using Aurey after setup

| User intent | Agent flow |
|-------------|------------|
| Wallet address | `get_agent_wallet_addresses` ( `refresh: true` if just finished 1Claw ) |
| Balance / portfolio | Address from above → read tools (`evm_get_native_balance`, portfolio tools) |
| Swap | `get_agent_wallet_addresses` → `swap_prepare` → confirm → `tx_prepare_lifi` → confirm → `tx_execute` |
| Send ERC-20 | Prepare transfer tools → confirm → `tx_execute` |

Signing stays in **1Claw Intents**; the model never sees the private key.

Optional: `AUREY_ROUTE_BUILDER_URL` in MCP `env` for hosted swap quotes — see [docs/setup.md](../docs/setup.md).

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|--------|----------------|-----|
| `aurey-setup`: auth / exchange failed | Wrong or expired `1ck_` | New personal API key in 1Claw dashboard |
| MCP: *no EVM wallet on agent* | No Ethereum signing key | Re-run provisioning or dashboard: signing keys → ethereum; then `get_agent_wallet_addresses(refresh=true)` |
| MCP: *Bootstrap API key unavailable* | `.env` not loaded | Check `~/.hermes/.env` and `${VAR}` in `config.yaml` |
| `hermes mcp test` connection closed | Bad `ocv_` or agent id | Rotate agent key in 1Claw; update `.env` via `aurey-hermes-install --prompt-secrets` |
| Balances fail / *scopes do not cover this secret path* | Vault policy OK but agent JWT scopes too narrow (`vaults:read` only) | In 1Claw: edit agent → clear fixed scopes (use policy-derived scopes) or create a new agent via latest `aurey-setup`; policy `api-keys/**` read |
| Balances fail | No Alchemy at `api-keys/alchemy` | Add secret in 1Claw; policy `api-keys/**` read |
| Swaps fail routing | No LiFi / route builder | `AUREY_ROUTE_BUILDER_URL` or LiFi key per [setup.md](../docs/setup.md) |
| Agent invents `0x` | Skipped wallet tool | Enforce `get_agent_wallet_addresses` |

---

## Agent rules (operators / skills)

1. **Hermes default:** direct user to `uv run aurey-setup` in terminal; never collect `1ck_` / `ocv_` / Alchemy in chat.
2. Chat is OK for: repo path, errors (redact secrets), vault/agent UUIDs after setup, verification tool output.
3. Do not run interactive installers with secrets embedded in agent-run command strings.
4. After install: `/reload-mcp` → `get_agent_wallet_addresses` → read-only check.
5. Load **both** onboarding and operations skills ([SKILL.md](../SKILL.md)).

---

## Related

- [docs/1claw-onboarding-guide.md](../docs/1claw-onboarding-guide.md) — all hosts, manual 1Claw, Platform note
- [docs/setup.md](../docs/setup.md) — route builder, dashboard, autonomy
- [install/openclaw.md](openclaw.md) / [install/cursor.md](cursor.md) — non-Hermes MCP hosts
- [ONBOARDING_1CLAW.md](../ONBOARDING_1CLAW.md) — one-page agent playbook

Telegram/Discord/Slack use the Hermes gateway; Aurey only adds wallet MCP tools on the machine running Hermes.
