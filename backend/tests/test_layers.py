"""F01/F02 pilot layers: gate graph, near-miss, 4-layer scoring, advisory mode.

Invariants under test:
- Parity: layers are additive — eligible set and final scores unchanged.
- Gate graph reads booleans verbatim; not_applicable never counts as fail.
- Advisory ranking never resurrects an ineligible candidate.
- Confidence reflects data coverage, not score.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.database import Base, SessionLocal, engine, init_db
from app.engine.layers import root_cause_gates
from app.engine.matcher import run_match, score_talent_against_requirement, serialize_run
from app.models import MatchResult
from app.seed import seed_db

REQ = "REQ-0001"


@pytest.fixture(scope="module", autouse=True)
def setup_db():
    Base.metadata.drop_all(bind=engine)
    init_db()
    seed_db()
    yield


def _results(db, run_id):
    return db.query(MatchResult).filter(MatchResult.run_id == run_id).all()


def test_layers_present_and_parity_preserved():
    db = SessionLocal()
    try:
        rules = run_match(db, REQ, ranking_mode="rules_only", scenario_label="rules")
        for r in _results(db, rules.id):
            bd = r.breakdown or {}
            layers = bd.get("layers")
            assert layers, f"layers missing for {r.talent_id}"
            # Layer 1 mirrors eligibility exactly
            assert layers["layer1_eligibility"]["score"] == (100.0 if r.eligible else 0.0)
            # Layer 2 is the authoritative score, unchanged
            assert layers["layer2_weighted"]["score"] == pytest.approx(r.score or 0.0)
            assert layers["layer2_weighted"]["authoritative"] is True
            # Ineligible candidates never get an advisory score
            if not r.eligible:
                assert layers["advisory_score"] is None
            # Confidence is well-formed
            conf = layers["confidence"]
            assert 0.0 <= conf["score"] <= 1.0
            assert conf["level"] in ("high", "medium", "low")
            # Gate graph exists and uses only known statuses
            graph = bd.get("gate_graph")
            assert graph and all(g["status"] in ("pass", "fail", "not_applicable") for g in graph)
    finally:
        db.close()


def test_gate_graph_matches_failed_gates():
    db = SessionLocal()
    try:
        rules = run_match(db, REQ, ranking_mode="rules_only", scenario_label="graph")
        for r in _results(db, rules.id):
            graph = (r.breakdown or {}).get("gate_graph") or []
            graph_fails = {g["gate"] for g in graph if g["status"] == "fail"}
            # Every graph failure is a recorded failed gate (verbatim booleans).
            assert graph_fails.issubset(set(r.failed_gates or [])), r.talent_id
            # not_applicable gates are never listed as failures in the graph.
            na = {g["gate"] for g in graph if g["status"] == "not_applicable"}
            assert not (na & graph_fails)
    finally:
        db.close()


def test_root_cause_masking():
    db = SessionLocal()
    try:
        rules = run_match(db, REQ, ranking_mode="rules_only", scenario_label="mask")
        for r in _results(db, rules.id):
            graph = (r.breakdown or {}).get("gate_graph") or []
            roots = root_cause_gates(graph)
            fails = [g for g in graph if g["status"] == "fail"]
            if fails:
                # There is always at least one unmasked root cause to lead with.
                assert roots, f"{r.talent_id}: all failures masked"
            for g in fails:
                for dep in g["masked_by"]:
                    dep_status = next(x["status"] for x in graph if x["gate"] == dep)
                    assert dep_status == "fail"
    finally:
        db.close()


def test_advisory_mode_same_eligible_set_as_rules():
    db = SessionLocal()
    try:
        rules = run_match(db, REQ, ranking_mode="rules_only", scenario_label="r2")
        advisory = run_match(db, REQ, ranking_mode="advisory", scenario_label="adv")
        r_out = serialize_run(db, rules)
        a_out = serialize_run(db, advisory)
        r_eligible = {x.talent_id for x in r_out.shortlist + r_out.other_eligible}
        a_eligible = {x.talent_id for x in a_out.shortlist + a_out.other_eligible}
        assert r_eligible == a_eligible
        # Scores per talent identical across modes (advisory only re-orders)
        r_scores = {x.talent_id: x.score for x in r_out.shortlist + r_out.other_eligible}
        a_scores = {x.talent_id: x.score for x in a_out.shortlist + a_out.other_eligible}
        assert r_scores == a_scores
    finally:
        db.close()


def test_single_talent_endpoint_shape():
    db = SessionLocal()
    try:
        rules = run_match(db, REQ, ranking_mode="rules_only", scenario_label="one")
        out = serialize_run(db, rules)
        some = (out.shortlist or out.other_eligible or out.rejected)[0]
        detail = score_talent_against_requirement(db, REQ, some.talent_id)
        assert "gate_graph" in detail and "layers" in detail and "near_miss" in detail
        near = detail["near_miss"]
        if near is not None:
            assert near["is_near_miss"] is True
            assert 1 <= len(near["root_cause_gates"]) <= 2
    finally:
        db.close()
