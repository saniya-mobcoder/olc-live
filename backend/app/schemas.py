"""Pydantic schemas -- aligned to OLC_Aligned_AI_Talent_Matching_Dataset."""
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field


class RequirementOut(BaseModel):
    requirement_id: str
    production_id: str
    production_title: str
    production_type: str
    required_category: str
    required_primary_role: str
    acceptable_secondary_roles: list[str]
    mandatory_skills: list[str]
    preferred_skills: list[str]
    city: str
    country: str
    latitude: float
    longitude: float
    venue_type: str
    rehearsal_start_date: date
    rehearsal_end_date: date
    technical_rehearsal_start_date: date
    technical_rehearsal_end_date: date
    performance_start_date: date
    performance_end_date: date
    number_of_performances: int
    contract_duration_days: int
    talent_required: int
    ensemble_or_solo: str
    minimum_experience_years: float
    minimum_director_rating: float
    minimum_showreel_score: float
    minimum_audition_score: float
    physical_skill_requirement: str
    aquatic_experience_required: bool
    aerial_experience_required: bool
    stunt_experience_required: bool
    required_safety_certifications: list[str]
    medical_clearance_required: bool
    audition_required: bool
    passport_validity_months_required: int
    visa_sponsorship_available: bool
    required_languages: list[str]
    overnight_rehearsal_required: bool
    weekly_budget_min_usd: float
    weekly_budget_max_usd: float
    travel_provided: bool
    accommodation_provided: bool
    per_diem_usd: float
    production_risk_level: str
    urgency_level: str
    booking_created_date: date
    application_deadline: date
    special_instructions: str = ""
    requirement_status: str

    model_config = {"from_attributes": True}


class TalentOut(BaseModel):
    talent_id: str
    full_name: str
    profile_title: str
    talent_category: str
    primary_role: str
    secondary_roles: list[str]
    primary_skills: list[str]
    secondary_skills: list[str]
    experience_years: float
    city: str
    country: str
    latitude: float
    longitude: float
    travel_ready: bool
    relocation_available: bool
    passport_valid_until: date
    work_authorized_countries: list[str]
    weekly_contract_rate_usd: float
    rehearsal_day_rate_usd: float
    performance_fee_usd: float
    buyout_rate_usd: float
    languages: list[str]
    showreel_quality_score: float
    audition_readiness_score: float
    physical_skill_level: str
    aquatic_performance_experience: bool
    aerial_performance_experience: bool
    stunt_experience: bool
    medical_clearance_status: str
    safety_training_level: str
    professional_certifications: list[str]
    portfolio_quality_score: float
    average_director_rating: float | None = None
    completed_productions: int
    completed_performances: int
    rehire_rate: float
    rehearsal_attendance_rate: float
    safety_incident_rate: float
    cancellation_rate: float
    response_time_hours: float
    profile_completion_percentage: float
    identity_verified: bool
    professional_references_verified: bool
    preferred_production_types: list[str]
    overnight_rehearsal_available: bool
    weekend_available: bool
    last_active_date: date
    profile_status: str

    model_config = {"from_attributes": True}


class ProductionCreditOut(BaseModel):
    credit_id: str
    talent_id: str
    production_title: str
    production_type: str
    role: str
    start_date: date
    end_date: date
    city: str
    country: str
    contract_status: str
    number_of_performances: int
    contract_value_usd: float
    director_rating: float
    safety_compliance_score: float
    incident_recorded: bool
    rehire_eligible: bool
    skills_used: list[str]
    director_feedback: str

    model_config = {"from_attributes": True}


class MatchResultOut(BaseModel):
    talent_id: str
    talent: TalentOut | None = None
    eligible: bool
    rank: int | None = None
    score: float | None = None
    match_category: str = ""
    breakdown: dict[str, Any] = Field(default_factory=dict)
    failed_gates: list[str] = Field(default_factory=list)
    positive_reasons: list[str] = Field(default_factory=list)
    risk_factors: list[str] = Field(default_factory=list)
    rejection_reasons: list[str] = Field(default_factory=list)
    distance_km: float | None = None


class MatchRunOut(BaseModel):
    id: str
    requirement_id: str
    created_at: datetime
    scenario_label: str
    params_override: dict[str, Any] = Field(default_factory=dict)
    shortlist: list[MatchResultOut] = Field(default_factory=list)
    other_eligible: list[MatchResultOut] = Field(default_factory=list)
    rejected: list[MatchResultOut] = Field(default_factory=list)
    eligible_count: int = 0
    rejected_count: int = 0


class MatchRequest(BaseModel):
    requirement_id: str
    top_k: int = 5
    scenario_label: str = "baseline"
    params_override: dict[str, Any] = Field(default_factory=dict)
    ranking_mode: str = "rules_only"  # rules_only | hybrid


