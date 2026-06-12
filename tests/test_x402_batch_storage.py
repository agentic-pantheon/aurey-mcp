from __future__ import annotations

from pathlib import Path

from aurey.settings import AureySettings
from aurey.x402.batch_storage import batch_storage_dir, make_batch_channel_storage


def test_batch_storage_uses_configured_directory(tmp_path: Path) -> None:
    settings = AureySettings(x402_batch_storage_path=str(tmp_path / "channels"))
    assert batch_storage_dir(settings) == tmp_path / "channels"
    storage = make_batch_channel_storage(settings)
    assert (tmp_path / "channels").is_dir()
    assert storage is not None
