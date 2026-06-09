# 1Claw + Aurey — agent playbook (one page)

**Load in the agent:** [skills/aurey-wallet-onboarding/SKILL.md](skills/aurey-wallet-onboarding/SKILL.md) (full steps).

**Shared install:** [install/index.md](install/index.md) · [GitHub Pages](https://agentic-pantheon.github.io/aurey-mcp/install.html).

**Humans / all hosts:** [docs/1claw-onboarding-guide.md](docs/1claw-onboarding-guide.md) · [docs/troubleshooting.md](docs/troubleshooting.md).

---

## Non-negotiables

- Never ask in chat: private keys, mnemonics, **`1ck_`**, **`ocv_`**, Alchemy.
- OK in chat: vault/agent UUIDs (after setup), repo path, tool results, errors (redacted).
- Never invent `0x` — use **`get_agent_wallet_addresses`**.
- No **`tx_execute`** until user confirms a **prepare** summary.

---

## Pick your MCP host

Ask which host the user runs **before** suggesting commands.

| Host | Setup | Verify |
|------|--------|--------|
| **Hermes** | `aurey-setup --host hermes` — [install/hermes.md](install/hermes.md) | `hermes mcp test aurey-wallet` → `/reload-mcp` |
| **Cursor** | `aurey-setup --host cursor` — [install/cursor.md](install/cursor.md) | Restart or reload MCP in Settings |
| **Claude** | `aurey-setup --host claude` — [install/claude.md](install/claude.md) | Quit and reopen app |
| **OpenClaw** | `aurey-setup --host openclaw` — [install/openclaw.md](install/openclaw.md) | Restart gateway |

**User terminal (PyPI install, any host):**

```bash
curl -fsSL https://agentic-pantheon.github.io/aurey-mcp/install.sh | bash
aurey-setup --host cursor   # match user's host
```

**Dev clone:** `uv sync --group dev && uv run aurey-setup --host <host>`.

Then **`get_agent_wallet_addresses`** → read-only balance.

---

## Manual path (reminder)

1. [1claw.xyz](https://1claw.xyz) account  
2. Vault → `AUREY_ONECLAW_VAULT_ID`  
3. Agent + **Intents** → `AUREY_ONECLAW_AGENT_ID`  
4. `ocv_…` → `AUREY_ONECLAW_VAULT_API_KEY` (host env, not chat)  
5. **Ethereum** signing key on agent  
6. Alchemy in vault `api-keys/alchemy` + policy  
7. MCP install: `aurey-setup --host <host>` or host doc above  
8. Verify: `get_agent_wallet_addresses`  

---

## After onboarding

Load [skills/aurey-wallet/SKILL.md](skills/aurey-wallet/SKILL.md).

- Swaps/sends: `get_agent_wallet_addresses` → prepare → **confirm** → `tx_execute(prepared_id=…)`

---

## MCP startup failures

See [docs/troubleshooting.md](docs/troubleshooting.md). Common: missing ids in `~/.aurey/mcp.env`, bad `ocv_`, or **no Ethereum signing key** on agent.
