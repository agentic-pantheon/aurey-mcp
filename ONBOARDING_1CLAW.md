# 1Claw + Aurey — agent playbook (one page)

**Load in the agent:** [skills/aurey-wallet-onboarding/SKILL.md](skills/aurey-wallet-onboarding/SKILL.md) (full steps).

**All hosts:** `uv run aurey-setup --host <hermes|cursor|claude|openclaw>` — [install/hermes.md](install/hermes.md).

**Humans / all hosts:** [docs/1claw-onboarding-guide.md](docs/1claw-onboarding-guide.md).

---

## Non-negotiables

- Never ask for—or offer to receive—in chat: private keys, mnemonics, **`1ck_`**, **`ocv_`**, Alchemy.
- **First setup message, unprompted:** say keys are never pasted in chat + give the terminal commands to run **on the machine where the agent runs** (`aurey-setup` prompts for keys there, masked).
- If a secret is pasted in chat anyway: don’t echo it; have the user **rotate it** and redo setup in the terminal.
- OK in chat: vault/agent UUIDs (after setup), repo path, tool results, errors (redacted).
- Never invent `0x` — use **`get_agent_wallet_addresses`**.
- No **`tx_execute`** until user confirms a **prepare** summary.

---

## Hermes fast path (default)

**User terminal:**

```bash
cd /path/to/aurey-wallet-mcp && uv sync --group dev && uv run aurey-setup --host hermes
```

**Agent chat:** coach prerequisites (1Claw account, `1ck_` from dashboard) → user runs command → `hermes mcp test aurey-wallet` → `/reload-mcp` → **`get_agent_wallet_addresses`** → read-only balance.

---

## Manual path (reminder)

1. [1claw.xyz](https://1claw.xyz) account  
2. Vault → `AUREY_ONECLAW_VAULT_ID`  
3. Agent + **Intents** → `AUREY_ONECLAW_AGENT_ID`  
4. `ocv_…` → `AUREY_ONECLAW_VAULT_API_KEY` (host env, not chat)  
5. **Ethereum** signing key on agent  
6. Alchemy in vault `api-keys/alchemy` + policy  
7. MCP install: `aurey-hermes-install` or host snippet (`install/openclaw.md`, `install/cursor.md`)  
8. Verify: `get_agent_wallet_addresses`  

---

## After onboarding

Load [skills/aurey-wallet/SKILL.md](skills/aurey-wallet/SKILL.md).

- Swaps/sends: `get_agent_wallet_addresses` → prepare → **confirm** → `tx_execute(prepared_id=…)`

---

## MCP startup failures

User fixes **host env** (e.g. `~/.hermes/.env`): missing ids, bad `ocv_`, or **no Ethereum signing key** on agent.
