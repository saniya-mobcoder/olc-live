"""Load the OLC_Aligned_AI_Talent_Matching_Dataset CSVs into local SQLite
(or optional Postgres) and build OpenAI talent embeddings."""
from __future__ import annotations

import csv
import os
from datetime import date, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import insert
from sqlalchemy.orm import Session

from .database import IS_POSTGRES, SessionLocal, ensure_vector_index, init_db
from .embeddings import OpenAIConfigError, embed_texts, talent_document
from .models import (
    AuditEvent,
    AuditionEvaluation,
    Booking,
    MarketingDraft,
    MatchDecision,
    MatchResult,
    MatchRun,
    ProductionCredit,
    Requirement,
    Talent,
    TalentAvailability,
)

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
CHUNK_SIZE = 2000


def _date(value: str) -> date:
    return datetime.strptime(value.strip(), "%Y-%m-%d").date()


def _datetime(value: str) -> datetime:
    return datetime.fromisoformat(value.strip())


def _bool(value: str) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes"}


def _float(value: str, default: float = 0.0) -> float:
    value = (value or "").strip()
    return float(value) if value else default


def _opt_float(value: str) -> float | None:
    value = (value or "").strip()
    return float(value) if value else None


def _int(value: str, default: int = 0) -> int:
    value = (value or "").strip()
    return int(float(value)) if value else default


def _list(value: str) -> list[str]:
    value = (value or "").strip()
    return [v for v in value.split("|") if v] if value else []


def _rows(filename: str):
    with open(DATA_DIR / filename, encoding="utf-8", newline="") as f:
        yield from csv.DictReader(f)


def _bulk_insert(db: Session, table, mappings: list[dict[str, Any]]) -> None:
    for i in range(0, len(mappings), CHUNK_SIZE):
        db.execute(insert(table), mappings[i : i + CHUNK_SIZE])


def _load_talents(db: Session) -> list[dict[str, Any]]:
    mappings = []
    for row in _rows("talent_profiles.csv"):
        mappings.append(
            {
                "talent_id": row["talent_id"],
                "full_name": row["full_name"],
                "profile_title": row["profile_title"],
                "talent_category": row["talent_category"],
                "primary_role": row["primary_role"],
                "secondary_roles": _list(row["secondary_roles"]),
                "primary_skills": _list(row["primary_skills"]),
                "secondary_skills": _list(row["secondary_skills"]),
                "experience_years": _float(row["experience_years"]),
                "city": row["city"],
                "country": row["country"],
                "latitude": _float(row["latitude"]),
                "longitude": _float(row["longitude"]),
                "home_market_region": row["home_market_region"],
                "travel_ready": _bool(row["travel_ready"]),
                "relocation_available": _bool(row["relocation_available"]),
                "passport_valid_until": _date(row["passport_valid_until"]),
                "work_authorized_countries": _list(row["work_authorized_countries"]),
                "weekly_contract_rate_usd": _float(row["weekly_contract_rate_usd"]),
                "rehearsal_day_rate_usd": _float(row["rehearsal_day_rate_usd"]),
                "performance_fee_usd": _float(row["performance_fee_usd"]),
                "buyout_rate_usd": _float(row["buyout_rate_usd"]),
                "languages": _list(row["languages"]),
                "showreel_quality_score": _float(row["showreel_quality_score"]),
                "audition_readiness_score": _float(row["audition_readiness_score"]),
                "physical_skill_level": row["physical_skill_level"],
                "aquatic_performance_experience": _bool(row["aquatic_performance_experience"]),
                "aerial_performance_experience": _bool(row["aerial_performance_experience"]),
                "stunt_experience": _bool(row["stunt_experience"]),
                "medical_clearance_status": row["medical_clearance_status"],
                "safety_training_level": row["safety_training_level"],
                "professional_certifications": _list(row["professional_certifications"]),
                "portfolio_quality_score": _float(row["portfolio_quality_score"]),
                "average_director_rating": _opt_float(row["average_director_rating"]),
                "completed_productions": _int(row["completed_productions"]),
                "completed_performances": _int(row["completed_performances"]),
                "rehire_rate": _float(row["rehire_rate"]),
                "rehearsal_attendance_rate": _float(row["rehearsal_attendance_rate"]),
                "safety_incident_rate": _float(row["safety_incident_rate"]),
                "cancellation_rate": _float(row["cancellation_rate"]),
                "response_time_hours": _float(row["response_time_hours"]),
                "profile_completion_percentage": _float(row["profile_completion_percentage"]),
                "identity_verified": _bool(row["identity_verified"]),
                "professional_references_verified": _bool(row["professional_references_verified"]),
                "preferred_production_types": _list(row["preferred_production_types"]),
                "overnight_rehearsal_available": _bool(row["overnight_rehearsal_available"]),
                "weekend_available": _bool(row["weekend_available"]),
                "last_active_date": _date(row["last_active_date"]),
                "profile_status": row["profile_status"],
            }
        )
    _bulk_insert(db, Talent.__table__, mappings)
    return mappings


