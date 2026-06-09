"""Parse 1Claw signing-keys API and bootstrap JSON for agent wallet addresses."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from aurey.graphs.evm_codec import to_checksum_evm_address


def _dig_mapping(payload: Mapping[str, Any], *keys: str) -> Any:
    cur: Any = payload
    for k in keys:
        if not isinstance(cur, Mapping):
            return None
        cur = cur.get(k)
    return cur


def _signing_keys_list_candidates(payload: Any) -> list[Any]:
    if not isinstance(payload, Mapping):
        return []
    keys_paths: list[tuple[str, ...]] = (
        ("summary", "signing_keys"),
        ("data", "summary", "signing_keys"),
        ("signing_keys",),
        ("data", "signing_keys"),
    )
    out: list[Any] = []
    for path in keys_paths:
        node = _dig_mapping(payload, *path)
        if isinstance(node, list):
            out.append(node)
    return out


def _chain_label_ethereum(chain: Any) -> bool:
    if isinstance(chain, str):
        c = chain.strip().lower()
        if not c:
            return False
        if c in {"ethereum", "eth"}:
            return True
        if "eip155" in c:
            suffix = c.split(":")[-1]
            try:
                return int(suffix) == 1
            except ValueError:
                pass
            return "ethereum" in c
        return False
    return False


def _chain_label_solana(chain: Any) -> bool:
    if isinstance(chain, str):
        c = chain.strip().lower()
        if not c:
            return False
        return c == "solana" or c == "sol" or c.startswith("solana:")
    return False


def extract_ethereum_address_from_signing_key_items(items: Any) -> str | None:
    if not isinstance(items, list):
        return None
    eth_items: list[Mapping[str, Any]] = []
    for item in items:
        if not isinstance(item, Mapping):
            continue
        chain = item.get("chain") or item.get("chain_slug") or item.get("chainSlug")
        if _chain_label_ethereum(chain):
            eth_items.append(item)
    cand = eth_items if eth_items else [x for x in items if isinstance(x, Mapping)]

    for item in cand:
        if not isinstance(item, Mapping):
            continue
        raw = item.get("address") or item.get("evm_address")
        addr = raw if isinstance(raw, str) else None
        if not addr or not addr.strip():
            continue
        try:
            return to_checksum_evm_address(addr.strip())
        except ValueError:
            continue
    return None


def extract_solana_address_from_signing_key_items(items: Any) -> str | None:
    if not isinstance(items, list):
        return None
    for item in items:
        if not isinstance(item, Mapping):
            continue
        chain = item.get("chain") or item.get("chain_slug") or item.get("chainSlug")
        if not _chain_label_solana(chain):
            continue
        raw = item.get("address") or item.get("solana_address")
        if isinstance(raw, str) and raw.strip():
            return raw.strip()
    return None


def extract_signing_keys_array_from_api(payload: Any) -> list[Any] | None:
    if isinstance(payload, list):
        return payload
    if not isinstance(payload, Mapping):
        return None
    keys = payload.get("keys")
    if isinstance(keys, list):
        return keys
    inner = payload.get("data")
    if isinstance(inner, Mapping):
        keys2 = inner.get("keys")
        if isinstance(keys2, list):
            return keys2
    return None


def ethereum_address_from_signing_keys_payload(payload: Any) -> str | None:
    arr = extract_signing_keys_array_from_api(payload)
    if arr is None:
        for lst in _signing_keys_list_candidates(payload):
            found = extract_ethereum_address_from_signing_key_items(lst)
            if found is not None:
                return found
        return None
    return extract_ethereum_address_from_signing_key_items(arr)


def solana_address_from_signing_keys_payload(payload: Any) -> str | None:
    arr = extract_signing_keys_array_from_api(payload)
    if arr is None:
        for lst in _signing_keys_list_candidates(payload):
            found = extract_solana_address_from_signing_key_items(lst)
            if found is not None:
                return found
        return None
    return extract_solana_address_from_signing_key_items(arr)


__all__ = [
    "ethereum_address_from_signing_keys_payload",
    "solana_address_from_signing_keys_payload",
]
