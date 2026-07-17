"""SQLAlchemy domain models — aligned to OLC_Aligned_AI_Talent_Matching_Dataset."""
from datetime import date, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .config import get_settings
from .database import IS_POSTGRES, Base

_settings = get_settings()

if IS_POSTGRES:
    from pgvector.sqlalchemy import Vector as _VectorType

    _EmbeddingType = _VectorType(_settings.embedding_dim)
else:
    _EmbeddingType = JSON


class Talent(Base):
    __tablename__ = "talents"

    talent_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    full_name: Mapped[str] = mapped_column(String(120))
    profile_title: Mapped[str] = mapped_column(String(160))
    talent_category: Mapped[str] = mapped_column(String(60))
    primary_role: Mapped[str] = mapped_column(String(80))
    secondary_roles: Mapped[list] = mapped_column(JSON, default=list)
    primary_skills: Mapped[list] = mapped_column(JSON, default=list)
    secondary_skills: Mapped[list] = mapped_column(JSON, default=list)
    experience_years: Mapped[float] = mapped_column(Float)
    city: Mapped[str] = mapped_column(String(120))
    country: Mapped[str] = mapped_column(String(80))
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    home_market_region: Mapped[str] = mapped_column(String(80))
    travel_ready: Mapped[bool] = mapped_column(Boolean, default=False)
    relocation_available: Mapped[bool] = mapped_column(Boolean, default=False)
    passport_valid_until: Mapped[date] = mapped_column(Date)
    work_authorized_countries: Mapped[list] = mapped_column(JSON, default=list)
    weekly_contract_rate_usd: Mapped[float] = mapped_column(Float)
    rehearsal_day_rate_usd: Mapped[float] = mapped_column(Float)
    performance_fee_usd: Mapped[float] = mapped_column(Float)
    buyout_rate_usd: Mapped[float] = mapped_column(Float)
    languages: Mapped[list] = mapped_column(JSON, default=list)
    showreel_quality_score: Mapped[float] = mapped_column(Float)
    audition_readiness_score: Mapped[float] = mapped_column(Float)
    physical_skill_level: Mapped[str] = mapped_column(String(20), default="Standard")
    aquatic_performance_experience: Mapped[bool] = mapped_column(Boolean, default=False)
    aerial_performance_experience: Mapped[bool] = mapped_column(Boolean, default=False)
    stunt_experience: Mapped[bool] = mapped_column(Boolean, default=False)
    medical_clearance_status: Mapped[str] = mapped_column(String(20), default="Not Required")
    safety_training_level: Mapped[str] = mapped_column(String(20), default="Basic")
    professional_certifications: Mapped[list] = mapped_column(JSON, default=list)
    portfolio_quality_score: Mapped[float] = mapped_column(Float)
    average_director_rating: Mapped[float | None] = mapped_column(Float, nullable=True)
    completed_productions: Mapped[int] = mapped_column(Integer, default=0)
    completed_performances: Mapped[int] = mapped_column(Integer, default=0)
    rehire_rate: Mapped[float] = mapped_column(Float, default=0.0)
    rehearsal_attendance_rate: Mapped[float] = mapped_column(Float, default=0.0)
    safety_incident_rate: Mapped[float] = mapped_column(Float, default=0.0)
    cancellation_rate: Mapped[float] = mapped_column(Float, default=0.0)
    response_time_hours: Mapped[float] = mapped_column(Float, default=0.0)
    profile_completion_percentage: Mapped[float] = mapped_column(Float, default=0.0)
    identity_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    professional_references_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    preferred_production_types: Mapped[list] = mapped_column(JSON, default=list)
    overnight_rehearsal_available: Mapped[bool] = mapped_column(Boolean, default=False)
    weekend_available: Mapped[bool] = mapped_column(Boolean, default=False)
    last_active_date: Mapped[date] = mapped_column(Date)
    profile_status: Mapped[str] = mapped_column(String(20), default="Active")
    # pgvector column on Postgres; JSON list fallback for SQLite tests
    embedding: Mapped[list | None] = mapped_column(_EmbeddingType, nullable=True)


