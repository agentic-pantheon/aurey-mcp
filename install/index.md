# Install Aurey Wallet MCP

Shared install flow for **Hermes**, **Cursor**, **Claude Desktop**, and **OpenClaw**. Pick a host-specific guide after step 2.

## Prerequisites

- Python **3.12+**
- 1Claw account and personal API key (`1ck_…`) from [1claw.xyz](https://1claw.xyz)
- Optional: [Alchemy](https://www.alchemy.com/) API key for balance reads
- Optional: [Zerion](https://developers.zerion.io/) API key for local portfolio UI / Mini App live data
- Your MCP host: Hermes, Cursor, Claude Desktop, or OpenClaw

> **Security:** Do not paste `1ck_`, `ocv_`, Alchemy, or Zerion API keys into chat. `curl | bash` runs a public script—review [install/install.sh](https://github.com/agentic-pantheon/aurey-mcp/blob/main/install/install.sh) or install manually below.

## 1 — Install the package

Recommended (curl):

```bash
curl -fsSL https://agentic-pantheon.github.io/aurey-mcp/install.sh | bash
```

Pin a version (optional):

```bash
AUREY_VERSION=0.1.2 curl -fsSL https://agentic-pantheon.github.io/aurey-mcp/install.sh | bash
```

Manual (no curl):

```bash
pip install 'aurey-wallet-mcp[hermes]'
# or: uv tool install 'aurey-wallet-mcp[hermes]'
# Cursor-only (no Hermes YAML tooling): pip install aurey-wallet-mcp
```

PyPI package name (exact): `aurey-wallet-mcp`.

### About the `[hermes]` extra

The curl installer and examples use `aurey-wallet-mcp[hermes]` because it adds **PyYAML** and Hermes YAML config helpers. **`aurey-setup` works for all hosts** with the base package; you do **not** need `[hermes]` for `--host cursor`, `claude`, or `openclaw`. Use `[hermes]` if you rely on `aurey-hermes-install` or Hermes-only YAML flows.

### Check version

```bash
aurey-version
# or: aurey-setup --version
```

`aurey-version -v` also prints the resolved `aurey-wallet-mcp` binary path when it is on `PATH`.

### Upgrade (PyPI)

On the machine where MCP runs (e.g. Railway shell, VPS, laptop):

```bash
aurey-update --host hermes
```

That upgrades `aurey-wallet-mcp[hermes]` from PyPI, refreshes host MCP config from `~/.aurey/mcp.env` (no new 1Claw keys), then reload MCP in Hermes (`/reload-mcp`). Use `--host cursor`, `claude`, or `openclaw` for other hosts.

Upgrade only (no config changes): `aurey-update --skip-rewire`. Pin a release: `aurey-update --pin-version 0.1.7 --host hermes`.

## 2 — Configure 1Claw and MCP {#hosts}

In a **terminal** (masked prompts — each keystroke shows `*`), pick your host:

| Host | Command | Detailed guide |
|------|---------|----------------|
| Hermes | `aurey-setup --host hermes` | [hermes.md](hermes.md) |
| Cursor | `aurey-setup --host cursor` | [cursor.md](cursor.md) |
| Claude Desktop | `aurey-setup --host claude` | [claude.md](claude.md) |
| OpenClaw | `aurey-setup --host openclaw` | [openclaw.md](openclaw.md) |

Example:

```bash
aurey-setup --host cursor
```

This provisions vault/agent/signing via 1Claw Human API, writes `~/.aurey/mcp.env`, and patches your host MCP config to use `~/.aurey/run-aurey-wallet-mcp.sh`.

Optional Zerion setup flags: `--zerion-key`, `--skip-zerion`, `--zerion-vault-path` (default vault path `api-keys/zerion`; sets `zerion_api_secret_path` in `~/.aurey/config.toml` when a key is stored).

## 3 — Reload and verify

| Host | After install |
|------|----------------|
| Hermes | `hermes mcp test aurey-wallet`, then `/reload-mcp` in chat |
| Cursor | Restart Cursor or reload MCP in Settings |
| Claude Desktop | Quit and reopen Claude Desktop |
| OpenClaw | Restart the OpenClaw gateway |

Ask your agent to call `get_agent_wallet_addresses`, then a read-only balance.

## Secrets

| Value | Where |
|-------|--------|
| `1ck_…` (human) | `aurey-setup` prompt only |
| `ocv_…` (agent) | `~/.aurey/mcp.env` (Hermes also mirrors to `~/.hermes/.env`) |
| Alchemy | 1Claw vault `api-keys/alchemy` |
| Zerion (optional) | 1Claw vault `api-keys/zerion` (or custom path); `zerion_api_secret_path` in `~/.aurey/config.toml` |
| Vault / agent UUID | OK in chat for debugging |

## Contributors (git clone)

```bash
git clone https://github.com/agentic-pantheon/aurey-mcp.git
cd aurey-mcp
uv sync --group dev
uv run aurey-setup --host cursor
```

Add `--extra hermes` when developing Hermes YAML install paths.

Machine-oriented spec: [llms.txt](https://agentic-pantheon.github.io/aurey-mcp/llms.txt).
