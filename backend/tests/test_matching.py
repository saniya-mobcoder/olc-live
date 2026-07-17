"""Regression tests: computed scores/hard-gates must reproduce
match_ground_truth.csv and edge_case_manifest.csv from the real
OLC_Aligned_AI_Talent_Matching_Dataset."""
from __future__ import annotations

import csv
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.database import Base, SessionLocal, engine, init_db
from app.engine.matcher import build_audition_lookup, build_availability_lookup
from app.engine.scoring import compute_score
from app.models import Requirement, Talent
from app.seed import seed_db

DATA = Path(__file__).resolve().parents[2] / "data"

HARD_CHECK_COLUMNS = [
    "role_eligible",
    "mandatory_skills_met",
    "full_contract_availability_met",
    "audition_met",
    "physical_technical_eligible",
    "mobility_work_authorization_eligible",
    "safety_certification_eligible",
    "medical_clearance_eligible",
    "language_eligible",
    "overnight_rehearsal_eligible",
    "profile_active",
    "verification_eligible",
]

SCORE_TOLERANCE = 0.05


@pytest.fixture(scope="module", autouse=True)
def setup_db():
    Base.metadata.drop_all(bind=engine)
    init_db()
    seed_db()
    yield


def _csv_bool(v: str) -> bool:
    return v.strip().lower() == "true"


def _load_ground_truth() -> list[dict]:
    with open(DATA / "match_ground_truth.csv", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def test_ground_truth_matches_engine():
    rows = _load_ground_truth()
    db = SessionLocal()
    try:
        req_cache = {}
        avail_cache = {}
        audition_cache = {}
        talent_cache = {}

        mismatches = []
        checked = 0

        for row in rows:
            req_id = row["requirement_id"]
            talent_id = row["talent_id"]

            if req_id not in req_cache:
                req_cache[req_id] = db.get(Requirement, req_id)
            req = req_cache[req_id]

            if talent_id not in talent_cache:
                talent_cache[talent_id] = db.get(Talent, talent_id)
            talent = talent_cache[talent_id]

            if req is None or talent is None:
                continue

            if req_id not in avail_cache:
                avail_cache[req_id] = build_availability_lookup(db, req)
                audition_cache[req_id] = build_audition_lookup(db, req_id)

            audition_score = audition_cache[req_id].get(talent_id)
            result = compute_score(
                req,
                talent,
                availability_lookup=avail_cache[req_id],
                audition_score=audition_score,
            )
            checked += 1

            for col in HARD_CHECK_COLUMNS:
                expected = _csv_bool(row[col])
                actual = result[col]
                if expected != actual:
                    mismatches.append(
                        row["match_id"] + " " + req_id + "/" + talent_id + ": " + col
                        + " expected=" + str(expected) + " actual=" + str(actual)
                    )

            expected_score = float(row["final_match_score"])
            if abs(expected_score - result["score"]) > SCORE_TOLERANCE:
                mismatches.append(
                    row["match_id"] + " " + req_id + "/" + talent_id + ": score expected="
                    + str(expected_score) + " actual=" + str(result["score"])
                )

            expected_category = row["match_category"]
            if expected_category != result["match_category"]:
                mismatches.append(
                    row["match_id"] + " " + req_id + "/" + talent_id + ": category expected="
                    + expected_category + " actual=" + result["match_category"]
                )

        assert checked > 5000, "only checked " + str(checked) + " rows -- seed may have failed"
        first_20 = "\n".join(mismatches[:20])
        extra = ""
        if len(mismatches) > 20:
            extra = "\n...and " + str(len(mismatches) - 20) + " more"
        assert not mismatches, "Mismatches (showing first 20):\n" + first_20 + extra
    finally:
        db.close()


def test_edge_case_manifest():
    with open(DATA / "edge_case_manifest.csv", encoding="utf-8", newline="") as f:
        edges = list(csv.DictReader(f))

    db = SessionLocal()
    try:
        for edge in edges:
            req = db.get(Requirement, edge["requirement_id"])
            talent = db.get(Talent, edge["talent_id"])
            assert req is not None and talent is not None, edge["edge_case_id"]

            availability_lookup = build_availability_lookup(db, req)
            audition_lookup = build_audition_lookup(db, req.requirement_id)
            result = compute_score(
                req,
                talent,
                availability_lookup=availability_lookup,
                audition_score=audition_lookup.get(talent.talent_id),
            )
            assert result["match_category"] == edge["observed_match_category"], (
                edge["edge_case_id"] + " (" + edge["edge_case_name"] + "): expected "
                + edge["observed_match_category"] + ", got " + result["match_category"]
            )
    finally:
        db.close()
