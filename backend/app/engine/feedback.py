"""Feedback prior for hybrid ranking -- formula only, no ML."""
from __future__ import annotations

from sqlalchemy.orm import Session

from ..models import MatchDecision, MatchRun, Requirement, Talent
from .scoring import clamp

RULE_WEIGHT = 0.85
FEEDBACK_WEIGHT = 0.15


def feedback_prior(
    db: Session,
    talent: Talent,
    requirement: Requirement,
) -> float:
    """0-100 prior from this talent's decisions, role-similar decisions, and rehire_rate."""
    rehire_base = clamp(float(talent.rehire_rate or 0.0) * 100.0, 0.0, 100.0)

    talent_rows = (
        db.query(MatchDecision)
        .filter(MatchDecision.talent_id == talent.talent_id)
        .all()
    )
    talent_signal = _decision_hire_score(talent_rows)

    role_rows = (
        db.query(MatchDecision)
        .join(MatchRun, MatchRun.id == MatchDecision.run_id)
        .join(Requirement, Requirement.requirement_id == MatchRun.requirement_id)
        .join(Talent, Talent.talent_id == MatchDecision.talent_id)
        .filter(
            Requirement.required_primary_role == requirement.required_primary_role,
            Requirement.required_category == requirement.required_category,
        )
        .all()
    )
    role_signal = _decision_hire_score(role_rows)

    if talent_signal is not None:
        decision_part = talent_signal
    elif role_signal is not None:
        decision_part = role_signal
    else:
        decision_part = rehire_base

    prior = 0.6 * decision_part + 0.4 * rehire_base
    return round(clamp(prior, 0.0, 100.0), 2)


def _decision_hire_score(rows: list[MatchDecision]) -> float | None:
    if not rows:
        return None
    positive = sum(1 for r in rows if r.decision in ("hire", "hold"))
    return round(100.0 * positive / len(rows), 2)


def hybrid_sort_score(rule_score: float, prior: float) -> float:
    return round(RULE_WEIGHT * rule_score + FEEDBACK_WEIGHT * prior, 2)