def _load_requirements(db: Session) -> None:
    mappings = []
    for row in _rows("production_requirements.csv"):
        mappings.append(
            {
                "requirement_id": row["requirement_id"],
                "production_id": row["production_id"],
                "production_title": row["production_title"],
                "production_type": row["production_type"],
                "fictional_client_id": row["fictional_client_id"],
                "required_category": row["required_category"],
                "required_primary_role": row["required_primary_role"],
                "acceptable_secondary_roles": _list(row["acceptable_secondary_roles"]),
                "mandatory_skills": _list(row["mandatory_skills"]),
                "preferred_skills": _list(row["preferred_skills"]),
                "city": row["city"],
                "country": row["country"],
                "latitude": _float(row["latitude"]),
                "longitude": _float(row["longitude"]),
                "venue_type": row["venue_type"],
                "rehearsal_start_date": _date(row["rehearsal_start_date"]),
                "rehearsal_end_date": _date(row["rehearsal_end_date"]),
                "technical_rehearsal_start_date": _date(row["technical_rehearsal_start_date"]),
                "technical_rehearsal_end_date": _date(row["technical_rehearsal_end_date"]),
                "performance_start_date": _date(row["performance_start_date"]),
                "performance_end_date": _date(row["performance_end_date"]),
                "number_of_performances": _int(row["number_of_performances"]),
                "contract_duration_days": _int(row["contract_duration_days"]),
                "talent_required": _int(row["talent_required"], 1),
                "ensemble_or_solo": row["ensemble_or_solo"],
                "minimum_experience_years": _float(row["minimum_experience_years"]),
                "minimum_director_rating": _float(row["minimum_director_rating"]),
                "minimum_showreel_score": _float(row["minimum_showreel_score"]),
                "minimum_audition_score": _float(row["minimum_audition_score"]),
                "physical_skill_requirement": row["physical_skill_requirement"],
                "aquatic_experience_required": _bool(row["aquatic_experience_required"]),
                "aerial_experience_required": _bool(row["aerial_experience_required"]),
                "stunt_experience_required": _bool(row["stunt_experience_required"]),
                "required_safety_certifications": _list(row["required_safety_certifications"]),
                "medical_clearance_required": _bool(row["medical_clearance_required"]),
                "audition_required": _bool(row["audition_required"]),
                "passport_validity_months_required": _int(row["passport_validity_months_required"], 6),
                "visa_sponsorship_available": _bool(row["visa_sponsorship_available"]),
                "required_languages": _list(row["required_languages"]),
                "overnight_rehearsal_required": _bool(row["overnight_rehearsal_required"]),
                "weekly_budget_min_usd": _float(row["weekly_budget_min_usd"]),
                "weekly_budget_max_usd": _float(row["weekly_budget_max_usd"]),
                "travel_provided": _bool(row["travel_provided"]),
                "accommodation_provided": _bool(row["accommodation_provided"]),
                "per_diem_usd": _float(row["per_diem_usd"]),
                "production_risk_level": row["production_risk_level"],
                "urgency_level": row["urgency_level"],
                "booking_created_date": _date(row["booking_created_date"]),
                "application_deadline": _date(row["application_deadline"]),
                "special_instructions": row.get("special_instructions", "") or "",
                "requirement_status": row["requirement_status"],
            }
        )
    _bulk_insert(db, Requirement.__table__, mappings)


def _load_credits(db: Session) -> None:
    mappings = []
    for row in _rows("production_credits.csv"):
        mappings.append(
            {
                "credit_id": row["credit_id"],
                "talent_id": row["talent_id"],
                "fictional_client_id": row["fictional_client_id"],
                "production_title": row["production_title"],
                "production_type": row["production_type"],
                "role": row["role"],
                "start_date": _date(row["start_date"]),
                "end_date": _date(row["end_date"]),
                "city": row["city"],
                "country": row["country"],
                "contract_status": row["contract_status"],
                "number_of_performances": _int(row["number_of_performances"]),
                "contract_value_usd": _float(row["contract_value_usd"]),
                "rehearsal_attendance_rate": _float(row["rehearsal_attendance_rate"]),
                "director_rating": _float(row["director_rating"]),
                "technical_readiness_score": _float(row["technical_readiness_score"]),
                "safety_compliance_score": _float(row["safety_compliance_score"]),
                "incident_recorded": _bool(row["incident_recorded"]),
                "incident_severity": row["incident_severity"],
                "rehire_eligible": _bool(row["rehire_eligible"]),
                "early_termination_party": row.get("early_termination_party", "") or "",
                "early_termination_reason": row.get("early_termination_reason", "") or "",
                "skills_used": _list(row["skills_used"]),
                "director_feedback": row.get("director_feedback", "") or "",
            }
        )
    _bulk_insert(db, ProductionCredit.__table__, mappings)


