"""F13 Query Planner: heuristic fallback, fairness screen, planned search endpoint.

Tests run offline (no API keys) — planner must fall back to heuristic and the
fairness screen must hold on both paths.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.ai.query_planner import fairness_screen, plan_query, strip_protected_terms
from app.database import Base, SessionLocal, engine, init_db
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


def test_heuristic_plan_extracts_filters():
    db = SessionLocal()
    try:
        plan = plan_query(db, "elite aerial performers in UAE speaking Arabic under $5,000")
        f = plan.filters
        assert plan.planner == "heuristic"  # no API key in tests
        assert f.physical_skill_level == "Elite"
        assert f.aerial_performance_experience is True
        assert f.country == "UAE"
        assert "Arabic" in f.languages
        assert f.max_weekly_rate_usd == 5000.0
    finally:
        db.close()


def test_fairness_screen_blocks_protected_filters():
    db = SessionLocal()
    try:
        plan = plan_query(db, "young female asian dancers in UAE")
        # Violations surfaced, never silently dropped
        assert any("gender" in u for u in plan.unsupported)
        assert any("age" in u for u in plan.unsupported)
        assert any("ethnicity" in u for u in plan.unsupported)
        # Protected terms stripped from the semantic query
        sq = (plan.semantic_query or "").lower()
        for term in ("female", "young", "asian"):
            assert term not in sq
        # Legitimate parts of the query still work
        assert plan.filters.country == "UAE"
    finally:
        db.close()


def test_strip_protected_terms():
    assert "dancer" in strip_protected_terms("young female dancer").lower()
    assert "female" not in strip_protected_terms("young female dancer").lower()
    assert fairness_screen("experienced rigger in Macau") == []


def test_vocab_validation_drops_unknown_values():
    db = SessionLocal()
    try:
        plan = plan_query(db, "performers in Atlantis")  # not a dataset country/city
        assert plan.filters.country is None or plan.filters.country != "Atlantis"
    finally:
        db.close()


def test_planned_endpoint_shape_and_filtering(client):
    resp = client.post("/api/search/planned", json={"query": "elite aerial performers in UAE", "limit": 5})
    assert resp.status_code == 200
    data = resp.json()
    assert "plan" in data and "results" in data
    assert data["filtered_pool"] <= data["total_pool"]
    assert len(data["results"]) <= 5
    for t in data["results"]:
        assert t["aerial_performance_experience"] is True
        assert t["country"] == "UAE"
        assert t["physical_skill_level"] == "Elite"


def test_planned_endpoint_protected_query_still_safe(client):
    resp = client.post("/api/search/planned", json={"query": "young female performers", "limit": 5})
    assert resp.status_code == 200
    data = resp.json()
    assert any("not a permitted" in u for u in data["plan"]["unsupported"])
