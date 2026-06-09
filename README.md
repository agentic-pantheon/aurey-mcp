# Aurey Wallet MCP

Self-hosted **Model Context Protocol** server for EVM wallet tools: balances, swaps, and prepare/execute signing through **1Claw Intents** (no private keys in chat or MCP env for Alchemy).

Works with [Hermes Agent](https://hermes-agent.org/), [Cursor](https://cursor.com/), Claude Desktop, and [OpenClaw](https://docs.openclaw.ai/).

---

## Quick start (`aurey-setup`)

One **1Claw human** API key (`1ck_…` from [1claw.xyz](https://1claw.xyz)) in **your terminal only**—never in LLM chat.

**Install without a git clone** ([full guide](https://agentic-pantheon.github.io/aurey-mcp/install.html)):

```bash
curl -fsSL https://agentic-pantheon.github.io/aurey-mcp/install.sh | bash
aurey-setup --host hermes
```

Manual: `pip install 'aurey-wallet-mcp[hermes]'` or `uv tool install 'aurey-wallet-mcp[hermes]'`, then `aurey-setup --host hermes`.

**Contributors** (develop from source):

```bash
git clone https://github.com/agentic-pantheon/aurey-mcp.git
cd aurey-mcp
uv sync --group dev --extra hermes
uv run aurey-setup --host hermes
```

**Masked prompts:** `1ck_…`, then optional [Alchemy](https://www.alchemy.com/) key (stored in 1Claw, not MCP `env`).

### Choose your MCP host

| `--host` | After install |
|----------|----------------|
| `hermes` (default) | `hermes mcp test aurey-wallet` → chat `/reload-mcp` |
| `cursor` | Restart Cursor or reload MCP in Settings |
| `claude` | Quit and reopen Claude Desktop |
| `openclaw` | Restart the OpenClaw gateway |

```bash
aurey-setup --host cursor
aurey-setup --host claude
aurey-setup --host openclaw
```

(From a dev clone, prefix with `uv run`.)

Host-specific notes: [install/hermes.md](install/hermes.md) · [cursor](install/cursor.md) · [claude](install/claude.md) · [openclaw](install/openclaw.md).

### What `aurey-setup` does

1. **1Claw (Human API)** — auth with `1ck_…`; pick or create vault; create Intents agent; read policy on `api-keys/**`; optional Alchemy at `api-keys/alchemy`; provision **Ethereum** signing key.
2. **Credentials** — `~/.aurey/mcp.env` (vault id, agent id, `ocv_…`, mode `600`).
3. **MCP launcher** — `~/.aurey/run-aurey-wallet-mcp.sh` (sources `mcp.env`; keeps secrets out of host JSON).
4. **Host config** — patches Hermes / Cursor / Claude / OpenClaw MCP entry to use the wrapper.
5. **Alchemy path** — `~/.aurey/config.toml` → `alchemy_secret_path = "api-keys/alchemy"`.
6. **Smoke test** — optional MCP bootstrap check.

Hermes also updates `~/.hermes/config.yaml` and `~/.hermes/.env`. For Hermes YAML edits: `uv sync --extra hermes` (included when you run `aurey-setup --host hermes`).

### Useful flags

```bash
uv run aurey-setup --vault-id '<uuid>'              # use existing vault
uv run aurey-setup --skip-alchemy                   # add Alchemy in 1Claw later
uv run aurey-setup --from-env                       # human key in AUREY_ONECLAW_HUMAN_API_KEY
uv run aurey-setup --provision-only                 # 1Claw + mcp.env only
uv run aurey-setup --host cursor --skip-provision   # re-wire MCP from ~/.aurey/mcp.env
uv run aurey-setup --host cursor --cursor-project . # project .cursor/mcp.json
uv run aurey-setup --config /path/to/mcp.json       # override config file
```

### Verify in chat

Load agent skills ([SKILL.md](SKILL.md)). Ask your agent to call **`get_agent_wallet_addresses`**, then a read-only balance. Swaps/sends: prepare → **you confirm** → `tx_execute(prepared_id=…)`.

### Secrets (do not paste in chat)

| Value | Where |
|-------|--------|
| `1ck_…` (human) | `aurey-setup` prompt only |
| `ocv_…` (agent) | `~/.aurey/mcp.env`, `~/.hermes/.env` (Hermes) |
| Alchemy | 1Claw vault `api-keys/alchemy` |
| Vault / agent UUID | OK in chat for debugging |

---

## Manual / advanced

**Hermes without full provision** (you already have vault, agent, `ocv_` in the dashboard):

```bash
uv sync --group dev --extra hermes
uv run aurey-hermes-install --prompt-secrets
```

**Run MCP in a shell** (after 1Claw is configured):

```bash
export AUREY_ONECLAW_VAULT_ID=...
export AUREY_ONECLAW_VAULT_API_KEY=...
export AUREY_ONECLAW_AGENT_ID=...
uv run aurey-wallet-mcp
```

Manual 1Claw steps: [docs/1claw-onboarding-guide.md](docs/1claw-onboarding-guide.md).

---

## Components

| Component | Purpose |
|-----------|---------|
| `aurey-setup` | 1Claw provision + MCP install (all hosts) |
| `aurey-hermes-install` | Hermes-only install when 1Claw is already done |
| `aurey-wallet-mcp` | MCP stdio server + optional local dashboard |
| `aurey-route-builder` | Li.Fi quote proxy with integrator fee |
| `aurey_autonomy_api` | Stub x402 autonomy signals (replace in production) |

---

## Docs

| Doc | Audience |
|-----|----------|
| [install/hermes.md](install/hermes.md) | Full `aurey-setup` reference + Hermes |
| [install/cursor.md](install/cursor.md) | Cursor |
| [install/claude.md](install/claude.md) | Claude Desktop |
| [install/openclaw.md](install/openclaw.md) | OpenClaw |
| [docs/setup.md](docs/setup.md) | Env vars, route builder, dashboard |
| [docs/1claw-onboarding-guide.md](docs/1claw-onboarding-guide.md) | 1Claw + agent coaching |
| [ONBOARDING_1CLAW.md](ONBOARDING_1CLAW.md) | One-page agent playbook |
| [docs/releasing.md](docs/releasing.md) | PyPI + GitHub Pages releases (maintainers) |
| [SKILL.md](SKILL.md) | Load `skills/aurey-wallet-onboarding` + `skills/aurey-wallet` |

---

## Safety

- `tx_execute` only accepts server-issued `prepared_id` values.
- Signing via 1Claw Intents; private keys are not exposed to the model.
- Autonomy tools default to **dry-run**; arming is explicit and local.
