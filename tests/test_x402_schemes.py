from __future__ import annotations

from unittest.mock import MagicMock

from x402 import x402ClientSync
from x402.mechanisms.evm.batch_settlement.client import (
    BatchSettlementEvmScheme,
    BatchSettlementEvmSchemeOptions,
    FileChannelStorageOptions,
    FileClientChannelStorage,
)
from x402.mechanisms.evm.exact.client import ExactEvmScheme
from x402.mechanisms.evm.upto import UptoEvmScheme


def test_registers_v2_scheme_classes() -> None:
    """Factory wiring uses V2 Exact/Upto/BatchSettlement — not register_exact_evm_client."""
    signer = MagicMock()
    signer.address = "0x00000000000000000000000000000000000000aa"
    client = x402ClientSync()
    exact = ExactEvmScheme(signer)
    upto = UptoEvmScheme(signer)
    storage = FileClientChannelStorage(
        FileChannelStorageOptions(directory="/tmp/x402-test-channels"),
    )
    batch_opts = BatchSettlementEvmSchemeOptions(storage=storage, rpc_url="https://rpc.example.invalid")
    batch = BatchSettlementEvmScheme(signer, batch_opts)
    client.register("eip155:*", exact)
    client.register("eip155:*", upto)
    client.register("eip155:*", batch)
    assert exact.scheme == "exact"
    assert upto.scheme == "upto"
    assert batch.scheme == "batch-settlement"
