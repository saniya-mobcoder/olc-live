"""Copilot harden: require match_run_id, no silent rematch, offline fallback."""
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
from app.models import MatchResult, MatchRun
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
        raise OpenAIConfigError("no key in tests")

    monkeypatch.setattr(
        "app.ai.agent.chat",
        lambda *a, **k: (_ for _ in ()).throw(OpenAIConfigError("no key in tests")),
    )
    monkeypatch.setattr(
        "app.routers.copilot.embed_text",
        lambda *_a, **_k: (_ for _ in ()).throw(OpenAIConfigError("no key in tests")),
    )
    with TestClient(app) as c:
        yield c


def test_copilot_requires_match_run_id(client):
    db = SessionLocal()
    before = db.query(MatchRun).count()
    db.close()
    resp = client.post(
        "/api/copilot/chat",
        json={"message": "Summarize", "requirement_id": "REQ-0001"},
    )
    db = SessionLocal()
    after = db.query(MatchRun).count()
    db.close()
    assert resp.status_code == 400
    detail = resp.json()["detail"].lower()
    assert "match_run_id" in detail or "run match" in detail
    assert after == before


def test_copilot_offline_cites_failed_gate(client):
    db = SessionLocal()
    try:
        run = run_match(db, "REQ-0001", ranking_mode="rules_only")
        rejected = (
            db.query(MatchResult)
            .filter(MatchResult.run_id == run.id, MatchResult.eligible.is_(False))
            .first()
        )
        assert rejected is not None
        talent_id = rejected.talent_id
        gates = list(rejected.failed_gates or [])
        assert gates
        run_id = run.id
    finally:
        db.close()

    resp = client.post(
        "/api/copilot/chat",
        json={
            "message": f"Why was {talent_id} rejected?",
            "match_run_id": run_id,
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["sources"]
    assert run_id in body["sources"]
    reply = body["reply"].lower()
    assert any(g.lower() in reply or g in body["sources"] for g in gates)


def test_score_against_endpoint(client):
    db = SessionLocal()
    try:
        run = run_match(db, "REQ-0001")
        row = db.query(MatchResult).filter(MatchResult.run_id == run.id).first()
        assert row is not None
        talent_id = row.talent_id
    finally:
        db.close()

    resp = client.post(
        "/api/search/score-against",
        json={"talent_id": talent_id, "requirement_id": "REQ-0001"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["talent_id"] == talent_id
    assert "eligible" in data
    assert "failed_gates" in data


def test_decision_capture_and_acceptance_kpi(client):
    db = SessionLocal()
    try:
        run = run_match(db, "REQ-0001")
        shortlisted = (
            db.query(MatchResult)
            .filter(MatchResult.run_id == run.id, MatchResult.rank.isnot(None))
            .first()
        )
        assert shortlisted is not None
        talent_id = shortlisted.talent_id
        run_id = run.id
    finally:
        db.close()

    resp = client.post(
        f"/api/matches/{run_id}/decisions",
        json={"talent_id": talent_id, "decision": "hire", "reason": "strong fit"},
    )
    assert resp.status_code == 200
    assert resp.json()["decision"] == "hire"

    listed = client.get(f"/api/matches/{run_id}/decisions")
    assert listed.status_code == 200
    assert any(d["talent_id"] == talent_id for d in listed.json())

    report = client.post(
        "/api/reports/executive",
        json={"period_start": "2020-01-01", "period_end": "2030-12-31"},
    )
    assert report.status_code == 200
    ops = report.json()["payload"]["operational"]
    assert ops["decision_count"] >= 1
    assert ops["decision_acceptance_pct"] >= 0
