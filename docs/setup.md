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
6. **LiFi** — optional store at `api-keys/lifi` (Earn vault discovery; see [Earn quickstart](https://docs.li.fi/earn/quickstart)).
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

**LiFi (optional):** `lifi_api_secret_path = "api-keys/lifi"` when you use Earn vault tools; get a key via [Earn quickstart](https://docs.li.fi/earn/quickstart). Optional plaintext: `AUREY_LIFI_API_KEY`.

On MCP start, the plugin loads the agent’s Ethereum address from signing-keys. Failure → finish 1Claw ETH key provisioning.

Tool: **`get_agent_wallet_addresses`** (`refresh=true` after provisioning without restart).

Optional: `AUREY_DEEP_AGENT_WALLET_ADDRESS`, `AUREY_ROUTE_BUILDER_URL`.

---

## Host install docs

- [Hermes](../install/hermes.md) — `aurey-setup --host hermes`
- [Cursor](../install/cursor.md) — `--host cursor`
- [Claude](../install/claude.md) — `--host claude`
- [OpenClaw](../install/openclaw.md) — `--host openclaw`

---

## Route builder (optional)

```bash
export AUREY_ROUTE_BUILDER_LIFI_API_KEY=...
export AUREY_ROUTE_BUILDER_AUTH_TOKEN=...
uv run aurey-route-builder
```

Plugin:

```bash
export AUREY_ROUTE_BUILDER_URL=http://127.0.0.1:8091
export AUREY_ROUTE_BUILDER_API_KEY=...
```

---

## Local dashboard

```bash
export AUREY_DASHBOARD_ENABLED=true
export AUREY_DASHBOARD_AUTH_TOKEN=...
uv sync --extra dashboard
uv run aurey-wallet-mcp
```

Open `http://127.0.0.1:8765/` (build `miniapp/` first: `cd miniapp && npm install && npm run build`).

---

## Autonomy (optional)

```bash
export AUREY_AUTONOMY_X402_URL=http://127.0.0.1:8092
uv run python -m aurey_autonomy_api.app
```

MCP tools: `autonomy_configure_policy`, `autonomy_dry_run`, `autonomy_tick`.