class MatchDecisionRequest(BaseModel):
    talent_id: str
    decision: str  # hire | hold | reject
    reason: str = ""


class MatchDecisionOut(BaseModel):
    id: int
    run_id: str
    talent_id: str
    decision: str
    reason: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ScoreAgainstRequest(BaseModel):
    talent_id: str
    requirement_id: str


class ScoreAgainstOut(BaseModel):
    talent_id: str
    requirement_id: str
    eligible: bool
    score: float | None = None
    match_category: str = ""
    failed_gates: list[str] = Field(default_factory=list)
    positive_reasons: list[str] = Field(default_factory=list)
    rejection_reasons: list[str] = Field(default_factory=list)
    risk_factors: list[str] = Field(default_factory=list)
    breakdown: dict[str, Any] = Field(default_factory=dict)
    distance_km: float | None = None


class WhatIfRequest(BaseModel):
    requirement_id: str
    baseline_label: str = "baseline"
    scenario_label: str = "what-if"
    params_override: dict[str, Any] = Field(default_factory=dict)
    top_k: int = 5


class WhatIfOut(BaseModel):
    baseline: MatchRunOut
    scenario: MatchRunOut
    eligible_delta: int
    new_talent_ids: list[str]
    lost_talent_ids: list[str]


class SearchRequest(BaseModel):
    query: str
    limit: int = 20


class CopilotRequest(BaseModel):
    message: str
    requirement_id: str | None = None
    match_run_id: str | None = None
    talent_id: str | None = None
    mode: str = "match"  # match | support


class CopilotResponse(BaseModel):
    reply: str
    sources: list[str] = Field(default_factory=list)


class JobParseRequest(BaseModel):
    brief_text: str


class JobParseOut(BaseModel):
    fields: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    missing_fields: list[str] = Field(default_factory=list)


class JobDedupeRequest(BaseModel):
    brief_text: str = ""
    title: str = ""


class JobDedupeOut(BaseModel):
    similar: list[dict[str, Any]] = Field(default_factory=list)


class JobConfirmRequest(BaseModel):
    fields: dict[str, Any] = Field(default_factory=dict)


class BookingCreateRequest(BaseModel):
    run_id: str
    talent_id: str


class BookingOut(BaseModel):
    id: str
    requirement_id: str
    talent_id: str
    match_run_id: str
    decision_id: int | None = None
    status: str
    weekly_rate_usd: float
    start_date: date
    end_date: date
    created_at: datetime
    production_title: str | None = None
    talent_name: str | None = None

    model_config = {"from_attributes": True}


class MarketingDraftRequest(BaseModel):
    channel: str  # linkedin | newsletter
    booking_id: str | None = None
    match_run_id: str | None = None


class MarketingDraftOut(BaseModel):
    id: str
    channel: str
    body: str
    source_ref: str
    created_at: datetime

    model_config = {"from_attributes": True}


class AuditEventOut(BaseModel):
    id: int
    run_id: str
    talent_id: str | None
    event_type: str
    message: str
    detail: dict[str, Any]
    created_at: datetime

    model_config = {"from_attributes": True}


class PoolAnalyticsOut(BaseModel):
    by_region: list[dict[str, Any]]
    by_role: list[dict[str, Any]]
    by_category: list[dict[str, Any]]
    gaps: list[dict[str, Any]]
    totals: dict[str, Any]


class ExecutiveReportRequest(BaseModel):
    period_start: date
    period_end: date
    scenario_label: str = "monthly"


class ExecutiveReportOut(BaseModel):
    id: str
    period_start: date
    period_end: date
    created_at: datetime
    scenario_label: str
    payload: dict[str, Any] = Field(default_factory=dict)

    model_config = {"from_attributes": True}


class StageLyncPersonOut(BaseModel):
    stagelync_person_id: str
    display_name: str
    primary_role: str
    secondary_roles: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    city: str
    country: str
    latitude: float
    longitude: float
    languages: list[str] = Field(default_factory=list)
    weekly_rate_usd: float
    experience_years: float
    physical_skill_level: str
    aquatic: bool
    aerial: bool
    stunt: bool
    certifications: list[str] = Field(default_factory=list)
    work_authorizations: list[str] = Field(default_factory=list)
    profile_summary: str = ""
    synced_at: datetime
    link_status: str = "mirrored"
    talent_id: str | None = None


class StageLyncSyncOut(BaseModel):
    synced: int
    total: int
    message: str


class StageLyncImportOut(BaseModel):
    stagelync_person_id: str
    talent_id: str
    status: str
    created: bool
