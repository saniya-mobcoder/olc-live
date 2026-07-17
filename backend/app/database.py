"""SQLAlchemy engine/session setup -- Postgres+pgvector by default, SQLite fallback."""
from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import get_settings

settings = get_settings()

DATABASE_URL = settings.database_url
IS_SQLITE = DATABASE_URL.startswith("sqlite")
IS_POSTGRES = DATABASE_URL.startswith("postgresql")

_connect_args = {"check_same_thread": False} if IS_SQLITE else {}

engine = create_engine(
    DATABASE_URL,
    connect_args=_connect_args,
    pool_pre_ping=True,
    future=True,
)


class Base(DeclarativeBase):
    pass


SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create tables. For Postgres, also ensure the pgvector extension exists."""
    if IS_POSTGRES:
        from sqlalchemy import text

        with engine.begin() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    Base.metadata.create_all(bind=engine)


def ensure_vector_index() -> None:
    """Build an IVFFlat ANN index on talents.embedding (Postgres only). No-op on SQLite."""
    if not IS_POSTGRES:
        return
    from sqlalchemy import text

    with engine.begin() as conn:
        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_talents_embedding "
                "ON talents USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)"
            )
        )
