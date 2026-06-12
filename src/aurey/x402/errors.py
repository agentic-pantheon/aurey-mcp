"""Map x402 transport failures to MCP tool error shapes."""

from __future__ import annotations

from typing import Any


def tool_error(code: str, message: str, **extra: Any) -> dict[str, Any]:
    err: dict[str, Any] = {"code": code, "message": message[:800]}
    if extra:
        err["details"] = extra
    return {"ok": False, "error": err}


__all__ = ["tool_error"]
