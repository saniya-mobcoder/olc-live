"""F01/F02 pilot upgrades — dependency-aware gate graph + 4-layer scoring.

Everything here is ADDITIVE and ADVISORY:
- `eligible` and `final_match_score` (dataset-parity values from gates.py /
  scoring.py) are never modified — parity with match_ground_truth.csv holds.
- The gate graph re-presents the same booleans with applicability + dependency
  context so rejection UIs and LLM explanations are cleaner.
- Layers 3 (semantic) and 4 (behavioral) feed an `advisory_score` that is
  clearly labelled and used only to re-order the *eligible* pool when the
  recruiter opts into advisory ranking.
"""
from __future__ import annotations

from datetime import date
from typing import Any

from ..ai.predictors import booking_success_prior, no_show_risk
from ..models import Requirement, Talent

# ---------------------------------------------------------------------------
# F01 — dependency-aware gate graph
# ---------------------------------------------------------------------------

# gate -> (depends_on gates, applicability predicate over the requirement)
# A gate that is not applicable is reported "not_applicable", never "fail".
# A gate whose dependency already failed is reported with `masked_by` so the
# UI/LLM leads with the root cause instead of a wall of red.
_GATE_SPEC: dict[str, dict[str, Any]] = {
    "profile_active": {"depends_on": [], "applicable": lambda r: True},
    "verification_eligible": {"depends_on": ["profile_active"], "applicable": lambda r: True},
    "role_eligible": {"depends_on": ["profile_active"], "applicable": lambda r: True},
    "mandatory_skills_met": {"depends_on": ["role_eligible"], "applicable": lambda r: True},
    "full_contract_availability_met": {"depends_on": ["profile_active"], "applicable": lambda r: True},
    "overnight_rehearsal_eligible": {
        "depends_on": ["full_contract_availability_met"],
        "applicable": lambda r: bool(r.overnight_rehearsal_required),
    },
    "audition_met": {
        "depends_on": ["role_eligible"],
        "applicable": lambda r: bool(r.audition_required) or float(r.minimum_showreel_score or 0) > 0,
    },
    "physical_technical_eligible": {"depends_on": ["role_eligible"], "applicable": lambda r: True},
    "safety_certification_eligible": {
        "depends_on": ["physical_technical_eligible"],
        "applicable": lambda r: bool(r.required_safety_certifications),
    },
    "medical_clearance_eligible": {
        "depends_on": ["safety_certification_eligible"],
        "applicable": lambda r: bool(r.medical_clearance_required),
    },
    "mobility_work_authorization_eligible": {"depends_on": ["profile_active"], "applicable": lambda r: True},
    "language_eligible": {
        "depends_on": ["role_eligible"],
        "applicable": lambda r: bool(r.required_languages),
    },
}

_GATE_EVIDENCE_KEYS: dict[str, list[str]] = {
    "mandatory_skills_met": ["missing_mandatory_skills"],
    "safety_certification_eligible": ["missing_certs"],
    "language_eligible": ["missing_languages"],
    "mobility_work_authorization_eligible": ["same_country", "authorized", "passport_ok", "mobility_ok"],
    "full_contract_availability_met": ["partial"],
    "physical_technical_eligible": ["physical_ok", "aquatic_ok", "aerial_ok", "stunt_ok"],
    "audition_met": ["showreel_ok", "audition_ok"],
}


def gate_graph(req: Requirement, gate_result: dict[str, Any]) -> list[dict[str, Any]]:
    """Structured, dependency-aware view over the 12 hard gates.

    Statuses: pass | fail | not_applicable. Failed gates whose dependency also
    failed carry `masked_by` (root-cause first). Booleans are read verbatim from
    gates.evaluate_gates() output — never recomputed.
    """
    details = gate_result.get("details", {})
    report: list[dict[str, Any]] = []
    for gate, spec in _GATE_SPEC.items():
        applicable = bool(spec["applicable"](req))
        passed = bool(gate_result.get(gate))
        if not applicable:
            status = "not_applicable"
        else:
            status = "pass" if passed else "fail"
        masked_by = [
            dep for dep in spec["depends_on"]
            if status == "fail" and not bool(gate_result.get(dep))
        ]
        evidence = {
            k: (sorted(details[k]) if isinstance(details.get(k), set) else details.get(k))
            for k in _GATE_EVIDENCE_KEYS.get(gate, [])
            if k in details
        }
        report.append(
            {
                "gate": gate,
                "status": status,
                "depends_on": spec["depends_on"],
                "masked_by": masked_by,
                "evidence": evidence,
            }
        )
    return report


def root_cause_gates(report: list[dict[str, Any]]) -> list[str]:
    """Failed gates that are NOT masked by an upstream failure — lead with these."""
    return [g["gate"] for g in report if g["status"] == "fail" and not g["masked_by"]]


# ---------------------------------------------------------------------------
# F04 — near-miss gap analysis
# ---------------------------------------------------------------------------

