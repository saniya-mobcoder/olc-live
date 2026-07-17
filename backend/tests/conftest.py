"""Force isolated SQLite + skip OpenAI embeds for unit tests."""
from __future__ import annotations

import os
from pathlib import Path

_test_db = Path(__file__).resolve().parent / "test_olc.db"
if _test_db.exists():
    _test_db.unlink()
os.environ["DATABASE_URL"] = "sqlite:///" + _test_db.as_posix()
os.environ["SKIP_EMBEDDINGS"] = "1"
