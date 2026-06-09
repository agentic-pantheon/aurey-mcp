"""Minimal cloud exports for standalone wallet plugin."""
from aurey.cloud.signing_context import (
    HOSTED_SIGNING_CONTEXT_REQUIRED_CODE,
    HostedSigningContext,
    aurey_invoke_context_scope,
    current_aurey_invoke_context,
    current_hosted_signing_context,
    current_hosted_telegram_user_id,
    hosted_signing_context_scope,
    hosted_telegram_user_id_scope,
)

__all__ = [
    "HOSTED_SIGNING_CONTEXT_REQUIRED_CODE",
    "HostedSigningContext",
    "aurey_invoke_context_scope",
    "current_aurey_invoke_context",
    "current_hosted_signing_context",
    "current_hosted_telegram_user_id",
    "hosted_signing_context_scope",
    "hosted_telegram_user_id_scope",
]
