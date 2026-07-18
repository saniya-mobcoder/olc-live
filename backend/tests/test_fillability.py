"""Fillability report: live full-pool computation, status rules, and
cross-validation against known dataset facts (REQ-0001 has exactly 4
eligible talents in the 500-talent pool)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.database import SessionLocal, init_db
from app.routers.reports import compute_fillability_rows
from app.seed import seed_db


def _db():
    init_db()
    seed_db()
    return SessionLocal()


def test_fillability_req0001_known_counts():
    db = _db()
    try:
        rows = compute_fillability_rows(db, ["REQ-0001"], 1)
        assert len(rows) == 1
        row = rows[0]
        assert row["requirement_id"] == "REQ-0001"
        # 500 core talents; StageLync imports (TAL-SL-*) may add a few more.
        assert row["evaluated"] >= 500
        # Known dataset fact (see FEATURE_AUDIT_F01_F20.md): 4 talents clear all 12 gates.
        assert row["eligible"] == 4
        assert row["shortlist_preview"][0]["talent_id"] == "TAL-0378"
        assert abs(row["shortlist_preview"][0]["score"] - 87.75) < 0.05
        assert row["status"] in {"Healthy", "Attention Required", "Critical", "Blocked"}
        assert row["eligible"] >= row["recommended"] >= row["excellent"] >= 0
    finally:
        db.close()


def test_fillability_status_rules_consistent():
    db = _db()
    try:
        rows = compute_fillability_rows(db, ["REQ-0001", "REQ-0002", "REQ-0003"], 3)
        for row in rows:
            needed = row["talent_required"]
            if row["eligible"] == 0:
                assert row["status"] == "Blocked"
            elif row["eligible"] < needed:
                assert row["status"] == "Critical"
            elif row["recommended"] < needed or row["eligible"] < 2 * needed:
                assert row["status"] == "Attention Required"
            else:
                assert row["status"] == "Healthy"
            assert row["sourcing_action"]
            assert len(row["shortlist_preview"]) <= 5
    finally:
        db.close()
