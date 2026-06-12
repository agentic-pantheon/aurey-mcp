---
name: aurey-wallet
description: >-
  Operates Aurey Wallet MCP tools for EVM reads, swaps, and 1Claw Intents
  prepare/execute. Use when the user checks balances, swaps, sends tokens, or
  uses wallet tools after MCP is configured. For first-time setup, use
  aurey-wallet-onboarding instead.
---

# Aurey Wallet — operations (agent skill)

MCP tools provide EVM operations with **1Claw Intents** custody. If MCP is not configured yet, switch to **[skills/aurey-wallet-onboarding/SKILL.md](../aurey-wallet-onboarding/SKILL.md)**.

## Rules

1. Use tools only — never invent balances, addresses, or tx hashes.
2. **Call `get_agent_wallet_addresses` first** when you need the user's EVM `from_address`.
3. Resolve tickers with `resolve_known_address` before other `0x` addresses.
4. **Token catalog (LiFi file):** use `resolve_known_address(chain, ticker)` or `resolve_token_by_address` for one token. Call `list_supported_tokens` **only with `chain`** (never global). Do not paste large token lists into chat—use counts and a few examples.
5. Flow: read → prepare (`swap_prepare`, `tx_prepare_*`) → **show summary** → `tx_execute(prepared_id=...)` only after **explicit** user confirmation.
6. Never ask for private keys; signing is server-side via 1Claw Intents.
7. For swaps, prefer `prepared_id` over copying calldata.
8. **Paid HTTP APIs (x402):** use `x402_preview` then `x402_fetch`; auto-pay only under `auto_approve_max_usd`. Above that, get explicit user assent and retry with `confirm_payment=true` and `max_price_usd` bound to the quote. Do not use x402 for swaps—use `swap_prepare`.

## Paid API (x402)

1. `get_agent_wallet_addresses` and `x402_payment_status` if balance may be low.
2. `x402_preview` on the endpoint URL.
3. If exposure ≤ caps → `x402_fetch` once. Else explain quote → user assents → `x402_fetch` with `confirm_payment=true` and `max_price_usd` set to the quoted amount.
4. Batch-heavy usage: `x402_batch_channel_status`; offer `x402_batch_refund` for unused escrow.
5. Summarize the API response body for the user.

## Typical swap

1. `get_agent_wallet_addresses` → `ethereum` as `from_address`
2. `evm_get_erc20_balance` / portfolio reads as needed
3. `swap_prepare` → note `prepared_id` and fees
4. Optional `tx_prepare_erc20_approval` if indicated
5. `tx_prepare_lifi` with `prepared_id`
6. User confirms
7. `tx_execute(prepared_id=...)`
8. Cross-chain: `lifi_get_status`

## Operator env (reference)

Hermes install writes `~/.hermes/.env`:

- `AUREY_ONECLAW_VAULT_ID`, `AUREY_ONECLAW_AGENT_ID`, `AUREY_ONECLAW_VAULT_API_KEY` (`ocv_…`)

Defaults in package: `oneclaw_intents`, standalone mode. **Alchemy:** 1Claw path `api-keys/alchemy` (`~/.aurey/config.toml`), not MCP env on Hermes.

No manual wallet address unless `AUREY_DEEP_AGENT_WALLET_ADDRESS`.

**Setup:** [install/hermes.md](../../install/hermes.md) (`aurey-setup`) · [docs/setup.md](../../docs/setup.md)
