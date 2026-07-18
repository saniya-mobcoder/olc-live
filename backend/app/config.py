"""App settings -- SQLite + OpenAI embeddings + Groq free Llama chat (POC)."""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_DEFAULT_SQLITE = f"sqlite:///{(Path(__file__).resolve().parents[1] / 'olc.db').as_posix()}"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Local-first: SQLite file under backend/olc.db (no Docker)
    database_url: str = _DEFAULT_SQLITE
    embedding_dim: int = 1536

    # OpenAI — embeddings only (POC); optional chat failover
    openai_api_key: str | None = None
    openai_embedding_model: str = "text-embedding-3-small"
    openai_chat_model: str = "gpt-4o-mini"
    openai_base_url: str = "https://api.openai.com/v1"

    # Groq — free-tier Llama Instruct 70B for all chat (POC)
    groq_api_key: str | None = None
    groq_base_url: str = "https://api.groq.com/openai/v1"
    groq_chat_model: str = "llama-3.3-70b-versatile"

    # Optional — xAI / Grok (extra failover only)
    xai_api_key: str | None = None
    xai_base_url: str = "https://api.x.ai/v1"
    xai_chat_model: str = "grok-4.3"

    # Routing: both chat tiers default to Groq (free 70B)
    ai_cheap_provider: str = "groq"  # groq | openai | xai
    ai_quality_provider: str = "groq"  # groq | openai | xai
    ai_fallback: bool = True


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    url = os.getenv("DATABASE_URL")
    if url:
        settings.database_url = url
    if not settings.openai_api_key:
        settings.openai_api_key = os.getenv("OPENAI_API_KEY")
    if not settings.groq_api_key:
        settings.groq_api_key = os.getenv("GROQ_API_KEY")
    if not settings.xai_api_key:
        settings.xai_api_key = os.getenv("XAI_API_KEY") or os.getenv("GROK_API_KEY")
    cheap = os.getenv("AI_CHEAP_PROVIDER")
    if cheap:
        settings.ai_cheap_provider = cheap.strip().lower()
    quality = os.getenv("AI_QUALITY_PROVIDER")
    if quality:
        settings.ai_quality_provider = quality.strip().lower()
    fb = os.getenv("AI_FALLBACK")
    if fb is not None:
        settings.ai_fallback = fb.strip().lower() in ("1", "true", "yes", "on")
    return settings