def near_miss_gaps(gate_result: dict[str, Any], report: list[dict[str, Any]]) -> dict[str, Any] | None:
    """If a candidate fails on <=2 root-cause gates, describe exactly what is
    missing so the UI can show an actionable 'near miss' tray."""
    if gate_result.get("eligible"):
        return None
    roots = root_cause_gates(report)
    if not roots or len(roots) > 2:
        return None
    details = gate_result.get("details", {})
    gaps: list[dict[str, Any]] = []
    for gate in roots:
        gap: dict[str, Any] = {"gate": gate}
        if gate == "mandatory_skills_met":
            gap["missing"] = details.get("missing_mandatory_skills", [])
        elif gate == "safety_certification_eligible":
            gap["missing"] = details.get("missing_certs", [])
        elif gate == "language_eligible":
            gap["missing"] = details.get("missing_languages", [])
        elif gate == "full_contract_availability_met":
            statuses = details.get("statuses", [])
            gap["unavailable_days"] = sum(1 for s in statuses if s != "Available")
            gap["window_days"] = len(statuses)
        gaps.append(gap)
    return {"is_near_miss": True, "root_cause_gates": roots, "gaps": gaps}


# ---------------------------------------------------------------------------
# F02 — confidence level (how much data backs this score)
# ---------------------------------------------------------------------------

def confidence_level(talent: Talent, *, audition_score: float | None) -> dict[str, Any]:
    """0..1 confidence from data coverage — NOT from the score itself.

    Drivers: profile completeness, director-rating history, real audition data,
    credit depth, verification, recency of activity.
    """
    drivers: list[str] = []
    completeness = float(talent.profile_completion_percentage or 0) / 100.0
    c = 0.30 * completeness
    if completeness < 0.8:
        drivers.append("profile_incomplete")

    if talent.average_director_rating is not None:
        c += 0.20
    else:
        drivers.append("no_director_rating_history")

    if audition_score is not None:
        c += 0.20
    else:
        drivers.append("no_audition_for_this_requirement")

    productions = int(talent.completed_productions or 0)
    c += 0.15 * min(1.0, productions / 5.0)
    if productions < 2:
        drivers.append("thin_credit_history")

    if talent.identity_verified and talent.professional_references_verified:
        c += 0.10
    else:
        drivers.append("verification_incomplete")

    last_active = talent.last_active_date
    if isinstance(last_active, date) and (date(2026, 7, 1) - last_active).days <= 90:
        c += 0.05
    else:
        drivers.append("low_recent_activity")

    score = round(max(0.0, min(1.0, c)), 3)
    level = "high" if score >= 0.75 else ("medium" if score >= 0.5 else "low")
    return {"score": score, "level": level, "drivers": drivers}


# ---------------------------------------------------------------------------
# F02 — four-layer scoring assembly
# ---------------------------------------------------------------------------

# Advisory blend weights (eligible candidates only). Semantic is optional —
# when absent its weight folds into the deterministic layer, never invented.
_ADVISORY_W_WEIGHTED = 0.70
_ADVISORY_W_BEHAVIORAL = 0.15
_ADVISORY_W_SEMANTIC = 0.15


def four_layer_score(
    req: Requirement,
    talent: Talent,
    score_result: dict[str, Any],
    *,
    feedback_prior_value: float,
    semantic_score: float | None = None,
    audition_score: float | None = None,
) -> dict[str, Any]:
    """Assemble the 4-layer view. Layer 2 final_match_score is authoritative and
    unchanged; advisory_score is a labelled, optional re-ranking aid."""
    eligible = bool(score_result["eligible"])
    weighted = float(score_result["score"] or 0.0)

    behavioral_prior = booking_success_prior({"score": weighted, "talent": talent})
    behavioral = round(0.5 * behavioral_prior + 0.5 * float(feedback_prior_value or 0.0), 2)

    if eligible:
        if semantic_score is not None:
            advisory = (
                _ADVISORY_W_WEIGHTED * weighted
                + _ADVISORY_W_BEHAVIORAL * behavioral
                + _ADVISORY_W_SEMANTIC * float(semantic_score)
            )
        else:
            w_det = _ADVISORY_W_WEIGHTED + _ADVISORY_W_SEMANTIC
            advisory = w_det * weighted + _ADVISORY_W_BEHAVIORAL * behavioral
        advisory = round(min(100.0, max(0.0, advisory)), 2)
    else:
        advisory = None  # advisory ranking never resurrects an ineligible candidate

    return {
        "layer1_eligibility": {
            "score": 100.0 if eligible else 0.0,
            "failed_gates": score_result.get("failed_gates", []),
        },
        "layer2_weighted": {
            "score": weighted,
            "factors": (score_result.get("breakdown") or {}).get("factors", {}),
            "authoritative": True,
        },
        "layer3_semantic": {
            "score": round(float(semantic_score), 2) if semantic_score is not None else None,
            "source": "pgvector_cosine" if semantic_score is not None else "unavailable",
            "advisory_only": True,
        },
        "layer4_behavioral": {
            "score": behavioral,
            "booking_success_prior": behavioral_prior,
            "feedback_prior": round(float(feedback_prior_value or 0.0), 2),
            "no_show_risk": no_show_risk(talent),
            "advisory_only": True,
        },
        "advisory_score": advisory,
        "confidence": confidence_level(talent, audition_score=audition_score),
    }
