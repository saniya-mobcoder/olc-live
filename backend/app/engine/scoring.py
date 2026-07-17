"""Explainable weighted scoring 0-100 -- exact port of evaluate_match() from
generate_olc_aligned_dataset.py so scores/labels reproduce match_ground_truth.csv.

Weights (must sum to 1.0):
  skills 25% | production credits 15% | availability 15% | audition/showreel 10%
  physical/technical 10% | mobility 8% | reliability 7% | safety 5% | budget 3% | language 2%
"""
from __future__ import annotations

from typing import Any

from ..models import Requirement, Talent
from .gates import evaluate_gates

WEIGHTS = {
    "skill_score": 0.25,
    "production_credit_score": 0.15,
    "availability_score": 0.15,
    "audition_showreel_score": 0.10,
    "physical_technical_score": 0.10,
    "mobility_score": 0.08,
    "reliability_score": 0.07,
    "safety_compliance_score": 0.05,
    "budget_score": 0.03,
    "language_cultural_score": 0.02,
}


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def match_category(eligible: bool, score: float) -> str:
    if not eligible:
        return "Not Eligible"
    if score >= 85:
        return "Excellent Match"
    if score >= 70:
        return "Good Match"
    if score >= 50:
        return "Partial Match"
    return "Weak Match"


def ground_truth_label(eligible: bool, score: float) -> str:
    if not eligible:
        return "Hard Rejection"
    if score >= 85:
        return "Strong Positive"
    if score >= 70:
        return "Positive"
    if score >= 50:
        return "Borderline"
    return "Negative"