class Requirement(Base):
    __tablename__ = "requirements"

    requirement_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    production_id: Mapped[str] = mapped_column(String(32))
    production_title: Mapped[str] = mapped_column(String(200))
    production_type: Mapped[str] = mapped_column(String(80))
    fictional_client_id: Mapped[str] = mapped_column(String(32))
    required_category: Mapped[str] = mapped_column(String(60))
    required_primary_role: Mapped[str] = mapped_column(String(80))
    acceptable_secondary_roles: Mapped[list] = mapped_column(JSON, default=list)
    mandatory_skills: Mapped[list] = mapped_column(JSON, default=list)
    preferred_skills: Mapped[list] = mapped_column(JSON, default=list)
    city: Mapped[str] = mapped_column(String(120))
    country: Mapped[str] = mapped_column(String(80))
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    venue_type: Mapped[str] = mapped_column(String(80))
    rehearsal_start_date: Mapped[date] = mapped_column(Date)
    rehearsal_end_date: Mapped[date] = mapped_column(Date)
    technical_rehearsal_start_date: Mapped[date] = mapped_column(Date)
    technical_rehearsal_end_date: Mapped[date] = mapped_column(Date)
    performance_start_date: Mapped[date] = mapped_column(Date)
    performance_end_date: Mapped[date] = mapped_column(Date)
    number_of_performances: Mapped[int] = mapped_column(Integer, default=0)
    contract_duration_days: Mapped[int] = mapped_column(Integer, default=0)
    talent_required: Mapped[int] = mapped_column(Integer, default=1)
    ensemble_or_solo: Mapped[str] = mapped_column(String(40), default="Solo")
    minimum_experience_years: Mapped[float] = mapped_column(Float, default=0.0)
    minimum_director_rating: Mapped[float] = mapped_column(Float, default=0.0)
    minimum_showreel_score: Mapped[float] = mapped_column(Float, default=0.0)
    minimum_audition_score: Mapped[float] = mapped_column(Float, default=0.0)
    physical_skill_requirement: Mapped[str] = mapped_column(String(20), default="Standard")
    aquatic_experience_required: Mapped[bool] = mapped_column(Boolean, default=False)
    aerial_experience_required: Mapped[bool] = mapped_column(Boolean, default=False)
    stunt_experience_required: Mapped[bool] = mapped_column(Boolean, default=False)
    required_safety_certifications: Mapped[list] = mapped_column(JSON, default=list)
    medical_clearance_required: Mapped[bool] = mapped_column(Boolean, default=False)
    audition_required: Mapped[bool] = mapped_column(Boolean, default=False)
    passport_validity_months_required: Mapped[int] = mapped_column(Integer, default=6)
    visa_sponsorship_available: Mapped[bool] = mapped_column(Boolean, default=False)
    required_languages: Mapped[list] = mapped_column(JSON, default=list)
    overnight_rehearsal_required: Mapped[bool] = mapped_column(Boolean, default=False)
    weekly_budget_min_usd: Mapped[float] = mapped_column(Float, default=0.0)
    weekly_budget_max_usd: Mapped[float] = mapped_column(Float, default=0.0)
    travel_provided: Mapped[bool] = mapped_column(Boolean, default=False)
    accommodation_provided: Mapped[bool] = mapped_column(Boolean, default=False)
    per_diem_usd: Mapped[float] = mapped_column(Float, default=0.0)
    production_risk_level: Mapped[str] = mapped_column(String(20), default="Medium")
    urgency_level: Mapped[str] = mapped_column(String(20), default="Standard")
    booking_created_date: Mapped[date] = mapped_column(Date)
    application_deadline: Mapped[date] = mapped_column(Date)
    special_instructions: Mapped[str] = mapped_column(Text, default="")
    requirement_status: Mapped[str] = mapped_column(String(40), default="Open")


