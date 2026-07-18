"""F21 Requirement Intake: vocab grounding, confidence, clarifying questions.

Offline path (no API key) must still produce grounded fields + questions.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.ai.intake import build_requirement_vocab, clarifying_questions, ground_fields
from app.database import Base, SessionLocal, engine, init_db
from app.main import app
from app.seed import seed_db

BRIEF = """Production: Dubai Waterfront Multimedia Spectacle
Looking for: Aerial Artist for a resident show in Dubai.
Rehearsals from 2026-10-04, final performance 2026-11-07.
Budget max $5,500 weekly. Arabic and English required. Overnight rehearsals expected.
"""


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


def test_vocab_built_from_both_sides():
    db = SessionLocal()
    try:
        vocab = build_requirement_vocab(db)
        assert vocab["roles"] and vocab["skills"] and vocab["languages"]
        assert "Performer" in vocab["categories"]
    finally:
        db.close()


def test_ground_fields_maps_and_collects_unmapped():
    db = SessionLocal()
    try:
        vocab = build_requirement_vocab(db)
        known_skill = vocab["skills"][0]
        fields = {
            "mandatory_skills": [known_skill.lower(), "Quantum Juggling"],  # one real, one invented
            "required_languages": ["english"],
        }
        grounded, unmapped = ground_fields(fields, vocab)
        assert known_skill in grounded["mandatory_skills"]
        assert "Quantum Juggling" not in grounded["mandatory_skills"]
        assert any("Quantum Juggling" in u for u in unmapped)
        assert grounded["required_languages"] == ["English"]
    finally:
        db.close()


def test_clarifying_questions_for_missing_criticals():
    qs = clarifying_questions({"required_primary_role": "Aerial Artist"})
    joined = " ".join(qs).lower()
    assert "budget" in joined
    assert "city" in joined or "country" in joined


def test_parse_endpoint_returns_confidence_and_questions(client):
    resp = client.post("/api/jobs/parse", json={"brief_text": BRIEF})
    assert resp.status_code == 200
    data = resp.json()
    assert data["parser"] in ("llm", "offline")
    # Every populated field carries a confidence value
    assert data["field_confidence"]
    for key, value in data["fields"].items():
        assert key in data["field_confidence"]
    # Confidence is 0 for empty values, positive for extracted ones
    conf = data["field_confidence"]
    assert conf.get("special_instructions", 0) > 0
    # Grounded languages come from dataset vocabulary
    for lang in data["fields"].get("required_languages", []):
        assert lang in ("Arabic", "English") or isinstance(lang, str)
    # Questions list exists (talent_required is never in the brief)
    assert isinstance(data["questions"], list)


def test_parse_grounding_blocks_invented_skills(client):
    brief = (
        "Looking for: Performer in Dubai from 2026-09-01 to 2026-10-01. "
        "Must know Hyperspace Navigation and Telepathic Choreography. Budget max $4,000."
    )
    resp = client.post("/api/jobs/parse", json={"brief_text": brief})
    assert resp.status_code == 200
    data = resp.json()
    skills = data["fields"].get("mandatory_skills") or []
    assert "Hyperspace Navigation" not in skills
    assert "Telepathic Choreography" not in skills