def compute_score(
    req: Requirement,
    talent: Talent,
    *,
    availability_lookup: dict[tuple[str, str], dict[str, Any]],
    audition_score: float | None,
) -> dict[str, Any]:
    gate = evaluate_gates(req, talent, availability_lookup=availability_lookup, audition_score=audition_score)
    d = gate["details"]

    # --- Skill score: 78% mandatory coverage + 22% preferred coverage ---
    mandatory, preferred, talent_skills = d["mandatory"], d["preferred"], d["talent_skills"]
    skill_score = 100 * (
        0.78 * (len(mandatory & talent_skills) / max(1, len(mandatory)))
        + 0.22 * (len(preferred & talent_skills) / max(1, len(preferred)))
    )

    # --- Availability score ---
    statuses = d["statuses"]
    if gate["full_contract_availability_met"]:
        availability_score = 100.0
    elif all(s in {"Available", "Tentatively Available"} for s in statuses):
        availability_score = 65.0
    else:
        availability_score = max(0.0, 100 * statuses.count("Available") / max(1, len(statuses)))

    # --- Mobility score ---
    same_country, authorized = d["same_country"], d["authorized"]
    if same_country:
        mobility_score = 100.0
    elif authorized:
        mobility_score = 92.0
    elif talent.travel_ready and req.visa_sponsorship_available:
        mobility_score = 76.0
    else:
        mobility_score = 20.0
    if not req.travel_provided and not same_country:
        mobility_score -= 18.0

    # --- Budget score ---
    rate = d["rate"]
    if rate <= req.weekly_budget_min_usd:
        budget_score = 100.0
    elif gate["budget_eligible"]:
        span = max(1.0, req.weekly_budget_max_usd - req.weekly_budget_min_usd)
        budget_score = 100.0 - 25.0 * (rate - req.weekly_budget_min_usd) / span
    else:
        budget_score = max(0.0, 70.0 - 70.0 * (rate - req.weekly_budget_max_usd) / max(1.0, req.weekly_budget_max_usd))

    # --- Production credit relevance ---
    credit_relevance = 0.0
    prefs = set(talent.preferred_production_types or [])
    if req.production_type in prefs:
        credit_relevance += 35.0
    credit_relevance += min(50.0, float(talent.completed_productions) * 4.0)
    if gate["role_eligible"]:
        credit_relevance += 15.0
    production_credit_score = min(100.0, credit_relevance)

    # --- Audition / showreel ---
    fallback_audition = audition_score if audition_score is not None else talent.audition_readiness_score
    audition_showreel_score = 0.52 * talent.showreel_quality_score + 0.48 * fallback_audition

    # --- Physical / technical ---
    physical_technical_score = 100.0 * (
        sum([d["physical_ok"], d["aquatic_ok"], d["aerial_ok"], d["stunt_ok"]]) / 4.0
    )

    # --- Safety compliance ---
    safety_bonus = {"Advanced": 10.0, "Intermediate": 3.0}.get(talent.safety_training_level, -4.0)
    safety_score = clamp(100.0 - talent.safety_incident_rate * 500.0 + safety_bonus, 0.0, 100.0)

    # --- Reliability ---
    reliability_score = clamp(
        100.0
        * (
            0.36 * talent.rehearsal_attendance_rate
            + 0.28 * talent.rehire_rate
            + 0.20 * (1 - talent.cancellation_rate)
            + 0.16 * (1 - talent.safety_incident_rate)
        ),
        0.0,
        100.0,
    )

    # --- Language ---
    if gate["language_eligible"]:
        language_score = 100.0
    elif "English" in (talent.languages or []):
        language_score = 40.0
    else:
        language_score = 10.0

    factors = {
        "skill_score": round(skill_score, 2),
        "production_credit_score": round(production_credit_score, 2),
        "availability_score": round(availability_score, 2),
        "audition_showreel_score": round(audition_showreel_score, 2),
        "physical_technical_score": round(physical_technical_score, 2),
        "mobility_score": round(mobility_score, 2),
        "reliability_score": round(reliability_score, 2),
        "safety_compliance_score": round(safety_score, 2),
        "budget_score": round(budget_score, 2),
        "language_cultural_score": round(language_score, 2),
    }

    final_score = round(clamp(sum(factors[k] * WEIGHTS[k] for k in WEIGHTS), 0.0, 100.0), 2)
    eligible = gate["eligible"]
    category = match_category(eligible, final_score)
    label = ground_truth_label(eligible, final_score)

    reasons: list[str] = []
    risks: list[str] = []
    rejects: list[str] = []

    if gate["role_eligible"]:
        reasons.append(f"Eligible for the required {req.required_primary_role} discipline")
    else:
        rejects.append("Required discipline or talent category not matched")

    if gate["mandatory_skills_met"]:
        reasons.append("Meets all mandatory production skills")
    else:
        rejects.append("Missing mandatory production skill")

    if gate["full_contract_availability_met"]:
        reasons.append("Available for the complete rehearsal and performance contract window")
    else:
        rejects.append("Not fully available for the contract window")

    if production_credit_score >= 75:
        reasons.append(f"Relevant history across {int(talent.completed_productions)} completed productions")

    if gate["audition_met"]:
        reasons.append("Meets audition and showreel thresholds")
    else:
        rejects.append("Audition or showreel threshold not met")

    if gate["physical_technical_eligible"]:
        reasons.append("Meets physical and technical suitability requirements")
    else:
        rejects.append("Physical or specialist technical requirement not met")

    if gate["mobility_work_authorization_eligible"]:
        reasons.append(f"Travel and work eligibility is feasible for {req.country}")
    else:
        rejects.append("Travel, passport, visa, or work authorisation condition not met")

    if gate["safety_certification_eligible"] and gate["medical_clearance_eligible"]:
        reasons.append("Required safety credentials and medical clearance are satisfied")
    else:
        rejects.append("Required safety certification or medical clearance missing")

    if gate["language_eligible"]:
        reasons.append("Supports all mandatory production languages")
    else:
        rejects.append("Required language not supported")

    if not gate["overnight_rehearsal_eligible"]:
        rejects.append("Overnight rehearsal availability required")
    if not gate["profile_active"]:
        rejects.append("Profile inactive")
    if not gate["verification_eligible"]:
        rejects.append("Identity or professional references not fully verified")

    if rate > req.weekly_budget_max_usd:
        risks.append("Weekly rate exceeds the maximum production budget")
    elif rate >= req.weekly_budget_max_usd * 0.92:
        risks.append("Weekly rate is close to the maximum production budget")
    if not d["same_country"] and not req.travel_provided:
        risks.append("International travel is not provided by the production")
    if talent.cancellation_rate >= 0.15:
        risks.append("Historical cancellation rate is above the preferred threshold")
    if talent.response_time_hours > 24:
        risks.append("Response time is higher than the platform target")
    if talent.profile_completion_percentage < 80:
        risks.append("Profile information is incomplete")
    if talent.average_director_rating is None:
        risks.append("New talent has limited director-rating history")

    return {
        **{k: gate[k] for k in (
            "role_eligible", "mandatory_skills_met", "full_contract_availability_met", "audition_met",
            "physical_technical_eligible", "mobility_work_authorization_eligible",
            "safety_certification_eligible", "medical_clearance_eligible", "language_eligible",
            "overnight_rehearsal_eligible", "profile_active", "verification_eligible",
            "budget_eligible", "experience_eligible", "rating_eligible",
        )},
        "eligible": eligible,
        "score": final_score,
        "match_category": category,
        "ground_truth_label": label,
        "breakdown": {"factors": factors, "weights": WEIGHTS, "weighted_total": final_score},
        "positive_match_reasons": reasons[:6],
        "risk_factors": risks,
        "rejection_reasons": list(dict.fromkeys(rejects)),
        "failed_gates": [
            k for k in (
                "role_eligible", "mandatory_skills_met", "full_contract_availability_met", "audition_met",
                "physical_technical_eligible", "mobility_work_authorization_eligible",
                "safety_certification_eligible", "medical_clearance_eligible", "language_eligible",
                "overnight_rehearsal_eligible", "profile_active", "verification_eligible",
            ) if not gate[k]
        ],
        "distance_km": round(d["distance_km"], 1),
        "audition_score": round(audition_score, 2) if audition_score is not None else None,
    }
