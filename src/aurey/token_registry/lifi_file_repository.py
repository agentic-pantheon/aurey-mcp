"""Lazy indexed token registry from a local LiFi ``/v1/tokens`` export."""

from __future__ import annotations

import json
import logging
import threading
from pathlib import Path
from typing import Any

from aurey.graphs.chains import CHAIN_INDEX, chain_id_for
from aurey.known_addresses.book import iter_catalog_tokens
from aurey.token_registry.lifi_catalog import iter_lifi_catalog_entries
from aurey.token_registry.lifi_import import load_lifi_tokens_file
from aurey.token_registry.repository import TokenRow

_log = logging.getLogger(__name__)

_ALLOWLIST_TIERS = frozenset({"curated", "indexed"})


def build_token_registry_repository(*, lifi_tokens_path: Path | None) -> LifiFileTokenRegistryRepository | InMemoryFallback:
    """Standalone MCP registry: bundled curated rows plus LiFi catalog (bundled or override path)."""

    if lifi_tokens_path is not None and (lifi_tokens_path.is_file() or lifi_tokens_path.is_dir()):
        return LifiFileTokenRegistryRepository(lifi_tokens_path)
    if lifi_tokens_path is not None:
        _log.warning("LiFi tokens catalog not found: %s — using curated catalog only.", lifi_tokens_path)
    return InMemoryFallback()


class InMemoryFallback:
    """Same surface as :class:`LifiFileTokenRegistryRepository` without a LiFi file."""

    def __init__(self) -> None:
        self._by_address: dict[tuple[str, str], TokenRow] = {}
        self._by_symbol: dict[tuple[str, str], TokenRow] = {}
        self._by_name: dict[tuple[str, str], TokenRow] = {}
        self._seed_curated()

    @property
    def loaded_chain_slugs(self) -> frozenset[str]:
        return frozenset()

    def _seed_curated(self) -> None:
        for chain_slug, symbol, name, address in iter_catalog_tokens():
            row = _curated_row(chain_slug, symbol, name, address)
            self._insert_row(row, overwrite=True)

    def _insert_row(self, row: TokenRow, *, overwrite: bool) -> None:
        addr_key = (row.chain_slug, row.address.lower())
        if not overwrite and addr_key in self._by_address:
            existing = self._by_address[addr_key]
            if existing.trust_tier == "curated":
                return
        self._by_address[addr_key] = row
        self._refresh_symbol_index_for_chain(row.chain_slug)
        name_key = (row.chain_slug, row.name.strip().lower())
        if name_key not in self._by_name:
            self._by_name[name_key] = row

    def _refresh_symbol_index_for_chain(self, chain_slug: str) -> None:
        slug = chain_slug.strip().lower()
        sym_groups: dict[str, list[TokenRow]] = {}
        for row in self._by_address.values():
            if row.chain_slug != slug or row.trust_tier not in _ALLOWLIST_TIERS:
                continue
            sym_groups.setdefault(row.symbol.upper(), []).append(row)
        for sym, rows in sym_groups.items():
            key = (slug, sym)
            if len(rows) == 1:
                self._by_symbol[key] = rows[0]
            else:
                self._by_symbol.pop(key, None)

    def lookup_symbol(self, chain_slug: str, symbol: str) -> TokenRow | None:
        slug = chain_slug.strip().lower()
        needle = symbol.strip().upper()
        hit = self._by_symbol.get((slug, needle))
        if hit is not None and hit.symbol.upper() == needle:
            return hit
        matches = [r for r in self._by_address.values() if r.chain_slug == slug and r.symbol.upper() == needle]
        if len(matches) == 1:
            return matches[0]
        return None

    def lookup_name(self, chain_slug: str, token_name: str) -> TokenRow | None:
        slug = chain_slug.strip().lower()
        target = token_name.strip().lower()
        hit = self._by_name.get((slug, target))
        if hit is not None:
            return hit
        matches = [r for r in self._by_address.values() if r.chain_slug == slug and r.name.strip().lower() == target]
        if len(matches) == 1:
            return matches[0]
        return None

    def lookup_address(self, chain_slug: str, address: str) -> TokenRow | None:
        slug = chain_slug.strip().lower()
        return self._by_address.get((slug, address.strip().lower()))

    def list_allowlist_rows(self, *, chain_slug: str | None = None) -> list[TokenRow]:
        rows = [r for r in self._by_address.values() if r.trust_tier in _ALLOWLIST_TIERS]
        if chain_slug is None:
            return rows
        slug = chain_slug.strip().lower()
        return [r for r in rows if r.chain_slug == slug]

    def upsert_discovered(
        self,
        *,
        chain_slug: str,
        symbol: str,
        name: str,
        address: str,
        decimals: int | None,
        coingecko_id: str | None,
        cg_recognized: bool,
        chain_id: int | None = None,
        source: str = "on_demand",
        trust_tier: str = "discovered",
        verified_onchain: bool = True,
        lifi_supported: bool = False,
    ) -> TokenRow:
        slug = chain_slug.strip().lower()
        cid = chain_id if chain_id is not None else chain_id_for(slug)
        row = TokenRow(
            chain_slug=slug,
            chain_id=cid,
            symbol=symbol.strip().upper()[:32],
            name=name[:255],
            address=address,
            decimals=decimals,
            coingecko_id=coingecko_id,
            source=source,
            trust_tier=trust_tier,
            verified_onchain=verified_onchain,
            cg_recognized=cg_recognized,
            lifi_supported=lifi_supported,
        )
        self._by_address[(slug, row.address.lower())] = row
        return row


