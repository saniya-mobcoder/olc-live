"""App settings -- local SQLite by default + OpenAI only."""
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
    openai_api_key: str | None = None
    openai_embedding_model: str = "text-embedding-3-small"
    openai_chat_model: str = "gpt-4o-mini"


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    url = os.getenv("DATABASE_URL")
    if url:
        settings.database_url = url
    if not settings.openai_api_key:
        settings.openai_api_key = os.getenv("OPENAI_API_KEY")
    return settings
