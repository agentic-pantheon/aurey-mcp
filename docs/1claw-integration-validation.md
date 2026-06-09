# Aurey Wallet MCP and 1Claw — integration overview

**Audience:** 1Claw team (validation of how we call your APIs and model credentials).  
**Repository:** [agentic-pantheon/aurey-mcp](https://github.com/agentic-pantheon/aurey-mcp) (Python package name: `aurey-wallet-mcp`).  
**Default API base:** `https://api.1claw.xyz`  
**Official 1Claw docs we reference:** [docs.1claw.xyz](https://docs.1claw.xyz) (Human API, Intents API, Platform API).

This document is maintained for external review and is **not** part of the published user onboarding path (see `docs/1claw-onboarding-guide.md` for operators).

---

## 1. What Aurey Wallet MCP is

**Aurey Wallet MCP** is a self-hosted **Model Context Protocol (MCP)** server that exposes EVM wallet capabilities to LLM agents (Hermes, Cursor, Claude Desktop, OpenClaw, and similar hosts). The model never receives private keys or third-party API keys for chain reads; it calls MCP tools, and the server performs RPC, quoting, policy checks, and signing on the operator’s machine.

### 1.1 Role in the stack

```text
Human (terminal)          MCP host (Hermes / Cursor / …)          Aurey MCP process          1Claw + chain
      │                              │                                    │                        │
      │ 1ck_… once (aurey-setup)     │  spawns stdio child                │  ocv_… + vault/agent   │
      ├─────────────────────────────►│  (wrapper script, no secrets       ├───────────────────────►│
      │                              │   in host JSON)                    │  JWT + Intents sign    │
      │                              │                                    │                        │
      │                              │  tool calls (JSON)                 │  Alchemy/LiFi from     │
      │                              ├───────────────────────────────────►│  vault secrets         │
      │                              │◄───────────────────────────────────┤  balances, prepares    │
```

- **Entry point:** `aurey-wallet-mcp` → `src/aurey_wallet_mcp/server.py` (stdio MCP, server name `aurey-wallet`).
- **Runtime wiring:** `bootstrap_aurey_runtime()` in `src/aurey/service/bootstrap.py` builds `AureyRuntime` (secret store, Web3 tx pipeline, LiFi/token tooling).
- **Tools:** LangChain tools from `build_aurey_subgraph_tools()` are registered in `src/aurey_wallet_mcp/tools.py` and invoked as MCP tools.

### 1.2 How operators install and use it

1. **Provision 1Claw** (vault, Intents agent, policies, optional secrets, Ethereum signing key) — usually via `aurey-setup` and a human key `1ck_…` in the terminal only.
2. **Install MCP on a host** — `aurey-setup --host <hermes|cursor|claude|openclaw>` writes host config and shared files under `~/.aurey/` (`mcp.env`, `run-aurey-wallet-mcp.sh`, `config.toml`).
3. **Runtime env** (in MCP subprocess, not in chat): `AUREY_ONECLAW_VAULT_ID`, `AUREY_ONECLAW_AGENT_ID`, `AUREY_ONECLAW_VAULT_API_KEY` (`ocv_…`).
4. **Agent workflow:** `get_agent_wallet_addresses` → read-only tools (balances, quotes) → **prepare** tools return a server-side `prepared_id` → human confirms → `tx_execute(prepared_id=…)` signs and broadcasts.

**Safety properties we enforce in product/docs:**

- No `tx_execute` without a server-issued `prepared_id` (or equivalent envelope from prepare).
- Addresses come from 1Claw signing-keys, not from model-invented `0x` strings.
- Human `1ck_`, agent `ocv_`, Alchemy, and LiFi keys are not requested in LLM chat.

### 1.3 Package defaults (MCP distribution)

| Setting | Default for `aurey-wallet-mcp` |
|--------|--------------------------------|
| `AUREY_HOSTED_PLATFORM_ENABLED` | `false` (standalone: one agent per MCP instance) |
| `AUREY_EVM_SIGNING_MODE` | `oneclaw_intents` (required; bootstrap fails otherwise) |
| `oneclaw_base_url` | `https://api.1claw.xyz` |

The shared `aurey` library also contains **hosted multi-tenant** and **Shroud LLM proxy** settings for other deployments; the **published MCP package** refuses to start with `hosted_platform_enabled=true` and does not depend on Shroud for wallet tools.

---

## 2. Deep dive: how we use 1Claw

### 2.1 Credential and principal model

We distinguish three 1Claw key types in documentation; the default MCP install uses two of them.

| Prefix | 1Claw role | Where Aurey uses it |
|--------|------------|---------------------|
| `1ck_` | Human / personal API key | **Provisioning only** (`aurey-setup`, `oneclaw_provision.py`). Exchanged for a Bearer JWT or used directly against Human API. Never stored in MCP host JSON or passed to the model. |
| `ocv_` | Agent API key | **Runtime** bootstrap credential in `AUREY_ONECLAW_VAULT_API_KEY` (legacy alias: `AUREY_ONECLAW_BOOTSTRAP_API_KEY`). Used to obtain agent JWTs and call agent-scoped endpoints. |
| `plt_` | Platform operator | Documented for Path C (one agent per end user). **Not** used in the default personal MCP install. |

**Stable IDs at runtime:**

- `AUREY_ONECLAW_VAULT_ID` — vault UUID for secret reads.
- `AUREY_ONECLAW_AGENT_ID` — Intents-enabled agent UUID for signing and signing-keys.

Optional override: `AUREY_DEEP_AGENT_WALLET_ADDRESS` bypasses signing-keys for display/prepare `from` address (discouraged for normal onboarding).

### 2.2 Provisioning flow (Human API)

Implemented in `src/aurey_wallet_mcp/oneclaw_provision.py` (`provision_for_aurey`, `OneClawHumanClient`).

**Authentication:**

1. If the credential starts with `1ck_`, `POST /v1/auth/api-key-token` with `{"api_key": "1ck_…"}` → use `access_token` as Bearer.
2. Else if the value is already a JWT (`eyJ…`), use as Bearer.
3. Else probe `GET /v1/vaults` with `Authorization: Bearer <key>`; on 200, treat key as Bearer.

**Resources created or selected:**

| Step | HTTP | Purpose |
|------|------|---------|
| List / create vault | `GET /v1/vaults`, `POST /v1/vaults` | Default name `aurey-wallet`; reuse logic if one vault or name match |
| Create agent | `POST /v1/agents` | Name `Aurey Wallet MCP`, `intents_api_enabled: true`. **We omit `scopes`** so JWT scopes derive from vault policies (hard-coded scopes blocked secret reads in testing). |
| Vault policy | `POST /v1/vaults/{vault_id}/policies` | `principal_type: agent`, `secret_path_pattern: api-keys/**`, `permissions: ["read"]` (409 ignored) |
| Optional secrets | `PUT /v1/vaults/{vault_id}/secrets/{path}` | `type: api_key` — default paths `api-keys/alchemy`, `api-keys/lifi` |
| Signing key | `GET` then `POST /v1/agents/{agent_id}/signing-keys` | Chain `ethereum`; idempotent if key already exists |

**Provisioner output** (`ProvisionResult`): `vault_id`, `agent_id`, `agent_api_key` (`ocv_…`), optional `ethereum_address`, secret paths for Alchemy/LiFi.

CLI: `aurey-setup` writes these into `~/.aurey/mcp.env` and host-specific env (e.g. `~/.hermes/.env`).

### 2.3 Runtime client: `OneClawHttpClient`

Single HTTP adapter in `src/aurey/custody/secret_store.py` implements:

- `OneClawClient` (secret reads)
- `OneClawEvmTransactionSigner` (unified sign + Intents sign-only)

It is constructed at bootstrap with the bootstrap `ocv_…` and `oneclaw_agent_id`.

#### 2.3.1 Agent JWT (`POST /v1/auth/agent-token`)

For hosted-style reads and all agent POSTs when `agent_id` is known:

- Request: `agent_id` + `api_key` (bootstrap `ocv_…` in standalone MCP).
- Response: access token; we cache per `(agent_id, api_key fingerprint)`.
- Expiry: if `expires_in` is present, refresh at `expires_in - oneclaw_agent_token_expiry_skew_seconds` (default skew 60s). On 401 during secret GET, invalidate cache and retry once.

This matches the documented pattern of reusing agent tokens until near expiry rather than exchanging on every call.

#### 2.3.2 Vault secret reads

When `OneClawSecretStore` is constructed with `agent_id` (always in MCP bootstrap):

1. Obtain Bearer via agent-token flow above.
2. `GET /v1/vaults/{vault_id}/secrets/{path}` with that Bearer.

**Legacy path** (no `agent_id` on store): `POST /v1/vaults/{vault_id}/secrets:resolve` with API key as Bearer — retained for older/self-hosted compatibility; MCP standalone uses the hosted GET path.

**Typical secret paths:**

| Logical path | Consumer |
|--------------|----------|
| `api-keys/alchemy` | EVM RPC via Alchemy (configured in `~/.aurey/config.toml` as `alchemy_secret_path`) |
| `api-keys/lifi` | LiFi Earn / optional `x-lifi-api-key` on quotes |
| `api-keys/coingecko` | Optional price feeds (settings) |

Plaintext env fallbacks (`AUREY_ALCHEMY_API_KEY`, `AUREY_LIFI_API_KEY`) exist but vault storage is preferred, especially on Hermes.

**Human API PUT** (`put_secret_human_api`): used in hosted/dual-write scenarios in the library; provisioning uses the Human client in `oneclaw_provision.py` instead.

### 2.4 Wallet addresses (no manual `0x`)

On MCP startup, `hydrate_runtime_agent_wallets()` calls `fetch_agent_wallet_addresses_from_oneclaw()`:

- Uses bootstrap `ocv_…` → agent JWT → `GET /v1/agents/{agent_id}/signing-keys`.
- Parses Ethereum (and Solana if present) addresses into runtime cache.
- MCP tool `get_agent_wallet_addresses` exposes this; `refresh: true` forces a new signing-keys fetch.

Bootstrap **fails** if no EVM address is available and no `AUREY_DEEP_AGENT_WALLET_ADDRESS` override is set — this is intentional to block a half-provisioned agent.

### 2.5 Signing mode: `oneclaw_intents` only (MCP package)

`aurey-wallet-mcp` requires `evm_signing_mode=oneclaw_intents`. The alternate mode `vault_key` (read raw key material from vault and sign locally) exists in the library for other products but is **rejected** at MCP bootstrap.

**Principal resolution** (`OneClawSigningPrincipal` in `src/aurey/custody/intents_principal.py`):

- Standalone MCP: `settings.oneclaw_agent_id` + implicit Bearer via `OneClawHttpClient` (no separate bearer in tools).
- Hosted (`hosted_platform_enabled=true`): per-request `user_agent_id` from async context — **not** available in the MCP package (bootstrap error if enabled).

### 2.6 Transaction execution path (primary production use)

User-facing flow: prepare MCP tool → `prepared_id` → `tx_execute`.

Pipeline (`src/aurey/graphs/tx_execute.py`, `src/aurey/graphs/evm_tx_pipeline.py`):

1. Load `PreparedTxEnvelope` (signing_mode must match `oneclaw_intents`).
2. Simulate / policy on server (Web3 + operator settings).
3. **Sign** via `OneClawHttpClient.sign_evm_transaction()`:
   - Convert Web3-style tx dict to 1Claw unified flat fields (`_web3_tx_to_oneclaw_unified_flat`).
   - **Important:** unified `/sign` expects `value` as **decimal ETH string**, not wei (we convert from wei).
   - `POST /v1/agents/{agent_id}/sign` with body:
     - `intent_type: "transaction"`
     - `chain: <name>` (e.g. `base`, `ethereum` — from chain id mapping)
     - transaction fields (`to`, `data`, `value`, gas fields, nonce, etc.)
     - optional `signing_key_path` if envelope carries `signing_key_secret_path`
4. Validate signer `from_address` matches envelope `from_address` when returned.
5. **Broadcast** signed raw tx via operator-configured RPC (Alchemy secret), not via 1Claw broadcast in this path.

So for swaps, sends, and Earn deposits prepared through Aurey, **1Claw is the signing authority**; **chain broadcast is BYORPC** (bring your own RPC).

### 2.7 Additional 1Claw signing surfaces (MCP tools)

When `oneclaw_intents` and `oneclaw_evm_signer` are configured, we also expose tools that map directly to 1Claw APIs (see `src/aurey/tools/agent_tools.py`):

| MCP tool | 1Claw endpoint | `intent_type` / notes |
|----------|----------------|------------------------|
| `oneclaw_sign_personal_message` | `POST …/sign` | `personal_sign` (EIP-191); UTF-8 → `0x` hex payload |
| `oneclaw_sign_typed_data` | `POST …/sign` | `typed_data` (EIP-712) |
| `oneclaw_intents_sign_transaction` | `POST …/transactions/sign` | Intents sign-only (no 1Claw broadcast); BYORPC serialized tx |

These require operator/agent policy (e.g. message signing enabled on the agent). Errors are normalized to `oneclaw_signing_error` without leaking secrets.

### 2.8 Policies and scopes (design choices worth validating)

1. **Agent creation:** we do **not** send a fixed `scopes` array on `POST /v1/agents`; we rely on vault policies for effective JWT permissions.
2. **Provisioner policy:** read-only on `api-keys/**` for the Aurey agent principal.
3. **Signing:** Intents API enabled on the agent; Ethereum signing key provisioned at setup.
4. **Secrets in errors:** provision and HTTP layers truncate problem details and avoid echoing secret values in exceptions/logs (Bearer redacted in log lines).

### 2.9 What we do **not** do with 1Claw (default MCP)

- We do **not** store `1ck_` or `ocv_` in MCP host JSON; wrapper script sources `~/.aurey/mcp.env`.
- We do **not** expose private keys or vault secret values to the model—only tool results (addresses, hashes, errors).
- We do **not** use Platform API (`plt_`) in the default single-user install.
- We do **not** enable `hosted_platform_enabled` in the MCP server process.
- We do **not** use 1Claw to broadcast in the main `tx_execute` path (unified sign → local RPC broadcast).

### 2.10 Hosted / Platform code path (library only)

The codebase includes hooks for multi-tenant hosted products (`hosted_platform_enabled`, `POST /v1/auth/delegated-token`, per-user `ocv_`, `current_hosted_signing_context`). That path is **intentionally disabled** in `bootstrap_aurey_runtime()` for `aurey-wallet-mcp`. Operators building SaaS on Aurey would use 1Claw [Platform API](https://docs.1claw.xyz/docs/guides/platform-api) separately; we document Path C in `docs/1claw-onboarding-guide.md` but do not ship it in the personal MCP binary behavior.

---

## 3. 1Claw API surface — consolidated reference

**Base URL:** `https://api.1claw.xyz` (overridable via `oneclaw_base_url` / settings).

### Provisioning (Human Bearer)

| Method | Path | Body / notes |
|--------|------|----------------|
| POST | `/v1/auth/api-key-token` | `1ck_…` → JWT |
| GET | `/v1/vaults` | List vaults |
| POST | `/v1/vaults` | Create vault |
| POST | `/v1/agents` | `intents_api_enabled: true` |
| POST | `/v1/vaults/{id}/policies` | Agent read `api-keys/**` |
| PUT | `/v1/vaults/{id}/secrets/{path}` | `type: api_key` |
| GET | `/v1/agents/{id}/signing-keys` | List keys |
| POST | `/v1/agents/{id}/signing-keys` | `chain: ethereum` |

### Runtime (agent `ocv_…`)

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/v1/auth/agent-token` | Agent JWT |
| GET | `/v1/vaults/{id}/secrets/{path}` | Read Alchemy/LiFi/etc. |
| POST | `/v1/vaults/{id}/secrets:resolve` | Legacy resolve (fallback) |
| GET | `/v1/agents/{id}/signing-keys` | Addresses |
| POST | `/v1/agents/{id}/sign` | Unified sign (`transaction`, `personal_sign`, `typed_data`) |
| POST | `/v1/agents/{id}/transactions/sign` | Intents sign-only |

---

## 4. Validation checklist (for 1Claw team)

Please confirm or correct the following assumptions:

1. **JWT + policy model:** Omitting `scopes` on agent create and relying on vault policy `api-keys/**` read is the supported way for our agent to read Alchemy/LiFi secrets.
2. **Agent-token caching:** Our `expires_in` skew refresh and single 401 retry on secret GET align with your recommendations.
3. **Unified sign `value`:** Decimal ETH string (not wei) for `intent_type: transaction` is still the canonical contract per [Intents API](https://docs.1claw.xyz/docs/guides/intents-api).
4. **BYORPC:** Using unified `/sign` then broadcasting via external RPC is a supported/intended pattern for Intents-enabled agents.
5. **Signing-keys:** `GET signing-keys` with agent JWT from the same `ocv_…` used at bootstrap is the correct way to discover the default Ethereum address for Intents.
6. **409 handling:** We treat 409 on policy create and signing-key create as idempotent success / “already exists”—is that correct for your API?
7. **MCP-only constraints:** Requiring `oneclaw_intents` and disabling hosted bootstrap in the MCP package matches your expected split between “personal agent MCP” vs “Platform per-user agents.”

---

## 5. Code map (quick index)

| Area | Location |
|------|----------|
| Human API provision | `src/aurey_wallet_mcp/oneclaw_provision.py` |
| Setup CLI | `src/aurey_wallet_mcp/setup.py` |
| MCP server | `src/aurey_wallet_mcp/server.py` |
| Runtime bootstrap | `src/aurey/service/bootstrap.py` |
| HTTP client + sign | `src/aurey/custody/secret_store.py` |
| Secret store wrapper | `OneClawSecretStore` (same file) |
| Addresses | `src/aurey/custody/agent_wallet.py` |
| Signing principal | `src/aurey/custody/intents_principal.py` |
| Execute pipeline | `src/aurey/graphs/tx_execute.py`, `evm_tx_pipeline.py` |
| MCP tools | `src/aurey/tools/agent_tools.py` |
| Settings / env | `src/aurey/settings/__init__.py`, `config.example.toml` |

---

## 6. Contact context

**Project:** Agentic Pantheon — Aurey Wallet MCP  
**PyPI:** `aurey-wallet-mcp`  
**User-facing 1Claw onboarding:** `docs/1claw-onboarding-guide.md`, `ONBOARDING_1CLAW.md`

If anything in this document disagrees with current 1Claw API behavior, we will adjust provisioner, client, or docs in the open-source repo accordingly.
