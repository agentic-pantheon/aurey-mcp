from aurey.custody.signing_keys_parse import ethereum_address_from_signing_keys_payload


def test_ethereum_from_signing_keys_keys_array() -> None:
    payload = {
        "keys": [
            {"chain": "ethereum", "address": "0x00000000000000000000000000000000000000a1"},
            {"chain": "solana", "address": "So11111111111111111111111111111111111111112"},
        ]
    }
    eth = ethereum_address_from_signing_keys_payload(payload)
    assert eth == "0x00000000000000000000000000000000000000A1"
