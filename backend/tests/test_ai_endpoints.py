"""F12 edge regression + F19 AI cost endpoint smoke."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.ai.guardrails import assert_gates_unchanged, is_grounded
from app.database import Base, engine, init_db
from app.main import app
from app.seed import seed_db


@pytest.fixture(scope="module", autouse=True)
def setup_db():
    Base.metadata.drop_all(bind=engine)
    init_db()
    seed_db()
    yield


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


def test_ai_cost_endpoint(client):
    res = client.get("/api/ai/costs")
    assert res.status_code == 200
    body = res.json()
    assert "call_count" in body
    assert "total_cost_usd" in body
    assert "by_provider" in body


def test_whatif_suggest_offline(client):
    res = client.post("/api/what-if/suggest?requirement_id=REQ-0001")
    assert res.status_code == 200
    body = res.json()
    assert body["requirement_id"] == "REQ-0001"
    assert len(body["scenarios"]) >= 1
    assert "params_override" in body["scenarios"][0]


def test_explain_template_for_reject(client):
    # Run match then explain a rejected talent if any
    match = client.post(
        "/api/matches",
        json={"requirement_id": "REQ-0001", "top_k": 5, "include_ml_signals": True},
    )
    assert match.status_code == 200
    data = match.json()
    rejected = data.get("rejected") or []
    if not rejected:
        pytest.skip("no rejected rows for REQ-0001")
    tid = rejected[0]["talent_id"]
    exp = client.post(
        "/api/matches/explain",
        json={"match_run_id": data["id"], "talent_id": tid},
    )
    assert exp.status_code == 200
    body = exp.json()
    assert body["explanation"]
    assert body["grounded"] is True


def test_gate_assert_helper():
    assert assert_gates_unchanged(["visa", "budget"], ["budget", "visa"])
    assert not assert_gates_unchanged(["visa"], ["budget"])
    assert is_grounded("score 10", {"score": 10})