class ProductionCredit(Base):
    __tablename__ = "production_credits"

    credit_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    talent_id: Mapped[str] = mapped_column(ForeignKey("talents.talent_id"), index=True)
    fictional_client_id: Mapped[str] = mapped_column(String(32))
    production_title: Mapped[str] = mapped_column(String(200))
    production_type: Mapped[str] = mapped_column(String(80))
    role: Mapped[str] = mapped_column(String(80))
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    city: Mapped[str] = mapped_column(String(120))
    country: Mapped[str] = mapped_column(String(80))
    contract_status: Mapped[str] = mapped_column(String(40))
    number_of_performances: Mapped[int] = mapped_column(Integer, default=0)
    contract_value_usd: Mapped[float] = mapped_column(Float, default=0.0)
    rehearsal_attendance_rate: Mapped[float] = mapped_column(Float, default=0.0)
    director_rating: Mapped[float] = mapped_column(Float, default=0.0)
    technical_readiness_score: Mapped[float] = mapped_column(Float, default=0.0)
    safety_compliance_score: Mapped[float] = mapped_column(Float, default=0.0)
    incident_recorded: Mapped[bool] = mapped_column(Boolean, default=False)
    incident_severity: Mapped[str] = mapped_column(String(20), default="None")
    rehire_eligible: Mapped[bool] = mapped_column(Boolean, default=False)
    early_termination_party: Mapped[str] = mapped_column(String(40), default="")
    early_termination_reason: Mapped[str] = mapped_column(String(120), default="")
    skills_used: Mapped[list] = mapped_column(JSON, default=list)
    director_feedback: Mapped[str] = mapped_column(Text, default="")


class TalentAvailability(Base):
    __tablename__ = "talent_availability"

    availability_id: Mapped[str] = mapped_column(String(48), primary_key=True)
    talent_id: Mapped[str] = mapped_column(ForeignKey("talents.talent_id"), index=True)
    availability_date: Mapped[date] = mapped_column(Date, index=True)
    availability_status: Mapped[str] = mapped_column(String(30))
    available_from: Mapped[str] = mapped_column(String(8), default="00:00")
    available_until: Mapped[str] = mapped_column(String(8), default="23:59")
    partially_available: Mapped[bool] = mapped_column(Boolean, default=False)
    booked_contract_reference: Mapped[str] = mapped_column(String(40), default="")
    advance_notice_days: Mapped[int] = mapped_column(Integer, default=0)
    overnight_available: Mapped[bool] = mapped_column(Boolean, default=False)
    last_updated_at: Mapped[datetime] = mapped_column(DateTime)

    __table_args__ = (
        Index("ix_availability_talent_date", "talent_id", "availability_date"),
    )


class AuditionEvaluation(Base):
    __tablename__ = "audition_evaluations"

    audition_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    requirement_id: Mapped[str] = mapped_column(ForeignKey("requirements.requirement_id"), index=True)
    talent_id: Mapped[str] = mapped_column(ForeignKey("talents.talent_id"), index=True)
    audition_date: Mapped[date] = mapped_column(Date)
    audition_format: Mapped[str] = mapped_column(String(40))
    technical_score: Mapped[float] = mapped_column(Float)
    artistic_score: Mapped[float] = mapped_column(Float)
    response_to_direction_score: Mapped[float] = mapped_column(Float)
    safety_awareness_score: Mapped[float] = mapped_column(Float)
    panel_score: Mapped[float] = mapped_column(Float)
    audition_outcome: Mapped[str] = mapped_column(String(20))
    panel_notes: Mapped[str] = mapped_column(Text, default="")

    __table_args__ = (
        Index("ix_audition_req_talent", "requirement_id", "talent_id"),
    )


