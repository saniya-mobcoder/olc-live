"""Support FAQ mode + match mode still requires match_run_id."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.database import Base, engine, init_db
from app.embeddings import OpenAIConfigError
from app.main import app
from app.seed import seed_db


@pytest.fixture(scope="module", autouse=True)
def setup_db():
    Base.metadata.drop_all(bind=engine)
    init_db()
    seed_db()
    yield


@pytest.fixture()
def client(monkeypatch):
    def _no_key():
        raise OpenAIConfigError("no key")

    monkeypatch.setattr("app.routers.copilot.require_api_key", _no_key)
    monkeypatch.setattr(
        "app.routers.copilot.embed_text",
        lambda *_a, **_k: (_ for _ in ()).throw(OpenAIConfigError("no key")),
    )
    with TestClient(app) as c:
        yield c


def test_support_how_to_run_match_cites_faq(client):
    resp = client.post(
        "/api/copilot/chat",
        json={"message": "How do I run a match?", "mode": "support"},
    )
    assert resp.status_code == 200
    body = resp.json()
    sources = " ".join(body["sources"]).lower()
    reply = body["reply"].lower()
    assert "run-match.md" in sources or "run match" in reply
    assert "run-match.md" in sources or "match" in reply


def test_match_mode_still_requires_run_id(client):
    resp = client.post(
        "/api/copilot/chat",
        json={"message": "Summarize", "mode": "match"},
    )
    assert resp.status_code == 400
