"""1Claw-backed x402 EVM signer (EIP-712 + optional RPC reads / tx sign)."""

from __future__ import annotations

from typing import Any

from eth_utils import to_checksum_address
from x402.mechanisms.evm.signer import (
    ClientEvmSignerWithReadContract,
    ClientEvmSignerWithSignTransaction,
)
from x402.mechanisms.evm.types import TypedDataDomain, TypedDataField

from aurey.custody.errors import OneClawSigningError, SecretStoreUnavailableError
from aurey.custody.intents_principal import OneClawSigningPrincipal
from aurey.custody.secret_store import OneClawEvmTransactionSigner
from aurey.graphs.chains import chain_name_for_id
from aurey.runtime import AureyRuntime


def _network_to_chain_slug(network: str) -> str:
    net = (network or "").strip()
    if net.startswith("eip155:"):
        try:
            cid = int(net.split(":", 1)[1])
        except (IndexError, ValueError) as exc:
            raise ValueError(f"Invalid EVM network id: {network}") from exc
        slug = chain_name_for_id(cid)
        if slug:
            return slug
    raise ValueError(f"Unsupported x402 network for 1Claw signing: {network}")


def _eip712_domain_type_fields(domain_dict: dict[str, Any]) -> list[dict[str, str]]:
    """Build ``EIP712Domain`` type entries for fields present in ``domain``."""
    candidates: tuple[tuple[str, str], ...] = (
        ("name", "string"),
        ("version", "string"),
        ("chainId", "uint256"),
        ("verifyingContract", "address"),
        ("salt", "bytes32"),
    )
    fields: list[dict[str, str]] = []
    for name, typ in candidates:
        if name in domain_dict and domain_dict[name] is not None:
            fields.append({"name": name, "type": typ})
    return fields


def _json_safe_eip712_value(value: Any) -> Any:
    """Coerce x402 EIP-712 message fields for JSON POST to 1Claw ``/sign``."""
    if isinstance(value, bytes):
        return "0x" + value.hex()
    if isinstance(value, dict):
        return {k: _json_safe_eip712_value(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_json_safe_eip712_value(v) for v in value]
    return value


def _typed_data_to_eip712_json(
    domain: TypedDataDomain | dict[str, Any],
    types: dict[str, list[TypedDataField] | list[dict[str, str]]],
    primary_type: str,
    message: dict[str, Any],
) -> dict[str, Any]:
    if isinstance(domain, TypedDataDomain):
        domain_dict: dict[str, Any] = {
            "name": domain.name,
            "version": domain.version,
            "chainId": domain.chain_id,
            "verifyingContract": to_checksum_address(domain.verifying_contract),
        }
    else:
        domain_dict = dict(domain)

    types_out: dict[str, list[dict[str, str]]] = {}
    domain_fields = _eip712_domain_type_fields(domain_dict)
    if domain_fields:
        types_out["EIP712Domain"] = domain_fields
    for type_name, fields in types.items():
        if type_name == "EIP712Domain":
            continue
        row: list[dict[str, str]] = []
        for f in fields:
            if isinstance(f, TypedDataField):
                row.append({"name": f.name, "type": f.type})
            else:
                row.append({"name": str(f["name"]), "type": str(f["type"])})
        types_out[type_name] = row

    return {
        "types": types_out,
        "primaryType": primary_type,
        "domain": _json_safe_eip712_value(domain_dict),
        "message": _json_safe_eip712_value(message),
    }


def _signature_hex_to_bytes(sig: str) -> bytes:
    raw = sig.strip()
    if raw.startswith("0x"):
        raw = raw[2:]
    return bytes.fromhex(raw)


class OneClawEvmX402Signer(ClientEvmSignerWithReadContract, ClientEvmSignerWithSignTransaction):
    """Adapts 1Claw unified signing to the x402 ``ClientEvmSigner`` protocol."""

    def __init__(
        self,
        runtime: AureyRuntime,
        *,
        signer: OneClawEvmTransactionSigner,
        chain_slug: str = "base",
        rpc_url: str | None = None,
    ) -> None:
        self._runtime = runtime
        self._signer = signer
        self._default_chain = chain_slug.strip().lower()
        self._rpc_url = (rpc_url or "").strip() or None
        self._web3: Any | None = None
        addr = (runtime.agent_evm_wallet_address or "").strip()
        if not addr:
            raise ValueError("Agent EVM wallet address is not available on runtime.")
        self._address = to_checksum_address(addr)

    @property
    def address(self) -> str:
        return self._address

    def _principal(self) -> tuple[OneClawSigningPrincipal, str]:
        principal, err = OneClawSigningPrincipal.resolve(self._runtime)
        if err is not None:
            raise OneClawSigningError(err.get("message", "1Claw signing principal unavailable."))
        chain = self._default_chain
        return principal, chain

    def sign_typed_data(
        self,
        domain: TypedDataDomain,
        types: dict[str, list[TypedDataField]],
        primary_type: str,
        message: dict[str, Any],
    ) -> bytes:
        principal, chain = self._principal()
        typed_data = _typed_data_to_eip712_json(domain, types, primary_type, message)
        try:
            out = self._signer.sign_typed_data(
                agent_id=principal.agent_id,
                chain=chain,
                typed_data=typed_data,
                authorization_bearer=principal.authorization_bearer,
            )
        except (OneClawSigningError, SecretStoreUnavailableError, ValueError) as exc:
            raise OneClawSigningError(str(exc)) from exc
        return _signature_hex_to_bytes(out.signature)

    def read_contract(
        self,
        address: str,
        abi: list[dict[str, Any]],
        function_name: str,
        *args: Any,
    ) -> Any:
        w3 = self._web3_instance()
        contract = w3.eth.contract(address=to_checksum_address(address), abi=abi)
        fn = getattr(contract.functions, function_name)
        return fn(*args).call()

    def sign_transaction(self, tx: dict[str, Any]) -> str:
        principal, chain = self._principal()
        try:
            out = self._signer.sign_evm_transaction(
                agent_id=principal.agent_id,
                chain=chain,
                transaction=dict(tx),
                authorization_bearer=principal.authorization_bearer,
            )
        except (OneClawSigningError, SecretStoreUnavailableError, ValueError) as exc:
            raise OneClawSigningError(str(exc)) from exc
        return out.signed_tx if out.signed_tx.startswith("0x") else f"0x{out.signed_tx}"

    def get_transaction_count(self, address: str) -> int:
        w3 = self._web3_instance()
        return int(w3.eth.get_transaction_count(to_checksum_address(address)))

    def _web3_instance(self) -> Any:
        if self._web3 is not None:
            return self._web3
        if not self._rpc_url:
            raise RuntimeError("RPC URL is not configured for x402 contract reads.")
        from web3 import Web3

        self._web3 = Web3(Web3.HTTPProvider(self._rpc_url, request_kwargs={"timeout": 30}))
        return self._web3


__all__ = ["OneClawEvmX402Signer", "_network_to_chain_slug"]
