"""Deterministic edge-case scenarios sourced from edge_case_manifest.csv."""
from __future__ import annotations

import csv
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..engine.matcher import build_audition_lookup, build_availability_lookup
from ..engine.scoring import compute_score
from ..models import Requirement, Talent

router = APIRouter(prefix="/edges", tags=["edges"])
DATA_DIR = Path(__file__).resolve().parents[3] / "data"


def load_edges() -> list[dict]:
    with open(DATA_DIR / "edge_case_manifest.csv", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


@router.get("")
def list_edges():
    return [
        {
            "id": e["edge_case_id"],
            "name": e["edge_case_name"],
            "description": e["description"],
            "requirement_id": e["requirement_id"],
            "talent_id": e["talent_id"],
            "observed_match_category": e["observed_match_category"],
            "observed_rejection_reason": e["observed_rejection_reason"],
            "expected_system_behaviour": e["expected_system_behaviour"],
        }
        for e in load_edges()
    ]


@router.post("/{edge_id}/run")
def run_edge(edge_id: str, db: Session = Depends(get_db)):
    edges = {e["edge_case_id"]: e for e in load_edges()}
    edge = edges.get(edge_id)
    if not edge:
        raise HTTPException(status_code=404, detail="Edge scenario not found")

    req = db.get(Requirement, edge["requirement_id"])
    talent = db.get(Talent, edge["talent_id"])
    if not req or not talent:
        raise HTTPException(status_code=404, detail="Requirement or talent not found")

    availability_lookup = build_availability_lookup(db, req)
    audition_lookup = build_audition_lookup(db, req.requirement_id)
    scored = compute_score(
        req,
        talent,
        availability_lookup=availability_lookup,
        audition_score=audition_lookup.get(talent.talent_id),
    )

    passed = (
        scored["match_category"] == edge["observed_match_category"]
        and (
            not edge["observed_rejection_reason"]
            or set(edge["observed_rejection_reason"].split("; ")).issubset(set(scored["rejection_reasons"]))
        )
    )

    return {
        "edge": edge,
        "result": {
            "eligible": scored["eligible"],
            "match_category": scored["match_category"],
            "score": scored["score"],
            "failed_gates": scored["failed_gates"],
            "rejection_reasons": scored["rejection_reasons"],
            "risk_factors": scored["risk_factors"],
            "positive_match_reasons": scored["positive_match_reasons"],
            "distance_km": scored["distance_km"],
            "breakdown": scored["breakdown"],
        },
        "passed": passed,
    }
