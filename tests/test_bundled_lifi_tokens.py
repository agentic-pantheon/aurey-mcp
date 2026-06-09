"""Bundled LiFi token catalog shipped with the MCP package."""

from __future__ import annotations

from aurey.settings import AureySettings
from aurey.token_registry.bundled_lifi_tokens import (
    bundled_lifi_tokens_available,
    default_bundled_lifi_tokens_catalog_path,
)
from aurey.token_registry.lifi_file_repository import (
    LifiFileTokenRegistryRepository,
    build_token_registry_repository,
)


def test_bundled_lifi_shards_are_packaged() -> None:
    assert bundled_lifi_tokens_available()
    catalog = default_bundled_lifi_tokens_catalog_path()
    assert catalog.is_dir()
    assert (catalog / "8453.json").is_file()


def test_default_settings_use_bundled_catalog() -> None:
    settings = AureySettings(
        lifi_tokens_path=None,
        bundled_lifi_tokens_enabled=True,
    )
    assert settings.uses_lifi_token_catalog()
    repo = build_token_registry_repository(lifi_tokens_path=settings.effective_lifi_tokens_path())
    assert isinstance(repo, LifiFileTokenRegistryRepository)
    row = repo.lookup_symbol("base", "USDC")
    assert row is not None
    assert row.lifi_supported is True


def test_per_chain_lazy_load_does_not_load_other_chains() -> None:
    settings = AureySettings(bundled_lifi_tokens_enabled=True)
    repo = build_token_registry_repository(lifi_tokens_path=settings.effective_lifi_tokens_path())
    assert isinstance(repo, LifiFileTokenRegistryRepository)
    repo.lookup_symbol("base", "WETH")
    assert "base" in repo.loaded_chain_slugs
    assert "ethereum" not in repo.loaded_chain_slugs