def _load_availability(db: Session) -> None:
    mappings = []
    for row in _rows("talent_availability.csv"):
        mappings.append(
            {
                "availability_id": row["availability_id"],
                "talent_id": row["talent_id"],
                "availability_date": _date(row["availability_date"]),
                "availability_status": row["availability_status"],
                "available_from": row["available_from"],
                "available_until": row["available_until"],
                "partially_available": _bool(row["partially_available"]),
                "booked_contract_reference": row.get("booked_contract_reference", "") or "",
                "advance_notice_days": _int(row["advance_notice_days"]),
                "overnight_available": _bool(row["overnight_available"]),
                "last_updated_at": _datetime(row["last_updated_at"]),
            }
        )
    _bulk_insert(db, TalentAvailability.__table__, mappings)


def _load_auditions(db: Session) -> None:
    mappings = []
    for row in _rows("audition_evaluations.csv"):
        mappings.append(
            {
                "audition_id": row["audition_id"],
                "requirement_id": row["requirement_id"],
                "talent_id": row["talent_id"],
                "audition_date": _date(row["audition_date"]),
                "audition_format": row["audition_format"],
                "technical_score": _float(row["technical_score"]),
                "artistic_score": _float(row["artistic_score"]),
                "response_to_direction_score": _float(row["response_to_direction_score"]),
                "safety_awareness_score": _float(row["safety_awareness_score"]),
                "panel_score": _float(row["panel_score"]),
                "audition_outcome": row["audition_outcome"],
                "panel_notes": row.get("panel_notes", "") or "",
            }
        )
    _bulk_insert(db, AuditionEvaluation.__table__, mappings)


def _has_embeddings(db: Session) -> bool:
    return db.query(Talent).filter(Talent.embedding.isnot(None)).limit(1).count() > 0


def _backfill_embeddings(db: Session, talents: list[Talent]) -> int:
    if os.getenv("SKIP_EMBEDDINGS", "").lower() in {"1", "true", "yes"}:
        return 0
    missing = [t for t in talents if not t.embedding]
    if not missing:
        return 0
    try:
        docs = [talent_document(t) for t in missing]
        vectors = embed_texts(docs)
    except OpenAIConfigError:
        # No key configured -- app still works, just no semantic search yet.
        return 0
    for talent, vec in zip(missing, vectors):
        talent.embedding = vec
    db.commit()
    return len(missing)


def seed_db(db: Session | None = None) -> None:
    """Idempotent: only loads CSVs once. On subsequent app restarts it just
    backfills any missing embeddings instead of re-seeding from scratch
    (set FORCE_RESEED=1 to wipe and reload everything)."""
    close = False
    if db is None:
        db = SessionLocal()
        close = True
    try:
        from .database import Base, engine

        force = os.getenv("FORCE_RESEED", "").lower() in {"1", "true", "yes"}
        init_db()

        existing = db.query(Talent).count()
        if existing > 0 and not force:
            talents = db.query(Talent).order_by(Talent.talent_id).all()
            added = _backfill_embeddings(db, talents)
            if added:
                ensure_vector_index()
                print(f"Backfilled OpenAI embeddings for {added} talents.")
            else:
                print(f"Database ready -- {existing} talents, embeddings present or skipped.")
            return

        if force and existing > 0:
            db.query(AuditEvent).delete()
            db.query(MarketingDraft).delete()
            db.query(Booking).delete()
            db.query(MatchDecision).delete()
            db.query(MatchResult).delete()
            db.query(MatchRun).delete()
            db.query(AuditionEvaluation).delete()
            db.query(TalentAvailability).delete()
            db.query(ProductionCredit).delete()
            db.query(Talent).delete()
            db.query(Requirement).delete()
            db.commit()

        talent_mappings = _load_talents(db)
        _load_requirements(db)
        _load_credits(db)
        _load_availability(db)
        _load_auditions(db)
        db.commit()

        talents = db.query(Talent).order_by(Talent.talent_id).all()
        added = _backfill_embeddings(db, talents)
        if added:
            ensure_vector_index()
            print(
                f"Seeded {len(talent_mappings)} talents, requirements, credits, "
                f"availability, and auditions (OpenAI embeddings for {added} talents)."
            )
        else:
            print(
                f"Seeded {len(talent_mappings)} talents, requirements, credits, "
                f"availability, and auditions (embeddings skipped -- no OPENAI_API_KEY or SKIP_EMBEDDINGS set)."
            )
    finally:
        if close:
            db.close()


if __name__ == "__main__":
    seed_db()
