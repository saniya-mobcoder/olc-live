"""Force isolated SQLite + skip OpenAI embeds for unit tests."""
from __future__ import annotations

import os
from pathlib import Path

_test_db = Path(__file__).resolve().parent / "test_olc.db"
for path in (_test_db, Path(str(_test_db) + "-journal"), Path(str(_test_db) + "-wal")):
    try:
        if path.exists():
            path.unlink()
    except PermissionError:
        # Another pytest process may still hold the file on Windows.
        pass
os.environ["DATABASE_URL"] = "sqlite:///" + _test_db.as_posix()
os.environ["SKIP_EMBEDDINGS"] = "1"
