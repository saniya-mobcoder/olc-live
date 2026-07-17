"""Bookings + call sheet + marketing drafts."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.database import Base, SessionLocal, engine, init_db
from app.embeddings import OpenAIConfigError
from app.engine.matcher import run_match
from app.main import app
from app.models import MatchResult
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

    monkeypatch.setattr("app.routers.marketing.require_api_key", _no_key)
    with TestClient(app) as c:
        yield c


def _hire_shortlisted(client) -> tuple[str, str]:
    db = SessionLocal()
    try:
        run = run_match(db, "REQ-0001")
        row = (
            db.query(MatchResult)
            .filter(MatchResult.run_id == run.id, MatchResult.rank.isnot(None))
            .order_by(MatchResult.rank)
            .first()
        )
        assert row is not None
        run_id, talent_id = run.id, row.talent_id
    finally:
        db.close()

    dec = client.post(
        f"/api/matches/{run_id}/decisions",
        json={"talent_id": talent_id, "decision": "hire"},
    )
    assert dec.status_code == 200
    return run_id, talent_id


def test_hire_booking_callsheet_and_schedule(client):
    run_id, talent_id = _hire_shortlisted(client)
    booking = client.post(
        "/api/bookings",
        json={"run_id": run_id, "talent_id": talent_id},
    )
    assert booking.status_code == 200, booking.text
    b = booking.json()
    assert b["id"].startswith("BKG-")
    assert b["talent_id"] == talent_id

    sched = client.get("/api/bookings/schedule", params={"requirement_id": "REQ-0001"})
    assert sched.status_code == 200
    assert any(x["id"] == b["id"] for x in sched.json())

    pdf = client.get(f"/api/export/callsheet/{b['id']}.pdf")
    assert pdf.status_code == 200
    assert pdf.headers["content-type"].startswith("application/pdf")
    assert pdf.content[:4] == b"%PDF"


def test_marketing_draft_from_booking(client):
    run_id, talent_id = _hire_shortlisted(client)
    booking = client.post(
        "/api/bookings",
        json={"run_id": run_id, "talent_id": talent_id},
    ).json()

    draft = client.post(
        "/api/marketing/draft",
        json={"channel": "linkedin", "booking_id": booking["id"]},
    )
    assert draft.status_code == 200, draft.text
    body = draft.json()
    assert body["channel"] == "linkedin"
    assert body["body"]
    assert body["source_ref"] == booking["id"]
