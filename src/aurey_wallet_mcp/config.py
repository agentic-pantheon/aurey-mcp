"""Load plugin configuration from env and optional ``~/.aurey/config.toml``."""

from __future__ import annotations

import os
from pathlib import Path

from aurey.settings import AureySettings


def default_config_path() -> Path:
    return Path.home() / ".aurey" / "config.toml"


def apply_toml_to_env(path: Path) -> None:
    """Parse simple TOML key=value sections into ``AUREY_*`` env vars (non-destructive)."""

    if not path.is_file():
        return
    try:
        import tomllib
    except ImportError:
        import tomli as tomllib  # type: ignore[no-redef]

    data = tomllib.loads(path.read_text(encoding="utf-8"))
    flat: dict[str, str] = {}

    def walk(prefix: str, obj: object) -> None:
        if isinstance(obj, dict):
            for k, v in obj.items():
                walk(f"{prefix}.{k}" if prefix else str(k), v)
        elif isinstance(obj, (str, int, float, bool)):
            flat[prefix.upper()] = str(obj).lower() if isinstance(obj, bool) else str(obj)

    walk("", data)
    aliases = {
        "ONECLAW.VAULT_ID": "AUREY_ONECLAW_VAULT_ID",
        "ONECLAW.AGENT_ID": "AUREY_ONECLAW_AGENT_ID",
        "WALLET.DEEP_AGENT_WALLET_ADDRESS": "AUREY_DEEP_AGENT_WALLET_ADDRESS",
        "WALLET.EVM_SIGNING_MODE": "AUREY_EVM_SIGNING_MODE",
        "PROVIDERS.ALCHEMY_API_KEY": "AUREY_ALCHEMY_API_KEY",
        "PROVIDERS.ALCHEMY_SECRET_PATH": "AUREY_ALCHEMY_API_SECRET_PATH",
        "PROVIDERS.ZERION_API_KEY": "AUREY_ZERION_API_KEY",
        "PROVIDERS.ZERION_API_SECRET_PATH": "AUREY_ZERION_API_SECRET_PATH",
        "ROUTING.ROUTE_BUILDER_URL": "AUREY_ROUTE_BUILDER_URL",
        "ROUTING.ROUTE_BUILDER_API_KEY": "AUREY_ROUTE_BUILDER_API_KEY",
        "ROUTING.LIFI_TOKENS_PATH": "AUREY_LIFI_TOKENS_PATH",
        "DASHBOARD.ENABLED": "AUREY_DASHBOARD_ENABLED",
        "DASHBOARD.HOST": "AUREY_DASHBOARD_HOST",
        "DASHBOARD.PORT": "AUREY_DASHBOARD_PORT",
        "DASHBOARD.AUTH_TOKEN": "AUREY_DASHBOARD_AUTH_TOKEN",
        "X402.MAX_PRICE_USD": "AUREY_X402_MAX_PRICE_USD",
        "X402.AUTO_APPROVE_MAX_USD": "AUREY_X402_AUTO_APPROVE_MAX_USD",
        "X402.BATCH_MAX_DEPOSIT_USD": "AUREY_X402_BATCH_MAX_DEPOSIT_USD",
        "X402.ALLOWED_HOSTS": "AUREY_X402_ALLOWED_HOSTS",
        "X402.PREFER_NETWORK": "AUREY_X402_PREFER_NETWORK",
        "X402.BATCH_STORAGE_PATH": "AUREY_X402_BATCH_STORAGE_PATH",
        "X402.SERVICES_URL": "AUREY_X402_SERVICES_URL",
        "X402.SERVICES_PATH": "AUREY_X402_SERVICES_PATH",
        "X402.SERVICES_TTL_SECONDS": "AUREY_X402_SERVICES_TTL_SECONDS",
        "X402.SERVICES_CACHE_PATH": "AUREY_X402_SERVICES_CACHE_PATH",
    }
    for key, val in flat.items():
        env_key = aliases.get(key, key if key.startswith("AUREY_") else f"AUREY_{key}")
        os.environ.setdefault(env_key, val)


def load_settings(*, config_path: Path | None = None) -> AureySettings:
    path = config_path or default_config_path()
    apply_toml_to_env(path)
    os.environ.setdefault("AUREY_HOSTED_PLATFORM_ENABLED", "false")
    return AureySettings()


__all__ = ["default_config_path", "load_settings"]
