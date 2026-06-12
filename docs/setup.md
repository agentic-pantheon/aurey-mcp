# Setup — Aurey Wallet MCP

Wallet addresses come from your **1Claw agent** (Intents signing keys). Do not paste a primary `0x` unless you override with `AUREY_DEEP_AGENT_WALLET_ADDRESS`.

---

## Onboarding paths

| Path | Command / doc |
|------|----------------|
| **All hosts** | `uv run aurey-setup --host <hermes\|cursor\|claude\|openclaw>` — [install/hermes.md](../install/hermes.md) |
| **Manual 1Claw + any host** | [1claw-onboarding-guide.md](1claw-onboarding-guide.md) |
| **Agent playbook** | [ONBOARDING_1CLAW.md](../ONBOARDING_1CLAW.md), [skills/aurey-wallet-onboarding/SKILL.md](../skills/aurey-wallet-onboarding/SKILL.md) |

---

## What `aurey-setup` provisions (1Claw)

Using a **human** API key (`1ck_…`, terminal only):

1. Authenticates to [api.1claw.xyz](https://api.1claw.xyz) (Human API).
2. **Vault** — uses `--vault-id` or picks/creates (see [hermes.md](../install/hermes.md)).
3. **Agent** — `Aurey Wallet MCP`, Intents enabled, returns **`ocv_…`** (written to `~/.hermes/.env` on Hermes).
4. **Policy** — agent read on `api-keys/**`.
5. **Alchemy** — optional store at `api-keys/alchemy`.
6. **LiFi** — optional store at `api-keys/lifi` (only if you disable the hosted route-builder; see below).
7. **Signing key** — Ethereum on the agent.
8. **Host MCP config** — Hermes `~/.hermes/*`; Cursor `mcp.json`; Claude desktop config; OpenClaw `openclaw.json`.
9. **Shared** — `~/.aurey/mcp.env`, wrapper `~/.aurey/run-aurey-wallet-mcp.sh`, `~/.aurey/config.toml`.

CLI: `aurey-setup` · Provision-only module: `oneclaw_provision.py`.

---

## Runtime env (personal MCP)

Required in MCP host env (or `~/.hermes/.env` on Hermes):

| Variable | Value |
|----------|--------|
| `AUREY_ONECLAW_VAULT_ID` | Vault UUID |
| `AUREY_ONECLAW_VAULT_API_KEY` | Agent `ocv_…` (legacy: `AUREY_ONECLAW_BOOTSTRAP_API_KEY`) |
| `AUREY_ONECLAW_AGENT_ID` | Agent UUID |

**Defaults in this package** (no env needed): `hosted_platform_enabled=false`, `evm_signing_mode=oneclaw_intents`.

**Alchemy (preferred):** `alchemy_secret_path = "api-keys/alchemy"` in `~/.aurey/config.toml` with key in 1Claw vault. Optional plaintext: `AUREY_ALCHEMY_API_KEY` (avoid on Hermes).

**LiFi (optional):** Not required when using the default hosted [aurey-route-builder](https://github.com/agentic-pantheon/aurey-route-builder) (swaps, Composer quotes, and Earn Data API). Set `AUREY_ROUTE_BUILDER_URL=` empty to call LiFi and `earn.li.fi` directly — then configure `lifi_api_secret_path = "api-keys/lifi"` or `AUREY_LIFI_API_KEY` ([Earn quickstart](https://docs.li.fi/earn/quickstart)).

On MCP start, the plugin loads the agent’s Ethereum address from signing-keys. Failure → finish 1Claw ETH key provisioning.

Tool: **`get_agent_wallet_addresses`** (`refresh=true` after provisioning without restart).

Optional: `AUREY_DEEP_AGENT_WALLET_ADDRESS`. Default swap routing uses `AUREY_ROUTE_BUILDER_URL` (hosted route-builder, 25 bps fee); set empty to opt out — see [Route builder](#route-builder-hosted-swaps).

**LiFi token catalog:** MCP ships `aurey/data/lifi_tokens/{chain_id}.json` shards (LiFi `/v1/tokens`, Aurey EVM chains). **Per-chain lazy load:** only the chain you query is read and indexed (plus small curated `known_addresses.json` at startup). No Postgres; catalog is not sent to the model. Override path: `AUREY_LIFI_TOKENS_PATH`. Disable bundled file: `AUREY_BUNDLED_LIFI_TOKENS_ENABLED=false`.

Maintainers refresh the bundle:

```bash
uv run python scripts/sync_bundled_lifi_tokens.py --from-file /path/to/li_quest_tokens.json
# or: uv run python scripts/sync_bundled_lifi_tokens.py --fetch
```

Agents: `resolve_known_address` per ticker; `list_supported_tokens` requires `chain` (capped page).

---

## Host install docs

- [Hermes](../install/hermes.md) — `aurey-setup --host hermes`
- [Cursor](../install/cursor.md) — `--host cursor`
- [Claude](../install/claude.md) — `--host claude`
- [OpenClaw](../install/openclaw.md) — `--host openclaw`

---

## Route builder (hosted swaps + Earn)

Swap quotes and **Earn Data API** reads use the hosted [aurey-route-builder](https://github.com/agentic-pantheon/aurey-route-builder) by default. Swaps include a **25 bps** integrator fee (disclosed in quote responses). Signing stays on your device via 1Claw.

```bash
# Opt out — quote LiFi and earn.li.fi directly (requires your own LiFi key for Earn)
export AUREY_ROUTE_BUILDER_URL=
```

Optional bearer for higher rate limits:

```bash
export AUREY_ROUTE_BUILDER_API_KEY=...
```

Self-host the route-builder: see the repo README and [docs/DEPLOY.md](https://github.com/agentic-pantheon/aurey-route-builder/blob/main/docs/DEPLOY.md).

---

## Local portfolio UI (agent, no Telegram)

`aurey-setup` sets `[dashboard] enabled = true` in `~/.aurey/config.toml` by default (`--skip-portfolio-ui` to opt out). While MCP runs:

- Open **http://127.0.0.1:8765/** (also logged at MCP startup).
- MCP tool **`get_local_portfolio_url`** returns the same URL and readiness flags.
- Optional **`AUREY_DASHBOARD_AUTH_TOKEN`** — if set, open `http://127.0.0.1:8765/?token=…` once.

**Zerion (optional):** live charts need `zerion_api_secret_path` / vault `api-keys/zerion` or `AUREY_ZERION_API_KEY`. Without it, the UI loads but shows a setup banner.

PyPI wheels ship prebuilt static assets. Dev clone: `uv run python scripts/build_portfolio_static.py`.

**Test without Hermes:** the UI listens only while MCP is running. For a dedicated server:

```bash
set -a && source ~/.aurey/mcp.env && set +a
uv run aurey-portfolio-serve
```

Then `curl http://127.0.0.1:8765/health` and open http://127.0.0.1:8765/.

**LAN / another device:** set `host = "0.0.0.0"` under `[dashboard]` in `~/.aurey/config.toml`, reload MCP, open `http://<your-machine-ip>:8765/`. Use `auth_token` when not on loopback.

---

## Paid HTTP APIs (x402, optional)

When **1Claw typed-data signing** is enabled on the agent key, MCP exposes wallet-backed **x402 V2** tools: `x402_preview`, `x402_fetch`, `x402_payment_status`, `x402_batch_channel_status`, `x402_batch_refund`.

Configure caps in `~/.aurey/config.toml` under `[x402]` (see `config.example.toml`) or via `AUREY_X402_*` env vars:

- `max_price_usd` — hard ceiling per request
- `auto_approve_max_usd` — auto-pay at or under this (default `0.25`)
- `batch_max_deposit_usd` — cap for batch-settlement channel deposits
- `allowed_hosts` — optional comma-separated host allowlist (empty = any)
- `prefer_network` — default `eip155:8453` (Base)

Flow: `x402_preview` → `x402_fetch` (or `confirm_payment=true` + `max_price_usd` when above auto-approve). Only **known USDC** on the quoted chain is auto-paid in v1.
