#!/usr/bin/env python3
"""Refresh bundled LiFi token shards under ``src/aurey/data/lifi_tokens/``.

Each Aurey EVM chain gets ``{chain_id}.json`` (array of LiFi token objects). Chains are
loaded lazily by MCP at runtime.

Examples::

  uv run python scripts/sync_bundled_lifi_tokens.py --from-file ~/hosted-aurey/li_quest_tokens.json
  uv run python scripts/sync_bundled_lifi_tokens.py --fetch
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

OUT_DIR = ROOT / "src" / "aurey" / "data" / "lifi_tokens"
LEGACY_MONOLITH = ROOT / "src" / "aurey" / "data" / "li_quest_tokens.json"


def _filter_payload(payload: dict) -> dict[str, list]:
    from aurey.graphs.chains import CHAIN_INDEX

    tokens_root = payload.get("tokens")
    if not isinstance(tokens_root, dict):
        raise ValueError("Expected LiFi payload with a 'tokens' object.")

    allowed = {str(info.chain_id) for info in CHAIN_INDEX.values()}
    filtered: dict[str, list] = {}
    for chain_key, entries in tokens_root.items():
        if chain_key not in allowed:
            continue
        if isinstance(entries, list):
            filtered[chain_key] = entries
    return filtered


def _write_shards(chains: dict[str, list]) -> tuple[int, int, int]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for old in OUT_DIR.glob("*.json"):
        old.unlink()
    token_count = 0
    bytes_written = 0
    for chain_id, entries in sorted(chains.items(), key=lambda kv: int(kv[0])):
        out = OUT_DIR / f"{chain_id}.json"
        body = json.dumps(entries, separators=(",", ":"))
        out.write_text(body, encoding="utf-8")
        token_count += len(entries)
        bytes_written += out.stat().st_size
    manifest = {
        "version": 1,
        "chain_ids": sorted(chains.keys(), key=int),
    }
    manifest_path = OUT_DIR / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    bytes_written += manifest_path.stat().st_size
    return len(chains), token_count, bytes_written


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--from-file",
        type=Path,
        help="Local LiFi GET /v1/tokens JSON",
    )
    parser.add_argument(
        "--fetch",
        action="store_true",
        help="Download from https://li.quest/v1/tokens",
    )
    parser.add_argument(
        "--keep-monolith",
        action="store_true",
        help="Also write legacy src/aurey/data/li_quest_tokens.json (not used by MCP).",
    )
    args = parser.parse_args()

    if args.from_file:
        raw = json.loads(args.from_file.expanduser().read_text(encoding="utf-8"))
    else:
        from aurey.service.adapters import UrllibHttpJsonClient
        from aurey.token_registry.lifi_tokens import fetch_lifi_tokens_payload

        http = UrllibHttpJsonClient(timeout_s=120.0)
        raw = fetch_lifi_tokens_payload(http)

    chains = _filter_payload(raw)
    chain_count, token_count, nbytes = _write_shards(chains)
    print(
        f"Wrote {OUT_DIR} ({chain_count} chains, {token_count} tokens, {nbytes} bytes total)"
    )
    if args.keep_monolith:
        LEGACY_MONOLITH.parent.mkdir(parents=True, exist_ok=True)
        LEGACY_MONOLITH.write_text(
            json.dumps({"tokens": chains}, separators=(",", ":")),
            encoding="utf-8",
        )
        print(f"Wrote legacy monolith {LEGACY_MONOLITH}")
    elif LEGACY_MONOLITH.is_file():
        LEGACY_MONOLITH.unlink()
        print(f"Removed legacy monolith {LEGACY_MONOLITH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
