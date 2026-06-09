"""FastAPI service shell for local dashboard (optional extra)."""

from aurey.service.adapters import HttpxJsonClient, make_evm_rpc_factory, make_shared_httpx_client
from aurey.service.bootstrap import AureyRuntimeBootstrapError, bootstrap_aurey_runtime

__all__ = [
    "AureyRuntimeBootstrapError",
    "HttpxJsonClient",
    "bootstrap_aurey_runtime",
    "make_evm_rpc_factory",
    "make_shared_httpx_client",
]
