#!/usr/bin/env python3
# ruff: noqa: E501
"""Write src/aurey/data/x402_services.json from curated Ampersend marketplace research."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "src" / "aurey" / "data" / "x402_services.json"

DISCOVER = "https://app.ampersend.ai/discover/agent/{pid}"


def ep(eid: str, method: str, url: str, desc: str, price: float | None = None, note: str | None = None):
    return {
        "id": eid,
        "method": method,
        "url": url,
        "description": desc,
        "price_usd_min": price,
        "price_note": note,
    }


def zapper_eps(base: str) -> list[dict]:
    rows = [
        ("account-identity", "/x402/account-identity", 0.0011, "ENS/Farcaster/Lens/Basenames lookup"),
        ("defi-balances", "/x402/defi-balances", 0.0011, "DeFi positions"),
        ("general-swap-feed", "/x402/general-swap-feed", 0.0037, "Farcaster swap feed"),
        ("historical-token-price", "/x402/historical-token-price", 0.0011, "Historical token price"),
        ("nft-balances", "/x402/nft-balances", 0.0011, "NFT balances"),
        ("nft-collection-metadata", "/x402/nft-collection-metadata", 0.0011, "Collection metadata"),
        ("nft-ranking", "/x402/nft-ranking", 0.0045, "NFT collections ranked"),
        ("nft-token-metadata", "/x402/nft-token-metadata", 0.0011, "Single NFT metadata"),
        ("portfolio-totals", "/x402/portfolio-totals", 0.0019, "Aggregated portfolio"),
        ("search", "/x402/search", 0.0045, "Search tokens/NFTs/users/apps"),
        ("token-activity-feed", "/x402/token-activity-feed", 0.0037, "Token activity feed"),
        ("token-balances", "/x402/token-balances", 0.0011, "Token balances"),
        ("token-holders", "/x402/token-holders", 0.0011, "Holders + identity"),
        ("token-price", "/x402/token-price", 0.0011, "Real-time price"),
        ("token-ranking", "/x402/token-ranking", 0.0045, "Token ranking"),
        ("transaction-details", "/x402/transaction-details", 0.0011, "Tx interpretation"),
        ("transaction-history", "/x402/transaction-history", 0.0011, "Tx history"),
    ]
    return [ep(i, "POST", f"{base}{path}", d, p) for i, path, p, d in rows]


def stableenrich_eps(base: str) -> list[dict]:
    rows = [
        ("apollo-people-search", "/api/apollo/people-search", 0.02, "Apollo people search"),
        ("clado-contacts-enrich", "/api/clado/contacts-enrich", 0.2, "Clado contact enrichment"),
        ("exa-search", "/api/exa/search", 0.01, "Exa neural search"),
        ("firecrawl-scrape", "/api/firecrawl/scrape", 0.013, "Firecrawl scrape"),
        ("google-maps-text-search", "/api/google-maps/text-search/full", 0.08, "Google Maps text search"),
        ("hunter-email-verifier", "/api/hunter/email-verifier", 0.03, "Hunter email verify"),
        ("reddit-search", "/api/reddit/search", 0.02, "Reddit search"),
        ("serper-news", "/api/serper/news", 0.04, "Serper news"),
    ]
    return [ep(i, "POST", f"{base}{path}", d, p) for i, path, p, d in rows]


def auor_eps(base: str) -> list[dict]:
    rows = [
        ("historical-fx", "/all-rates-today/v1/historical", "GET", 0.001, "Historical FX"),
        ("fx-rates", "/all-rates-today/v1/rates", "GET", 0.001, "FX rates"),
        ("amadeus-search", "/amadeus/v1/search", "GET", 0.03, "Flight search"),
        ("company-enrich", "/crustdata/v1/companies/enrich", "GET", 0.12, "Company enrich"),
        ("crustdata-filters", "/crustdata/v1/filters", "GET", 0.001, "CrustData filters"),
        ("people-enrich", "/crustdata/v1/people/enrich", "GET", 0.12, "People enrich"),
        ("maps-details-basic", "/google-maps/v1/details/basic", "GET", 0.005, "Place details basic"),
        ("maps-details-full", "/google-maps/v1/details/full", "GET", 0.025, "Place details full"),
        ("maps-geocode", "/google-maps/v1/geocode", "GET", 0.005, "Geocode"),
        ("maps-search-basic", "/google-maps/v1/search/basic", "GET", 0.032, "Places search basic"),
        ("maps-search-full", "/google-maps/v1/search/full", "GET", 0.04, "Places search full"),
        ("translate-languages", "/google-translate/v1/languages", "GET", 0.001, "Languages"),
        ("translate", "/google-translate/v1/translate", "POST", 0.001, "Translate"),
        ("weather-current", "/google-weather/v1/current", "GET", 0.001, "Current weather"),
        ("weather-forecast-days", "/google-weather/v1/forecast/days", "GET", 0.001, "Daily forecast"),
        ("weather-forecast-hours", "/google-weather/v1/forecast/hours", "GET", 0.001, "Hourly forecast"),
        ("weather-history-hours", "/google-weather/v1/history/hours", "GET", 0.001, "Weather history"),
        ("ip-lookup", "/ip-stack/v1/lookup", "GET", 0.001, "IP lookup"),
        ("holidays-public", "/open-holidays/v1/public", "GET", 0.001, "Public holidays"),
        ("holidays-school", "/open-holidays/v1/school", "GET", 0.001, "School holidays"),
        ("holidays-subdivisions", "/open-holidays/v1/subdivisions", "GET", 0.001, "Subdivisions"),
        ("tavily-search", "/tavily/v1/search", "POST", None, "Tavily search"),
    ]
    out = []
    for row in rows:
        eid, path, method, price, desc = row
        note = "varies" if price is None else None
        out.append(ep(eid, method, f"{base}{path}", desc, price, note))
    return out


def twit_eps(base: str) -> list[dict]:
    paths = [
        ("articles-by-id", "/articles/by/id", 0.01),
        ("communities-by-id", "/communities/by/id", 0.0025),
        ("communities-members", "/communities/members", 0.01),
        ("communities-posts", "/communities/posts", 0.01),
        ("lists-by-id", "/lists/by/id", 0.0025),
        ("lists-followers", "/lists/followers", 0.01),
        ("lists-members", "/lists/members", 0.01),
        ("lists-tweets", "/lists/tweets", 0.01),
        ("tweets-bulk", "/tweets", 0.01),
        ("tweets-by-id", "/tweets/by/id", 0.0025),
        ("tweets-quote", "/tweets/quote_tweets", 0.01),
        ("tweets-replies", "/tweets/replies", 0.01),
        ("tweets-retweeted-by", "/tweets/retweeted_by", 0.01),
        ("tweets-search", "/tweets/search", 0.01),
        ("tweets-user", "/tweets/user", 0.01),
        ("users-bulk", "/users", 0.01),
        ("users-by-id", "/users/by/id", 0.005),
        ("users-by-username", "/users/by/username", 0.005),
        ("users-followers", "/users/followers", 0.01),
        ("users-following", "/users/following", 0.01),
        ("users-search", "/users/search", 0.01),
    ]
    return [
        ep(eid, "GET", f"{base}{path}", f"X/Twitter API {path}", price) for eid, path, price in paths
    ]


def aster_eps(base: str) -> list[dict]:
    rows = [
        ("deep-analysis-batch", "POST", "/v1/agent/deep-analysis/batch", 0.05, "Batch deep analysis"),
        ("ai-code-review", "POST", "/v1/ai/code-review", 0.05, "Code review"),
        ("ai-fact-check", "POST", "/v1/ai/fact-check", 0.01, "Fact-check"),
        ("ai-sentiment", "POST", "/v1/ai/sentiment", 0.004, "Sentiment"),
        ("ai-summarize", "POST", "/v1/ai/summarize", 0.004, "Summarize"),
        ("ai-translate", "POST", "/v1/ai/translate", 0.02, "Translate"),
        ("collect-settle", "POST", "/v1/collect/settle", 0.1, "Collect settlement"),
        ("crypto-whale-alerts", "GET", "/v1/crypto/whale-alerts", 0.02, "Whale alerts"),
        ("market-trending", "GET", "/v1/market/trending", 0.005, "Trending tokens"),
        ("util-pdf", "POST", "/v1/util/pdf-generate", 0.03, "HTML to PDF"),
        ("util-qr", "POST", "/v1/util/qr-code", None, "QR code"),
        ("util-screenshot", "POST", "/v1/util/screenshot", 0.02, "Web screenshot"),
        ("v2-fact-check", "POST", "/v2/x402/ai/fact-check", 0.01, "Fact-check v2"),
        ("v2-fact-check-deep", "POST", "/v2/x402/ai/fact-check/deep", 0.05, "Deep fact-check"),
        ("v2-sentiment-get", "GET", "/v2/x402/ai/sentiment", 0.01, "Sentiment GET"),
        ("v2-crypto-prices", "GET", "/v2/x402/crypto/prices", 0.005, "Crypto prices"),
        ("v2-offramp-estimate", "GET", "/v2/x402/offramp/estimate", 0.005, "USDC to EUR estimate"),
    ]
    out = []
    for eid, method, path, price, desc in rows:
        note = "varies" if price is None else None
        out.append(ep(eid, method, f"{base}{path}", desc, price, note))
    return out


def main() -> None:
    services = [
        {
            "id": "blackswan",
            "provider_id": "cdd05d2f-7a58-41c2-b33c-b9424132e68c",
            "name": "BlackSwan",
            "description": (
                "Real-time risk signals for autonomous trading and treasury agents. "
                "Flags rugs, exploits, and abnormal token behavior."
            ),
            "tags": ["crypto", "risk", "defi", "monitoring", "agent-infra", "mcp"],
            "network": "eip155:8453",
            "discover_url": DISCOVER.format(pid="cdd05d2f-7a58-41c2-b33c-b9424132e68c"),
            "base_url": "https://x402.blackswan.wtf",
            "agent_notes": (
                "GET / returns a free service manifest (200). Use POST on paid paths; "
                "preview paid routes before fetch."
            ),
            "endpoints": [
                ep(
                    "risk-feed",
                    "GET",
                    "https://x402.blackswan.wtf",
                    "Real-time risk feed (Flare/Core tiers).",
                    0.1,
                ),
                ep(
                    "flare-analysis",
                    "POST",
                    "https://x402.blackswan.wtf/smart-agents/flare",
                    "Flare-tier risk analysis for a smart agent target.",
                    0.01,
                ),
            ],
        },
        {
            "id": "einstein-ai",
            "provider_id": "96480614-83c5-45ef-bf57-be7aab7a7b31",
            "name": "Einstein AI",
            "description": (
                "On-chain market intelligence: whale tracking, smart-money, DEX analytics, "
                "MEV detection, and launchpad monitoring."
            ),
            "tags": ["crypto", "whales", "smart-money", "dex", "mev", "security", "launchpad"],
            "network": "eip155:8453",
            "discover_url": DISCOVER.format(pid="96480614-83c5-45ef-bf57-be7aab7a7b31"),
            "base_url": "https://emc2ai.io",
            "agent_notes": "Use POST with JSON body (prompt field). Ampersend UI may show GET; live API expects POST.",
            "endpoints": [
                ep(
                    "einstein-report",
                    "POST",
                    "https://emc2ai.io/x402/einstein/report",
                    "Investment-report agent with whale/smart-money/MEV signals.",
                    0.5,
                ),
            ],
        },
        {
            "id": "limitless-exchange",
            "provider_id": "75c4264b-c658-45d5-b5f5-37796b267772",
            "name": "Limitless Exchange",
            "description": "Prediction market CLOB on Base for agentic betting.",
            "tags": ["crypto", "prediction-market", "clob", "betting", "agentic", "payments"],
            "network": "eip155:8453",
            "discover_url": DISCOVER.format(pid="75c4264b-c658-45d5-b5f5-37796b267772"),
            "base_url": "https://server-production-d471.up.railway.app",
            "endpoints": [
                ep(
                    "place-bet",
                    "POST",
                    "https://server-production-d471.up.railway.app/place-bet",
                    "Place YES/NO bet (marketSlug, side).",
                    0.15,
                ),
                ep(
                    "withdraw",
                    "POST",
                    "https://server-production-d471.up.railway.app/withdraw",
                    "Withdraw USDC from sub-account.",
                    0.05,
                ),
            ],
        },
        {
            "id": "zapper",
            "provider_id": "653d67c8-bb4c-43f4-bdcd-d2c007d0b49e",
            "name": "Zapper",
            "description": "Multi-chain wallet, portfolio, DeFi, and NFT reads via x402.",
            "tags": ["crypto", "wallet", "portfolio", "tokens", "nft", "defi", "multi-chain"],
            "network": "eip155:8453",
            "discover_url": DISCOVER.format(pid="653d67c8-bb4c-43f4-bdcd-d2c007d0b49e"),
            "base_url": "https://public.zapper.xyz",
            "agent_notes": "All listed routes expect POST with JSON per Zapper x402 schema.",
            "endpoints": zapper_eps("https://public.zapper.xyz"),
        },
        {
            "id": "stableenrich",
            "provider_id": "fa4f8059-57f0-4b99-8f5c-9ba98ea9cb9a",
            "name": "StableEnrich",
            "description": "Multi-vendor people, places, search, and enrichment aggregator.",
            "tags": ["data", "search", "aggregator", "social", "people", "places", "enrichment"],
            "network": "eip155:8453",
            "discover_url": DISCOVER.format(pid="fa4f8059-57f0-4b99-8f5c-9ba98ea9cb9a"),
            "base_url": "https://stableenrich.dev",
            "endpoints": stableenrich_eps("https://stableenrich.dev"),
        },
        {
            "id": "auor-io",
            "provider_id": "88969f4e-280b-49c8-bc0c-b7cff0aa3c3c",
            "name": "Auor.io",
            "description": "Keyless gateway to maps, weather, travel, FX, and search APIs.",
            "tags": ["aggregator", "google-maps", "weather", "translate", "amadeus", "tavily"],
            "network": "eip155:8453",
            "discover_url": DISCOVER.format(pid="88969f4e-280b-49c8-bc0c-b7cff0aa3c3c"),
            "base_url": "https://api.auor.io",
            "endpoints": auor_eps("https://api.auor.io"),
        },
        {
            "id": "twit-sh",
            "provider_id": "fe787629-c9b0-4ec7-8000-f140816d9384",
            "name": "twit.sh",
            "description": "Real-time X (Twitter) data API.",
            "tags": ["data", "search", "twitter", "x", "social", "real-time"],
            "network": "eip155:8453",
            "discover_url": DISCOVER.format(pid="fe787629-c9b0-4ec7-8000-f140816d9384"),
            "base_url": "https://x402.twit.sh",
            "endpoints": twit_eps("https://x402.twit.sh"),
        },
        {
            "id": "laso-finance",
            "provider_id": "107daaea-c5e8-4c5d-9874-3de2f2ec33f8",
            "name": "Laso Finance",
            "description": "Stablecoin to prepaid cards, gift cards, Venmo, and PayPal.",
            "tags": ["payments", "prepaid-card", "gift-cards", "venmo", "paypal", "no-kyc"],
            "network": "eip155:8453",
            "discover_url": DISCOVER.format(pid="107daaea-c5e8-4c5d-9874-3de2f2ec33f8"),
            "base_url": "https://laso.finance",
            "agent_notes": (
                "Push-to-card is about $10.48 USDC — above default x402_max_price_usd ($5). "
                "Raise the cap before calling that endpoint."
            ),
            "endpoints": [
                ep("auth", "GET", "https://laso.finance/auth", "Auth handshake", None, "varies"),
                ep("get-card", "GET", "https://laso.finance/get-card", "Mint prepaid card", None, "varies"),
                ep(
                    "get-push-to-card",
                    "GET",
                    "https://laso.finance/get-push-to-card",
                    "Push-to-card (USD/EUR/GBP).",
                    10.48,
                ),
                ep(
                    "order-gift-card",
                    "GET",
                    "https://laso.finance/order-gift-card",
                    "Order gift card",
                    None,
                    "varies",
                ),
            ],
        },
        {
            "id": "asterpay",
            "provider_id": "a06d5dd3-fe8c-4361-a65b-442d91075fa1",
            "name": "AsterPay",
            "description": "Stablecoin settlement, AI utilities, and market data.",
            "tags": ["payments", "settlement", "sepa", "eur", "mica", "compliance", "kya"],
            "network": "eip155:8453",
            "discover_url": DISCOVER.format(pid="a06d5dd3-fe8c-4361-a65b-442d91075fa1"),
            "base_url": "https://x402.asterpay.io",
            "endpoints": aster_eps("https://x402.asterpay.io"),
        },
        {
            "id": "grove-api",
            "provider_id": "76dc2f57-bfdd-485b-8d9b-bc6ecf1dccbb",
            "name": "Grove API",
            "description": "Fund Grove tipping accounts for creator payments.",
            "tags": ["payments", "tipping", "creator", "a2a", "mcp", "self-fund"],
            "network": "eip155:8453",
            "discover_url": DISCOVER.format(pid="76dc2f57-bfdd-485b-8d9b-bc6ecf1dccbb"),
            "base_url": "https://api.grove.city",
            "endpoints": [
                ep(
                    "fund",
                    "POST",
                    "https://api.grove.city/v1/fund",
                    "Self-fund Grove tipping account (min $1 USDC).",
                    1.0,
                ),
            ],
        },
        {
            "id": "pinata-x402",
            "provider_id": "676e8944-4b2c-4cbc-95c6-11c44f2aa069",
            "name": "Pinata x402",
            "description": "Account-free IPFS pin and retrieve.",
            "tags": ["storage", "ipfs", "pin", "retrieve"],
            "network": "eip155:8453",
            "discover_url": DISCOVER.format(pid="676e8944-4b2c-4cbc-95c6-11c44f2aa069"),
            "base_url": "https://402.pinata.cloud",
            "endpoints": [
                ep(
                    "pin-private",
                    "POST",
                    "https://402.pinata.cloud/v1/pin/private",
                    "Pin private content.",
                    0.001,
                ),
                ep(
                    "pin-public",
                    "POST",
                    "https://402.pinata.cloud/v1/pin/public",
                    "Pin public content.",
                    0.001,
                ),
                ep(
                    "retrieve-private",
                    "GET",
                    "https://402.pinata.cloud/v1/retrieve/private/{cid}",
                    "Retrieve private CID (replace {cid}).",
                    0.001,
                ),
            ],
        },
        {
            "id": "cybercentry",
            "provider_id": "27b3529e-10c5-4d8b-9206-00e24ee1e8ec",
            "name": "Cybercentry",
            "description": "Security consultant and on-chain / code verification agents.",
            "tags": ["security", "compliance", "verify", "ethereum", "solana", "solidity"],
            "network": "eip155:8453",
            "discover_url": DISCOVER.format(pid="27b3529e-10c5-4d8b-9206-00e24ee1e8ec"),
            "base_url": "https://x402-cybercentry-cyber-security-consultant.up.railway.app",
            "endpoints": [
                ep(
                    "consultant-query",
                    "POST",
                    "https://x402-cybercentry-cyber-security-consultant.up.railway.app/query",
                    "Generalist security consultant.",
                    0.02,
                ),
                ep(
                    "verify-ethereum-token",
                    "POST",
                    "https://x402-cybercentry-ethereum-token-verification.up.railway.app/verify",
                    "Verify Ethereum token.",
                    0.02,
                ),
                ep(
                    "verify-private-data",
                    "POST",
                    "https://x402-cybercentry-private-data-verification.up.railway.app/verify",
                    "Verify private data.",
                    0.02,
                ),
                ep(
                    "verify-solidity",
                    "POST",
                    "https://x402-cybercentry-solidity-code-verification.up.railway.app/verify",
                    "Verify Solidity code.",
                    0.02,
                ),
            ],
        },
    ]

    doc = {"version": "2026-06-12-amp-v1", "services": services}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUT} ({len(services)} services)")


if __name__ == "__main__":
    main()
