"""OpenAI-only embeddings for pgvector semantic search."""
from __future__ import annotations

import math
import time
from typing import Sequence

import httpx

from .config import get_settings

settings = get_settings()
# text-embedding-3-small default output size
DIM = settings.embedding_dim


class OpenAIConfigError(RuntimeError):
    pass


def require_api_key() -> str:
    key = settings.openai_api_key
    if not key:
        raise OpenAIConfigError(
            "OPENAI_API_KEY is required. Set it in backend/.env -- "
            "this POC uses OpenAI only (no local embedder)."
        )
    return key


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


def _normalize(vec: list[float]) -> list[float]:
    if len(vec) > DIM:
        vec = vec[:DIM]
    elif len(vec) < DIM:
        vec = vec + [0.0] * (DIM - len(vec))
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


def embed_texts(texts: list[str], *, batch_size: int = 100) -> list[list[float]]:
    """Batch embed via OpenAI Embeddings API (chunked + retried for reliability)."""
    if not texts:
        return []
    api_key = require_api_key()
    out: list[list[float]] = []
    for start in range(0, len(texts), batch_size):
        chunk = texts[start : start + batch_size]
        last_err: Exception | None = None
        for attempt in range(3):
            try:
                resp = httpx.post(
                    "https://api.openai.com/v1/embeddings",
                    headers={"Authorization": f"Bearer {api_key}"},
                    json={
                        "model": settings.openai_embedding_model,
                        "input": chunk,
                        "dimensions": DIM,
                    },
                    timeout=120.0,
                )
                if resp.status_code >= 400:
                    raise RuntimeError(
                        f"OpenAI embeddings failed: {resp.status_code} {resp.text}"
                    )
                data = resp.json()["data"]
                data.sort(key=lambda row: row["index"])
                out.extend(_normalize(row["embedding"]) for row in data)
                last_err = None
                break
            except Exception as exc:  # noqa: BLE001 -- retry on any transient failure
                last_err = exc
                if attempt < 2:
                    time.sleep(1.5 * (attempt + 1))
        if last_err is not None:
            raise RuntimeError(f"OpenAI embeddings failed after retries: {last_err}") from last_err
    return out


def embed_text(text: str) -> list[float]:
    return embed_texts([text])[0]


def cosine_similarity(a: Sequence[float], b: Sequence[float]) -> float:
    return float(sum(x * y for x, y in zip(a, b)))
