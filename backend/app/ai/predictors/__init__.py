"""Local predictive signals — zero API cost (heuristic stand-ins for trained models)."""
from __future__ import annotations

from typing import Any


def no_show_risk(talent_or_row: Any) -> float:
    """
    P(cancel / early-terminate) in 0..1 from reliability fields.
    Higher = riskier.
    """
    get = _getter(talent_or_row)
    cancel = float(get("cancellation_rate") or 0)
    attend = float(get("rehearsal_attendance_rate") or 1)
    rehire = float(get("rehire_rate") or 0.5)
    response_h = float(get("response_time_hours") or 24)
    # Weighted heuristic
    risk = (
        0.45 * min(1.0, cancel)
        + 0.25 * max(0.0, 1.0 - attend)
        + 0.20 * max(0.0, 1.0 - rehire)
        + 0.10 * min(1.0, response_h / 72.0)
    )
    return round(max(0.0, min(1.0, risk)), 3)


def fair_rate_usd(talent_or_row: Any) -> float:
    """Expected weekly_contract_rate_usd from experience/rating/skill."""
    get = _getter(talent_or_row)
    years = float(get("experience_years") or 0)
    rating = float(get("average_director_rating") or 3.5)
    level = str(get("physical_skill_level") or "Standard")
    base = 800.0 + years * 120.0 + rating * 200.0
    if level.lower() == "elite":
        base *= 1.35
    elif level.lower() == "advanced":
        base *= 1.15
    return round(base, 2)


def impute_audition_score(scores: dict[str, Any] | None) -> float | None:
    """Impute panel_score from sub-scores when missing."""
    if not scores:
        return None
    if scores.get("panel_score") is not None:
        try:
            return float(scores["panel_score"])
        except (TypeError, ValueError):
            pass
    parts = []
    for key in (
        "technical_score",
        "artistic_score",
        "response_to_direction_score",
        "safety_awareness_score",
    ):
        val = scores.get(key)
        if val is not None:
            try:
                parts.append(float(val))
            except (TypeError, ValueError):
                continue
    if not parts:
        return None
    return round(sum(parts) / len(parts), 2)


_POS = {
    "excellent",
    "outstanding",
    "reliable",
    "professional",
    "delight",
    "strong",
    "recommend",
    "rehire",
    "punctual",
}
_NEG = {
    "late",
    "unreliable",
    "incident",
    "unsafe",
    "difficult",
    "cancel",
    "no-show",
    "conflict",
    "poor",
}


def feedback_sentiment(text: str | None) -> dict[str, Any]:
    """Keyword sentiment 0..1 + theme tags from director_feedback / panel_notes."""
    raw = (text or "").strip()
    if not raw:
        return {"score": 0.5, "themes": [], "label": "neutral"}
    lower = raw.lower()
    pos = sum(1 for w in _POS if w in lower)
    neg = sum(1 for w in _NEG if w in lower)
    total = pos + neg
    if total == 0:
        score = 0.55
    else:
        score = pos / total
    themes: list[str] = []
    if pos:
        themes.append("positive_feedback")
    if neg:
        themes.append("risk_language")
    if "safety" in lower or "unsafe" in lower:
        themes.append("safety")
    if "rehire" in lower:
        themes.append("rehire")
    label = "positive" if score >= 0.6 else ("negative" if score <= 0.4 else "neutral")
    return {"score": round(score, 3), "themes": themes, "label": label}


def booking_success_prior(row: dict[str, Any]) -> float:
    """0..100 prior for re-rank — combines base signals already on the match row."""
    base = float(row.get("score") or 0)
    talent = row.get("talent") or row
    get = _getter(talent)
    risk = no_show_risk(talent)
    rating = float(get("average_director_rating") or 3.5)
    reliability = (1.0 - risk) * 40.0 + (rating / 5.0) * 20.0
    # Blend toward base score
    return round(min(100.0, 0.5 * base + 0.5 * (reliability + base * 0.3)), 2)


def predict_signals(talent: Any) -> dict[str, Any]:
    """Bundle advisory signals for UI badges."""
    risk = no_show_risk(talent)
    fair = fair_rate_usd(talent)
    get = _getter(talent)
    actual = get("weekly_contract_rate_usd")
    budget_note = None
    if actual is not None:
        try:
            delta = float(actual) - fair
            if abs(delta) < 50:
                budget_note = "near_fair_rate"
            elif delta > 0:
                budget_note = "above_fair_rate"
            else:
                budget_note = "below_fair_rate"
        except (TypeError, ValueError):
            budget_note = None
    return {
        "no_show_risk": risk,
        "no_show_label": "high" if risk >= 0.45 else ("medium" if risk >= 0.25 else "low"),
        "fair_weekly_rate_usd": fair,
        "rate_vs_fair": budget_note,
        "source": "local_heuristic",
    }


def _getter(obj: Any):
    if isinstance(obj, dict):
        return lambda k: obj.get(k)
    return lambda k: getattr(obj, k, None)
