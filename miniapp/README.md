# Aurey portfolio UI (SPA)

React SPA for portfolio charts and token balances. **Local agent mode** (default): served by `aurey-wallet-mcp` on `http://127.0.0.1:8765/` using `POST /v1/dashboard/portfolio`. **Telegram Web App** mode (hosted): uses `initData` and `POST /v1/miniapp/portfolio`.

## End users

`aurey-setup` enables `[dashboard] enabled = true` by default. Reload MCP, then open **http://127.0.0.1:8765/**.

Live Zerion data requires an optional Zerion API key (`aurey-setup` prompt or `api-keys/zerion` in 1Claw).

## Build (maintainers / dev clone)

From repository root:

```bash
uv run python scripts/build_portfolio_static.py
```

This runs `npm ci` + `npm run build` in `miniapp/` and copies output to `src/aurey_wallet_mcp/static/portfolio/` for the Python wheel.

## Local frontend development

Terminal A — MCP with dashboard (credentials in `~/.aurey/mcp.env`):

```bash
set -a && source ~/.aurey/mcp.env && set +a
export AUREY_DASHBOARD_ENABLED=true
uv run aurey-wallet-mcp
```

Terminal B — Vite (proxies `/v1` to port 8765):

```bash
cd miniapp
npm run dev
```

Open `http://127.0.0.1:5173/miniapp/`.

## Telegram (hosted, out of scope for personal MCP)

Expose HTTPS + tunnel and open from Telegram with `AUREY_TELEGRAM_MINIAPP_PUBLIC_URL` when hosted platform miniapp routes are enabled.