class MatchRun(Base):
    __tablename__ = "match_runs"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    requirement_id: Mapped[str] = mapped_column(ForeignKey("requirements.requirement_id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    weights: Mapped[dict] = mapped_column(JSON, default=dict)
    scenario_label: Mapped[str] = mapped_column(String(120), default="baseline")
    params_override: Mapped[dict] = mapped_column(JSON, default=dict)

    results: Mapped[list["MatchResult"]] = relationship(back_populates="run")
    audits: Mapped[list["AuditEvent"]] = relationship(back_populates="run")
    decisions: Mapped[list["MatchDecision"]] = relationship(back_populates="run")


class MatchResult(Base):
    __tablename__ = "match_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("match_runs.id"))
    talent_id: Mapped[str] = mapped_column(ForeignKey("talents.talent_id"))
    eligible: Mapped[bool] = mapped_column(Boolean, default=False)
    rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    match_category: Mapped[str] = mapped_column(String(40), default="")
    breakdown: Mapped[dict] = mapped_column(JSON, default=dict)
    failed_gates: Mapped[list] = mapped_column(JSON, default=list)
    positive_reasons: Mapped[list] = mapped_column(JSON, default=list)
    risk_factors: Mapped[list] = mapped_column(JSON, default=list)
    rejection_reasons: Mapped[list] = mapped_column(JSON, default=list)
    distance_km: Mapped[float | None] = mapped_column(Float, nullable=True)

    run: Mapped["MatchRun"] = relationship(back_populates="results")


class MatchDecision(Base):
    """Producer decision on a shortlisted talent for a match run."""

    __tablename__ = "match_decisions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("match_runs.id"), index=True)
    talent_id: Mapped[str] = mapped_column(ForeignKey("talents.talent_id"), index=True)
    decision: Mapped[str] = mapped_column(String(20))  # hire | hold | reject
    reason: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    run: Mapped["MatchRun"] = relationship(back_populates="decisions")


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("match_runs.id"))
    talent_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    event_type: Mapped[str] = mapped_column(String(60))
    message: Mapped[str] = mapped_column(Text)
    detail: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    run: Mapped["MatchRun"] = relationship(back_populates="audits")


class ExecutiveReport(Base):
    __tablename__ = "executive_reports"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    period_start: Mapped[date] = mapped_column(Date)
    period_end: Mapped[date] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    scenario_label: Mapped[str] = mapped_column(String(120), default="")
    payload: Mapped[dict] = mapped_column(JSON, default=dict)


class StageLyncPerson(Base):
    """Mirrored StageLync talent-network profile (source system: talent.olc.live /
    StageLync). Independent of OLC's own Talent table until explicitly imported."""

    __tablename__ = "stagelync_people"

    stagelync_person_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    display_name: Mapped[str] = mapped_column(String(120))
    primary_role: Mapped[str] = mapped_column(String(80))
    secondary_roles: Mapped[list] = mapped_column(JSON, default=list)
    skills: Mapped[list] = mapped_column(JSON, default=list)
    city: Mapped[str] = mapped_column(String(120))
    country: Mapped[str] = mapped_column(String(80))
    latitude: Mapped[float] = mapped_column(Float, default=0.0)
    longitude: Mapped[float] = mapped_column(Float, default=0.0)
    languages: Mapped[list] = mapped_column(JSON, default=list)
    weekly_rate_usd: Mapped[float] = mapped_column(Float, default=0.0)
    experience_years: Mapped[float] = mapped_column(Float, default=0.0)
    physical_skill_level: Mapped[str] = mapped_column(String(20), default="Standard")
    aquatic: Mapped[bool] = mapped_column(Boolean, default=False)
    aerial: Mapped[bool] = mapped_column(Boolean, default=False)
    stunt: Mapped[bool] = mapped_column(Boolean, default=False)
    certifications: Mapped[list] = mapped_column(JSON, default=list)
    work_authorizations: Mapped[list] = mapped_column(JSON, default=list)
    profile_summary: Mapped[str] = mapped_column(Text, default="")
    synced_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    embedding: Mapped[list | None] = mapped_column(_EmbeddingType, nullable=True)


class StageLyncLink(Base):
    """Links a StageLync person to an imported OLC Talent row once a producer
    pulls them into the OLC pool. status: mirrored -> imported."""

    __tablename__ = "stagelync_links"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    stagelync_person_id: Mapped[str] = mapped_column(
        ForeignKey("stagelync_people.stagelync_person_id"), unique=True, index=True
    )
    talent_id: Mapped[str | None] = mapped_column(
        ForeignKey("talents.talent_id"), nullable=True, index=True
    )
    status: Mapped[str] = mapped_column(String(40), default="mirrored")
    imported_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class Booking(Base):
    """Confirmed talent booking created from a hire decision."""

    __tablename__ = "bookings"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    requirement_id: Mapped[str] = mapped_column(
        ForeignKey("requirements.requirement_id"), index=True
    )
    talent_id: Mapped[str] = mapped_column(ForeignKey("talents.talent_id"), index=True)
    match_run_id: Mapped[str] = mapped_column(ForeignKey("match_runs.id"), index=True)
    decision_id: Mapped[int | None] = mapped_column(
        ForeignKey("match_decisions.id"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(40), default="confirmed")
    weekly_rate_usd: Mapped[float] = mapped_column(Float, default=0.0)
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class MarketingDraft(Base):
    """Draft-only marketing copy generated from a booking or match run."""

    __tablename__ = "marketing_drafts"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    channel: Mapped[str] = mapped_column(String(40))
    body: Mapped[str] = mapped_column(Text, default="")
    source_ref: Mapped[str] = mapped_column(String(80), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
