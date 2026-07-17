"""Smoke tests for executive report KPIs and StageLync import."""
from __future__ import annotations

import sys
from datetime import date, datetime
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.database import SessionLocal, init_db
from app.models import (
    MatchResult,
    MatchRun,
    ProductionCredit,
    Requirement,
    StageLyncLink,
    Talent,
)
from app.routers.reports import compute_executive_kpis
from app.routers.stagelync import import_person, sync_stagelync


def _minimal_requirement(**overrides) -> Requirement:
    base = dict(
        requirement_id="REQ-KPI-1",
        production_id="PROD-KPI",
        production_title="KPI Show",
        production_type="Spectacle",
        fictional_client_id="CLI-KPI",
        required_category="Performer",
        required_primary_role="Aerial Artist",
        acceptable_secondary_roles=[],
        mandatory_skills=[],
        preferred_skills=[],
        city="Dubai",
        country="UAE",
        latitude=25.2,
        longitude=55.2,
        venue_type="Arena",
        rehearsal_start_date=date(2026, 3, 1),
        rehearsal_end_date=date(2026, 3, 15),
        technical_rehearsal_start_date=date(2026, 3, 16),
        technical_rehearsal_end_date=date(2026, 3, 20),
        performance_start_date=date(2026, 3, 21),
        performance_end_date=date(2026, 4, 30),
        weekly_budget_max_usd=5000.0,
        booking_created_date=date(2026, 2, 10),
        application_deadline=date(2026, 2, 28),
        requirement_status="Open",
    )
    base.update(overrides)
    return Requirement(**base)


def _minimal_talent(talent_id: str = "TAL-KPI-1") -> Talent:
    return Talent(
        talent_id=talent_id,
        full_name="KPI Talent",
        profile_title="Performer",
        talent_category="Performer",
        primary_role="Aerial Artist",
        secondary_roles=[],
        primary_skills=[],
        secondary_skills=[],
        experience_years=5.0,
        city="Dubai",
        country="UAE",
        latitude=25.2,
        longitude=55.2,
        home_market_region="UAE",
        passport_valid_until=date(2030, 1, 1),
        work_authorized_countries=["UAE"],
        weekly_contract_rate_usd=4000.0,
        rehearsal_day_rate_usd=500.0,
        performance_fee_usd=800.0,
        buyout_rate_usd=8000.0,
        languages=["English"],
        showreel_quality_score=80.0,
        audition_readiness_score=80.0,
        portfolio_quality_score=80.0,
        last_active_date=date(2026, 1, 1),
        profile_status="Active",
    )


@pytest.fixture()
def db():
    init_db()
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def test_executive_kpis_smoke(db):
    if not db.get(Talent, "TAL-KPI-1"):
        db.add(_minimal_talent("TAL-KPI-1"))
    if not db.get(Talent, "TAL-KPI-2"):
        db.add(_minimal_talent("TAL-KPI-2"))
    if not db.get(Requirement, "REQ-KPI-1"):
        db.add(_minimal_requirement())
    if not db.get(Requirement, "REQ-KPI-2"):
        db.add(
            _minimal_requirement(
                requirement_id="REQ-KPI-2",
                booking_created_date=date(2025, 1, 1),
                application_deadline=date(2026, 6, 1),
                requirement_status="Filled",
            )
        )
    if not db.get(ProductionCredit, "CR-KPI-1"):
        db.add(
            ProductionCredit(
                credit_id="CR-KPI-1",
                talent_id="TAL-KPI-1",
                fictional_client_id="CLI-KPI",
                production_title="Past Show",
                production_type="Spectacle",
                role="Aerial Artist",
                start_date=date(2026, 1, 1),
                end_date=date(2026, 3, 1),
                city="Dubai",
                country="UAE",
                contract_status="Completed",
                contract_value_usd=12000.0,
                rehire_eligible=True,
            )
        )
    if not db.get(MatchRun, "RUN-KPI-1"):
        db.add(
            MatchRun(
                id="RUN-KPI-1",
                requirement_id="REQ-KPI-1",
                created_at=datetime(2026, 2, 15, 12, 0, 0),
                params_override={},
            )
        )
        db.add(
            MatchResult(
                run_id="RUN-KPI-1",
                talent_id="TAL-KPI-1",
                eligible=True,
                rank=1,
                score=88.0,
                failed_gates=[],
                breakdown={},
            )
        )
        db.add(
            MatchResult(
                run_id="RUN-KPI-1",
                talent_id="TAL-KPI-2",
                eligible=False,
                rank=None,
                score=0.0,
                failed_gates=["visa_gate"],
                breakdown={},
            )
        )
    db.commit()

    payload = compute_executive_kpis(db, date(2026, 1, 1), date(2026, 12, 31))
    ops = payload["operational"]
    commercial = payload["commercial"]

    assert ops["requirements_opened"] >= 1
    assert ops["requirements_closed"] >= 1
    assert ops["match_runs"] >= 1
    assert ops["top5_fill_rate_pct"] >= 0
    assert any(g["gate"] == "visa_gate" for g in ops["gate_fail_frequency"])
    assert commercial["contract_value_usd"] >= 12000.0
    assert commercial["rehire_eligible_share_pct"] >= 0


def test_stagelync_sync_and_import(db):
    out = sync_stagelync(db)
    assert out.total >= 20
    assert out.synced >= 0

    people = db.query(StageLyncLink).count()
    assert people >= 20

    imported = import_person("SL-1001", db)
    assert imported.stagelync_person_id == "SL-1001"
    assert imported.status == "imported"
    assert imported.talent_id.startswith("TAL-SL-")

    talent = db.get(Talent, imported.talent_id)
    assert talent is not None
    assert talent.full_name == "Maya Chen"
    assert talent.primary_role == "Aerial Artist"

    link = (
        db.query(StageLyncLink)
        .filter(StageLyncLink.stagelync_person_id == "SL-1001")
        .one()
    )
    assert link.talent_id == imported.talent_id
    assert link.status == "imported"

    again = import_person("SL-1001", db)
    assert again.created is False
    assert again.talent_id == imported.talent_id
