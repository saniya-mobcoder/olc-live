"""Embeddings facade — OpenAI-only vectors via dual-provider stack."""
from __future__ import annotations

from typing import Sequence

from .ai.providers import (
    AIConfigError,
    cosine_similarity,
    embed_texts as _embed_texts,
    require_openai_key,
)
from .config import get_settings

settings = get_settings()
DIM = settings.embedding_dim

# Back-compat aliases used across routers/tests
OpenAIConfigError = AIConfigError


def require_api_key() -> str:
    return require_openai_key()


def talent_document(talent) -> str:
    """Text blob embedded for semantic search."""
    parts = [
        talent.full_name,
        talent.profile_title,
        talent.talent_category,
        talent.primary_role,
        " ".join(talent.secondary_roles or []),
        " ".join(talent.primary_skills or []),
        " ".join(talent.secondary_skills or []),
        " ".join(talent.languages or []),
        talent.country,
        talent.city,
        " ".join(talent.professional_certifications or []),
        " ".join(talent.preferred_production_types or []),
        talent.physical_skill_level,
        "aquatic" if talent.aquatic_performance_experience else "",
        "aerial" if talent.aerial_performance_experience else "",
        "stunt" if talent.stunt_experience else "",
    ]
    return " ".join(p for p in parts if p)


def embed_texts(texts: list[str], *, batch_size: int = 100) -> list[list[float]]:
    return _embed_texts(texts, batch_size=batch_size)


def embed_text(text: str) -> list[float]:
    return embed_texts([text])[0]


__all__ = [
    "DIM",
    "OpenAIConfigError",
    "AIConfigError",
    "require_api_key",
    "talent_document",
    "embed_texts",
    "embed_text",
    "cosine_similarity",
]
