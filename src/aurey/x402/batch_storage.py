"""Persisted batch-settlement channel storage path."""

from __future__ import annotations

from pathlib import Path

from x402.mechanisms.evm.batch_settlement.client import (
    FileChannelStorageOptions,
    FileClientChannelStorage,
)

from aurey.settings import AureySettings


def batch_storage_dir(settings: AureySettings) -> Path:
    raw = (settings.x402_batch_storage_path or "").strip()
    if raw:
        return Path(raw).expanduser()
    return Path.home() / ".aurey" / "x402" / "batch_channels"


def make_batch_channel_storage(settings: AureySettings) -> FileClientChannelStorage:
    root = batch_storage_dir(settings)
    root.mkdir(parents=True, exist_ok=True)
    return FileClientChannelStorage(FileChannelStorageOptions(directory=root))


def list_batch_channel_files(settings: AureySettings) -> list[Path]:
    client_dir = batch_storage_dir(settings) / "client"
    if not client_dir.is_dir():
        return []
    return sorted(client_dir.glob("*.json"))


__all__ = ["batch_storage_dir", "list_batch_channel_files", "make_batch_channel_storage"]
