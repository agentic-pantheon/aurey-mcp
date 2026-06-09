"""In-memory token registry for standalone MCP installs (no Postgres)."""

from __future__ import annotations

from aurey.known_addresses.book import iter_catalog_tokens
from aurey.graphs.chains import chain_id_for
from aurey.token_registry.repository import TokenRow


class InMemoryTokenRegistryRepository:
    """Curated known-address rows plus optional discovered-token cache."""

    def __init__(self) -> None:
        self._by_address: dict[tuple[str, str], TokenRow] = {}
        self._seed_curated()

    def _seed_curated(self) -> None:
        for chain_slug, symbol, name, address in iter_catalog_tokens():
            cid = chain_id_for(chain_slug)
            row = TokenRow(
                chain_slug=chain_slug,
                chain_id=cid,
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
            self._by_address[(row.chain_slug, row.address.lower())] = row

    def lookup_symbol(self, chain_slug: str, symbol: str) -> TokenRow | None:
        slug = chain_slug.strip().lower()
        needle = symbol.strip().upper()
        for row in self._by_address.values():
            if row.chain_slug == slug and row.symbol.upper() == needle:
                return row
        return None

    def lookup_name(self, chain_slug: str, token_name: str) -> TokenRow | None:
        slug = chain_slug.strip().lower()
        target = token_name.strip().lower()
        for row in self._by_address.values():
            if row.chain_slug == slug and row.name.strip().lower() == target:
                return row
        return None

    def lookup_address(self, chain_slug: str, address: str) -> TokenRow | None:
        slug = chain_slug.strip().lower()
        return self._by_address.get((slug, address.strip().lower()))

    def list_allowlist_rows(self, *, chain_slug: str | None = None) -> list[TokenRow]:
        rows = list(self._by_address.values())
        if chain_slug is None:
            return rows
        slug = chain_slug.strip().lower()
        return [r for r in rows if r.chain_slug == slug]

    def upsert_discovered(
        self,
        *,
        chain_slug: str,
        chain_id: int | None,
        symbol: str,
        name: str,
        address: str,
        decimals: int | None,
        coingecko_id: str | None,
        source: str,
        trust_tier: str,
        verified_onchain: bool,
        cg_recognized: bool,
        lifi_supported: bool = False,
    ) -> TokenRow:
        row = TokenRow(
            chain_slug=chain_slug,
            chain_id=chain_id,
            symbol=symbol,
            name=name,
            address=address,
            decimals=decimals,
            coingecko_id=coingecko_id,
            source=source,
            trust_tier=trust_tier,
            verified_onchain=verified_onchain,
            cg_recognized=cg_recognized,
            lifi_supported=lifi_supported,
        )
        self._by_address[(row.chain_slug, row.address.lower())] = row
        return row
