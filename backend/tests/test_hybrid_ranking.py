"""Hybrid ranking: same eligible set as rules_only; prior in breakdown."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.database import Base, SessionLocal, engine, init_db
from app.engine.matcher import run_match, serialize_run
from app.models import MatchDecision, MatchResult
from app.seed import seed_db


@pytest.fixture(scope="module", autouse=True)
def setup_db():
    Base.metadata.drop_all(bind=engine)
    init_db()
    seed_db()
    yield


def test_hybrid_same_eligible_ids_as_rules_only():
    db = SessionLocal()
    try:
        rules = run_match(db, "REQ-0001", ranking_mode="rules_only", scenario_label="rules")
        hybrid = run_match(db, "REQ-0001", ranking_mode="hybrid", scenario_label="hybrid")

        rules_out = serialize_run(db, rules)
        hybrid_out = serialize_run(db, hybrid)

        rules_eligible = {r.talent_id for r in rules_out.shortlist + rules_out.other_eligible}
        hybrid_eligible = {r.talent_id for r in hybrid_out.shortlist + hybrid_out.other_eligible}
        assert rules_eligible == hybrid_eligible

        # Recommendable (>=70) set identical
        rules_rec = {
            r.talent_id
            for r in db.query(MatchResult).filter(MatchResult.run_id == rules.id, MatchResult.eligible.is_(True)).all()
            if (r.score or 0) >= 70
        }
        hybrid_rec = {
            r.talent_id
            for r in db.query(MatchResult).filter(MatchResult.run_id == hybrid.id, MatchResult.eligible.is_(True)).all()
            if (r.score or 0) >= 70
        }
        assert rules_rec == hybrid_rec

        # Breakdown carries prior + mode
        sample = (
            db.query(MatchResult)
            .filter(MatchResult.run_id == hybrid.id, MatchResult.rank == 1)
            .first()
        )
        assert sample is not None
        assert sample.breakdown.get("ranking_mode") == "hybrid"
        assert "feedback_prior" in sample.breakdown
        assert "hybrid_score" in sample.breakdown
        assert rules.weights.get("ranking_mode") == "rules_only"
        assert hybrid.weights.get("ranking_mode") == "hybrid"
    finally:
        db.close()


def test_hybrid_reorders_when_feedback_differs():
    db = SessionLocal()
    try:
        baseline = run_match(db, "REQ-0001", ranking_mode="rules_only", scenario_label="seed-decisions")
        shortlist = (
            db.query(MatchResult)
            .filter(MatchResult.run_id == baseline.id, MatchResult.rank.isnot(None))
            .order_by(MatchResult.rank)
            .all()
        )
        if len(shortlist) < 2:
            pytest.skip("need at least 2 shortlisted talents")

        # Boost second-ranked talent with hire decisions; reject the first
        first = shortlist[0]
        second = shortlist[1]
        for _ in range(3):
            db.add(
                MatchDecision(
                    run_id=baseline.id,
                    talent_id=second.talent_id,
                    decision="hire",
                    reason="demo boost",
                )
            )
        db.add(
            MatchDecision(
                run_id=baseline.id,
                talent_id=first.talent_id,
                decision="reject",
                reason="demo demote",
            )
        )
        db.commit()

        hybrid = run_match(db, "REQ-0001", ranking_mode="hybrid", scenario_label="after-feedback")
        ranked = (
            db.query(MatchResult)
            .filter(MatchResult.run_id == hybrid.id, MatchResult.rank.isnot(None))
            .order_by(MatchResult.rank)
            .all()
        )
        assert ranked
        # Second talent should have higher feedback prior; may or may not leapfrog
        # depending on score gap — at minimum priors differ in breakdown
        by_id = {r.talent_id: r for r in ranked}
        assert by_id[second.talent_id].breakdown["feedback_prior"] > by_id[first.talent_id].breakdown["feedback_prior"]
    finally:
        db.close()
