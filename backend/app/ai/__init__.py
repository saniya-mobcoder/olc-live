"""Shared AI capability stack — dual-provider routing + grounded LLM helpers."""

from .providers import (
    AIConfigError,
    ChatResult,
    TaskTier,
    chat,
    embed_texts,
    estimate_cost_usd,
)

__all__ = [
    "AIConfigError",
    "ChatResult",
    "TaskTier",
    "chat",
    "embed_texts",
    "estimate_cost_usd",
]
