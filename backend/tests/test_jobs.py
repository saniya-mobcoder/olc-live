"""Job ingestion: offline parse, confirm, dedupe shape."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.database import Base, SessionLocal, engine, init_db
from app.embeddings import OpenAIConfigError
from app.main import app
from app.models import Requirement
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

    monkeypatch.setattr("app.routers.jobs.require_api_key", _no_key)
    monkeypatch.setattr(
        "app.routers.jobs.embed_text",
        lambda *_a, **_k: (_ for _ in ()).throw(OpenAIConfigError("no key")),
    )
    with TestClient(app) as c:
        yield c


SAMPLE_BRIEF = """
Desert Lights Spectacle
Looking for: Aerial Artist in Dubai, UAE
Mandatory skills: Aerial Silks, Trampoline
Languages: Arabic, English
Weekly budget max $5500
Rehearsal 2026-09-01 performance ends 2026-10-15
Visa sponsorship available. Overnight rehearsals required.
"""


def test_offline_parse_maps_sample_brief(client):
    resp = client.post("/api/jobs/parse", json={"brief_text": SAMPLE_BRIEF})
    assert resp.status_code == 200
    data = resp.json()
    fields = data["fields"]
    assert "Aerial" in fields["required_primary_role"] or fields["required_primary_role"]
    assert fields.get("city")
    assert fields.get("weekly_budget_max_usd", 0) >= 5000
    assert "rehearsal_start_date" in fields or "missing_fields" in data


def test_confirm_creates_requirement(client):
    parsed = client.post("/api/jobs/parse", json={"brief_text": SAMPLE_BRIEF}).json()
    fields = parsed["fields"]
    # Ensure confirmable
    fields.setdefault("required_category", "Performer")
    fields.setdefault("country", "UAE")
    fields.setdefault("required_primary_role", "Aerial Artist")
    fields.setdefault("rehearsal_start_date", "2026-09-01")
    fields.setdefault("performance_end_date", "2026-10-15")
    fields.setdefault("weekly_budget_max_usd", 5500)

    before = SessionLocal().query(Requirement).count()
    resp = client.post("/api/jobs/confirm", json={"fields": fields})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["requirement_id"].startswith("REQ-")
    assert body["requirement_status"] == "Open"
    after = SessionLocal().query(Requirement).count()
    assert after == before + 1


def test_dedupe_returns_list_shape(client):
    resp = client.post(
        "/api/jobs/dedupe",
        json={"brief_text": "Aerial Artist Dubai Arabic spectacle"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "similar" in data
    assert isinstance(data["similar"], list)
