#!/usr/bin/env python3
# ruff: noqa: E501
"""Scrape Ampersend discover pages into x402_services.json (requires Playwright).

Run ad hoc (Playwright is not a package dependency):

  uv run --with playwright scripts/sync_x402_services_from_ampersend.py

Then review diff and run:

  uv run pytest tests/test_x402_catalog.py -q
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "src" / "aurey" / "data" / "x402_services.json"

DEFAULT_PROVIDER_IDS = [
    "cdd05d2f-7a58-41c2-b33c-b9424132e68c",
    "96480614-83c5-45ef-bf57-be7aab7a7b31",
    "75c4264b-c658-45d5-b5f5-37796b267772",
    "653d67c8-bb4c-43f4-bdcd-d2c007d0b49e",
    "fa4f8059-57f0-4b99-8f5c-9ba98ea9cb9a",
    "88969f4e-280b-49c8-bc0c-b7cff0aa3c3c",
    "fe787629-c9b0-4ec7-8000-f140816d9384",
    "107daaea-c5e8-4c5d-9874-3de2f2ec33f8",
    "a06d5dd3-fe8c-4361-a65b-442d91075fa1",
    "76dc2f57-bfdd-485b-8d9b-bc6ecf1dccbb",
    "676e8944-4b2c-4cbc-95c6-11c44f2aa069",
    "27b3529e-10c5-4d8b-9206-00e24ee1e8ec",
]

DISCOVER = "https://app.ampersend.ai/discover/agent/{pid}"


def _slug(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return s or "service"


def _parse_price(text: str) -> tuple[float | None, str | None]:
    t = text.strip().lower()
    if "varies" in t or not t:
        return None, "varies"
    m = re.search(r"\$?\s*([0-9]+(?:\.[0-9]+)?)", text)
    if not m:
        return None, "varies"
    return float(m.group(1)), None


def scrape_page(page, provider_id: str) -> dict:
    url = DISCOVER.format(pid=provider_id)
    page.goto(url, wait_until="networkidle", timeout=60_000)
    text = page.inner_text("body")

    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    name = ""
    description = ""
    tags: list[str] = []
    base_url = ""
    endpoints: list[dict] = []

    for i, ln in enumerate(lines):
        if ln == "Back to Marketplace" and i + 1 < len(lines):
            name = lines[i + 1]
        if ln.startswith("http") and "ampersend" not in ln and not base_url:
            if "SERVICE ENDPOINTS" in text and ln in text.split("SERVICE ENDPOINTS")[1].split("GET STARTED")[0]:
                base_url = ln.rstrip("/")

    if name:
        idx = text.find(name)
        if idx >= 0:
            chunk = text[idx + len(name) : idx + len(name) + 600]
            desc_lines = []
            for ln in chunk.splitlines():
                ln = ln.strip()
                if not ln or ln.startswith("http") or ln in {"Crypto", "GET STARTED"}:
                    break
                if ln.isupper() and len(ln) < 40:
                    break
                if re.match(r"^[A-Za-z0-9_-]+$", ln) and " " not in ln and len(ln) < 24:
                    tags.append(ln.lower())
                    continue
                desc_lines.append(ln)
            description = " ".join(desc_lines).strip()

    # Table rows after "Endpoints ("
    in_table = False
    for ln in lines:
        if ln.startswith("Endpoints ("):
            in_table = True
            continue
        if not in_table:
            continue
        if ln in {"Method", "Path", "Description", "Price"}:
            continue
        if ln.startswith("GET STARTED"):
            break
        if ln.startswith("http"):
            continue
        # Heuristic: method line followed by path/price in UI order varies; use inner_text table via locators
        pass

    rows = page.locator("table tbody tr").all()
    for row in rows:
        cells = [c.inner_text().strip() for c in row.locator("td").all()]
        if len(cells) < 3:
            continue
        method = cells[0].split()[0].upper() if cells[0] else "GET"
        path_or_url = cells[1].strip()
        desc = cells[2].strip() if len(cells) > 2 else ""
        price_raw = cells[3].strip() if len(cells) > 3 else ""
        price, note = _parse_price(price_raw)
        if path_or_url.startswith("http"):
            full_url = path_or_url
        elif path_or_url.startswith("/"):
            full_url = f"{base_url.rstrip('/')}{path_or_url}" if base_url else path_or_url
        else:
            full_url = f"{base_url.rstrip('/')}/{path_or_url}" if base_url else path_or_url
        eid = _slug(path_or_url.split("/")[-1] or name)
        endpoints.append(
            {
                "id": eid,
                "method": method,
                "url": full_url,
                "description": desc,
                "price_usd_min": price,
                "price_note": note,
            }
        )

    return {
        "id": _slug(name),
        "provider_id": provider_id,
        "name": name or provider_id,
        "description": description,
        "tags": tags,
        "network": "eip155:8453",
        "discover_url": url,
        "base_url": base_url,
        "endpoints": endpoints,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--provider-id",
        action="append",
        dest="provider_ids",
        help="Ampersend provider UUID (repeatable). Defaults to bundled marketplace list.",
    )
    parser.add_argument(
        "--merge-seed",
        action="store_true",
        help="After scrape, merge agent_notes from scripts/build_x402_services_seed.py output if missing.",
    )
    args = parser.parse_args()
    ids = args.provider_ids or DEFAULT_PROVIDER_IDS

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Install Playwright: uv run --with playwright …", file=sys.stderr)
        return 1

    services: list[dict] = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        for pid in ids:
            print(f"Scraping {pid}…")
            try:
                services.append(scrape_page(page, pid))
            except Exception as exc:
                print(f"  failed: {exc}", file=sys.stderr)
        browser.close()

    if args.merge_seed:
        import subprocess

        subprocess.run([sys.executable, str(ROOT / "scripts" / "build_x402_services_seed.py")], check=True)
        seed = json.loads(OUT.read_text(encoding="utf-8"))
        notes = {s["provider_id"]: s.get("agent_notes") for s in seed.get("services", [])}
        for svc in services:
            if not svc.get("agent_notes"):
                svc["agent_notes"] = notes.get(svc["provider_id"])

    doc = {"version": "amp-scrape", "services": services}
    OUT.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUT} ({len(services)} services). Review before commit.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
