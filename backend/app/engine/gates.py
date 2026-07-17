"""Hard constraints + shared eligibility facts, mirroring evaluate_match() in
generate_olc_aligned_dataset.py so results reproduce match_ground_truth.csv exactly.

Twelve hard gates decide `eligible`. budget_eligible / experience_eligible /
rating_eligible are computed (and surfaced) but are NOT gating -- the dataset's
own generator computes them purely as informational signals; a high score
cannot be blocked by budget/experience/rating alone in the reference data.
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from ..models import Requirement, Talent

PHYSICAL_RANK = {"Standard": 1, "Athletic": 2, "Elite": 3}


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    from math import asin, atan2, cos, radians, sin, sqrt

    r = 6371.0
    p1, p2 = radians(lat1), radians(lat2)
    dp = radians(lat2 - lat1)
    dl = radians(lon2 - lon1)
    a = sin(dp / 2) ** 2 + cos(p1) * cos(p2) * sin(dl / 2) ** 2
    return r * 2 * atan2(sqrt(a), sqrt(1 - a))


def contract_window(req: Requirement) -> tuple[date, date]:
    """Availability must span rehearsal_start_date .. performance_end_date."""
    return req.rehearsal_start_date, req.performance_end_date


def availability_statuses(
    req: Requirement,
    talent: Talent,
    availability_lookup: dict[tuple[str, str], dict[str, Any]],
) -> tuple[list[str], bool]:
    start, end = contract_window(req)
    statuses: list[str] = []
    partial = False
    for offset in range((end - start).days + 1):
        d = (start + timedelta(days=offset)).isoformat()
        row = availability_lookup.get((talent.talent_id, d))
        statuses.append(row["availability_status"] if row else "Unavailable")
        partial = partial or bool(row and row.get("partially_available"))
    return statuses, partial


def evaluate_gates(
    req: Requirement,
    talent: Talent,
    *,
    availability_lookup: dict[tuple[str, str], dict[str, Any]],
    audition_score: float | None,
) -> dict[str, Any]:
    # --- Role / discipline ---
    accepted_roles = {req.required_primary_role, *(req.acceptable_secondary_roles or [])}
    talent_roles = {talent.primary_role, *(talent.secondary_roles or [])}
    role_eligible = bool(accepted_roles & talent_roles) and talent.talent_category == req.required_category

    # --- Mandatory skills ---
    talent_skills = set((talent.primary_skills or []) + (talent.secondary_skills or []))
    mandatory = set(req.mandatory_skills or [])
    preferred = set(req.preferred_skills or [])
    mandatory_skills_met = mandatory.issubset(talent_skills)

    # --- Full contract availability ---
    statuses, partial = availability_statuses(req, talent, availability_lookup)
    availability_met = all(s == "Available" for s in statuses) and not partial

    # --- Distance / mobility / passport ---
    distance_km = haversine_km(req.latitude, req.longitude, talent.latitude, talent.longitude)
    same_country = talent.country == req.country
    authorized = req.country in set(talent.work_authorized_countries or [])
    start, _ = contract_window(req)
    passport_deadline = start + timedelta(days=int(req.passport_validity_months_required * 30.4))
    passport_ok = talent.passport_valid_until >= passport_deadline
    mobility_ok = same_country or authorized or (talent.travel_ready and req.visa_sponsorship_available)

    # --- Budget (informational only -- not a hard gate in the reference data) ---
    rate = float(talent.weekly_contract_rate_usd)
    budget_eligible = rate <= float(req.weekly_budget_max_usd)

    # --- Experience / rating (informational only) ---
    experience_eligible = talent.experience_years >= req.minimum_experience_years
    rating_value = float(talent.average_director_rating) if talent.average_director_rating is not None else 0.0
    rating_eligible = req.minimum_director_rating <= 0 or rating_value >= req.minimum_director_rating

    # --- Audition / showreel ---
    showreel_ok = req.minimum_showreel_score <= 0 or talent.showreel_quality_score >= req.minimum_showreel_score
    audition_ok = (not req.audition_required) or (
        audition_score is not None and audition_score >= req.minimum_audition_score
    )

    # --- Physical / specialist technical ---
    physical_ok = PHYSICAL_RANK[talent.physical_skill_level] >= PHYSICAL_RANK[req.physical_skill_requirement]
    aquatic_ok = (not req.aquatic_experience_required) or bool(talent.aquatic_performance_experience)
    aerial_ok = (not req.aerial_experience_required) or bool(talent.aerial_performance_experience)
    stunt_ok = (not req.stunt_experience_required) or bool(talent.stunt_experience)
    physical_technical_ok = physical_ok and aquatic_ok and aerial_ok and stunt_ok

    # --- Safety certs / medical ---
    certs = set(talent.professional_certifications or [])
    required_certs = set(req.required_safety_certifications or [])
    safety_certs_ok = required_certs.issubset(certs)
    medical_ok = (not req.medical_clearance_required) or talent.medical_clearance_status == "Cleared"

    # --- Language ---
    language_ok = set(req.required_languages or []).issubset(set(talent.languages or []))

    # --- Overnight / profile status / verification ---
    overnight_ok = (not req.overnight_rehearsal_required) or bool(talent.overnight_rehearsal_available)
    active_ok = talent.profile_status == "Active"
    verification_ok = bool(talent.identity_verified and talent.professional_references_verified)

    hard_checks = {
        "role_eligible": role_eligible,
        "mandatory_skills_met": mandatory_skills_met,
        "full_contract_availability_met": availability_met,
        "audition_met": audition_ok and showreel_ok,
        "physical_technical_eligible": physical_technical_ok,
        "mobility_work_authorization_eligible": mobility_ok and passport_ok,
        "safety_certification_eligible": safety_certs_ok,
        "medical_clearance_eligible": medical_ok,
        "language_eligible": language_ok,
        "overnight_rehearsal_eligible": overnight_ok,
        "profile_active": active_ok,
        "verification_eligible": verification_ok,
    }

    return {
        **hard_checks,
        "eligible": all(hard_checks.values()),
        "budget_eligible": budget_eligible,
        "experience_eligible": experience_eligible,
        "rating_eligible": rating_eligible,
        "details": {
            "mandatory": mandatory,
            "preferred": preferred,
            "talent_skills": talent_skills,
            "missing_mandatory_skills": sorted(mandatory - talent_skills),
            "statuses": statuses,
            "partial": partial,
            "distance_km": distance_km,
            "same_country": same_country,
            "authorized": authorized,
            "passport_ok": passport_ok,
            "mobility_ok": mobility_ok,
            "rate": rate,
            "showreel_ok": showreel_ok,
            "audition_ok": audition_ok,
            "physical_ok": physical_ok,
            "aquatic_ok": aquatic_ok,
            "aerial_ok": aerial_ok,
            "stunt_ok": stunt_ok,
            "safety_certs_ok": safety_certs_ok,
            "missing_certs": sorted(required_certs - certs),
            "medical_ok": medical_ok,
            "language_ok": language_ok,
            "missing_languages": sorted(set(req.required_languages or []) - set(talent.languages or [])),
            "overnight_ok": overnight_ok,
            "active_ok": active_ok,
            "verification_ok": verification_ok,
        },
    }
