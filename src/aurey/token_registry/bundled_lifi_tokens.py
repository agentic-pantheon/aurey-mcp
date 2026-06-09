"""Per-chain LiFi token shards + catalog path helpers."""

from __future__ import annotations

from functools import lru_cache
from importlib.resources import files
from pathlib import Path

_CATALOG_DIR_NAME = "lifi_tokens"
_LEGACY_MONOLITH = "li_quest_tokens.json"


@lru_cache(maxsize=1)
def default_bundled_lifi_tokens_catalog_path() -> Path:
    """Directory of ``{chain_id}.json`` shards shipped in ``aurey.data``."""

    ref = files("aurey.data").joinpath(_CATALOG_DIR_NAME)
    return Path(str(ref))


def default_bundled_lifi_tokens_path() -> Path:
    """Backward-compatible alias for :func:`default_bundled_lifi_tokens_catalog_path`."""

    return default_bundled_lifi_tokens_catalog_path()


def bundled_lifi_tokens_available() -> bool:
    try:
        catalog = default_bundled_lifi_tokens_catalog_path()
        if catalog.is_dir() and any(catalog.glob("[0-9]*.json")):
            return True
        legacy = Path(str(files("aurey.data").joinpath(_LEGACY_MONOLITH)))
        return legacy.is_file()
    except (FileNotFoundError, ModuleNotFoundError, ValueError):
        return False


def resolve_lifi_catalog_path(path: Path) -> Path:
    """Normalize user path to a catalog directory or monolith file."""

    return path.expanduser()


__all__ = [
    "bundled_lifi_tokens_available",
    "default_bundled_lifi_tokens_catalog_path",
    "default_bundled_lifi_tokens_path",
    "resolve_lifi_catalog_path",
]