class LifiFileTokenRegistryRepository(InMemoryFallback):
    """Curated seed + LiFi catalog loaded per chain on first use (indexed)."""

    def __init__(self, path: Path) -> None:
        super().__init__()
        self._lifi_path = path
        self._load_lock = threading.Lock()
        self._monolith_payload: dict[str, Any] | None = None
        self._lifi_chain_loaded: set[str] = set()

    @property
    def loaded_chain_slugs(self) -> frozenset[str]:
        return frozenset(self._lifi_chain_loaded)

    def _ensure_chain_loaded(self, chain_slug: str) -> None:
        slug = chain_slug.strip().lower()
        if slug in self._lifi_chain_loaded:
            return
        with self._load_lock:
            if slug in self._lifi_chain_loaded:
                return
            cid = chain_id_for(slug)
            if cid is None:
                self._lifi_chain_loaded.add(slug)
                return
            items = self._read_chain_token_items(cid)
            count = 0
            if items:
                payload = {"tokens": {str(cid): items}}
                for entry in iter_lifi_catalog_entries(payload):
                    row = TokenRow(
                        chain_slug=entry.chain_slug,
                        chain_id=entry.chain_id,
                        symbol=entry.symbol,
                        name=entry.name,
                        address=entry.address,
                        decimals=entry.decimals,
                        coingecko_id=None,
                        source="lifi_catalog",
                        trust_tier="indexed",
                        verified_onchain=True,
                        cg_recognized=False,
                        lifi_supported=True,
                        ecosystem=entry.ecosystem,
                    )
                    self._insert_lifi_row(row)
                    count += 1
                self._refresh_symbol_index_for_chain(slug)
            if count:
                _log.info(
                    "Loaded %s LiFi tokens for chain %s from %s (per-chain lazy).",
                    count,
                    slug,
                    self._lifi_path,
                )
            self._lifi_chain_loaded.add(slug)

    def _read_chain_token_items(self, chain_id: int) -> list[dict[str, Any]]:
        if self._lifi_path.is_dir():
            shard = self._lifi_path / f"{chain_id}.json"
            if not shard.is_file():
                return []
            raw = json.loads(shard.read_text(encoding="utf-8"))
            if not isinstance(raw, list):
                return []
            return [item for item in raw if isinstance(item, dict)]
        if not self._lifi_path.is_file():
            return []
        if self._monolith_payload is None:
            self._monolith_payload = load_lifi_tokens_file(self._lifi_path)
        root = self._monolith_payload.get("tokens")
        if not isinstance(root, dict):
            return []
        entries = root.get(str(chain_id))
        if not isinstance(entries, list):
            return []
        return [item for item in entries if isinstance(item, dict)]

    def _insert_lifi_row(self, row: TokenRow) -> None:
        addr_key = (row.chain_slug, row.address.lower())
        existing = self._by_address.get(addr_key)
        if existing is not None and existing.trust_tier == "curated":
            if not existing.lifi_supported:
                self._by_address[addr_key] = TokenRow(
                    chain_slug=existing.chain_slug,
                    chain_id=existing.chain_id,
                    symbol=existing.symbol,
                    name=existing.name,
                    address=existing.address,
                    decimals=existing.decimals or row.decimals,
                    coingecko_id=existing.coingecko_id,
                    source=existing.source,
                    trust_tier=existing.trust_tier,
                    verified_onchain=existing.verified_onchain,
                    cg_recognized=existing.cg_recognized,
                    lifi_supported=True,
                    ecosystem=existing.ecosystem,
                )
            return
        self._by_address[addr_key] = row
        name_key = (row.chain_slug, row.name.strip().lower())
        if name_key not in self._by_name:
            self._by_name[name_key] = row

    def _ensure_all_catalog_chains_loaded(self) -> None:
        for slug in CHAIN_INDEX:
            self._ensure_chain_loaded(slug)

    def lookup_symbol(self, chain_slug: str, symbol: str) -> TokenRow | None:
        self._ensure_chain_loaded(chain_slug)
        return super().lookup_symbol(chain_slug, symbol)

    def lookup_name(self, chain_slug: str, token_name: str) -> TokenRow | None:
        self._ensure_chain_loaded(chain_slug)
        return super().lookup_name(chain_slug, token_name)

    def lookup_address(self, chain_slug: str, address: str) -> TokenRow | None:
        self._ensure_chain_loaded(chain_slug)
        return super().lookup_address(chain_slug, address)

    def list_allowlist_rows(self, *, chain_slug: str | None = None) -> list[TokenRow]:
        if chain_slug is not None:
            self._ensure_chain_loaded(chain_slug)
        else:
            self._ensure_all_catalog_chains_loaded()
        return super().list_allowlist_rows(chain_slug=chain_slug)


def _curated_row(chain_slug: str, symbol: str, name: str, address: str) -> TokenRow:
    return TokenRow(
        chain_slug=chain_slug,
        chain_id=chain_id_for(chain_slug),
        symbol=symbol,
        name=name,
        address=address,
        decimals=None,
        coingecko_id=None,
        source="known_addresses",
        trust_tier="curated",
        verified_onchain=True,
        cg_recognized=False,
        lifi_supported=False,
    )


__all__ = ["LifiFileTokenRegistryRepository", "build_token_registry_repository"]
