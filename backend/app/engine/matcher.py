"""Top-K matching orchestrator + audit trail."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from ..models import (
    AuditEvent,
    AuditionEvaluation,
    MatchResult,
    MatchRun,
    Requirement,
    Talent,
    TalentAvailability,
)
from .feedback import RULE_WEIGHT, FEEDBACK_WEIGHT, feedback_prior, hybrid_sort_score
from .gates import contract_window
from .layers import four_layer_score, gate_graph, near_miss_gaps
from .scoring import WEIGHTS, compute_score

# Requirement fields a what-if scenario is allowed to override.
_OVERRIDABLE_FIELDS = {
    "weekly_budget_max_usd",
    "weekly_budget_min_usd",
    "visa_sponsorship_available",
    "travel_provided",
    "minimum_experience_years",
    "minimum_director_rating",
    "minimum_showreel_score",
    "minimum_audition_score",
    "overnight_rehearsal_required",
    "medical_clearance_required",
    "required_safety_certifications",
    "required_languages",
    "passport_validity_months_required",
}


def _next_match_id(db: Session) -> str:
    count = db.query(MatchRun).count() + 1
    return f"MAT-{count:06d}"


def apply_requirement_overrides(req: Requirement, overrides: dict[str, Any] | None) -> Requirement:
    """Return a detached-like proxy with override fields applied, without
    mutating the persisted Requirement row. Unknown keys raise -- silent typos
    in a what-if request should not be allowed to quietly no-op."""
    if not overrides:
        return req

    unknown = set(overrides) - _OVERRIDABLE_FIELDS
    if unknown:
        raise ValueError(f"Unsupported override field(s): {', '.join(sorted(unknown))}")

    class ReqProxy:
        pass

    proxy = ReqProxy()
    for col in Requirement.__table__.columns:
        setattr(proxy, col.name, getattr(req, col.name))
    for key, value in overrides.items():
        setattr(proxy, key, value)
    return proxy  # type: ignore[return-value]


def build_availability_lookup(db: Session, req: Requirement) -> dict[tuple[str, str], dict[str, Any]]:
    start, end = contract_window(req)
    rows = (
        db.query(TalentAvailability)
        .filter(TalentAvailability.availability_date >= start, TalentAvailability.availability_date <= end)
        .all()
    )
    return {
        (r.talent_id, r.availability_date.isoformat()): {
            "availability_status": r.availability_status,
            "partially_available": r.partially_available,
        }
        for r in rows
    }


def build_audition_lookup(db: Session, requirement_id: str) -> dict[str, float]:
    rows = (
        db.query(AuditionEvaluation)
        .filter(AuditionEvaluation.requirement_id == requirement_id)
        .all()
    )
    return {r.talent_id: r.panel_score for r in rows}


def build_semantic_lookup(db: Session, req: Requirement) -> dict[str, float]:
    """Layer-3 semantic relevance (0-100) per talent via stored embeddings.

    Best-effort and strictly optional: returns {} when embeddings or the
    OpenAI key are unavailable (tests, offline demos). Never raises.
    """
    try:
        from ..embeddings import embed_text

        req_text = " ".join(
            str(x)
            for x in (
                req.required_primary_role,
                req.production_type,
                getattr(req, "venue_type", None),
                " ".join(req.mandatory_skills or []),
                " ".join(req.preferred_skills or []),
                getattr(req, "special_instructions", None),
            )
            if x
        )
        qvec = embed_text(req_text)
    except Exception:
        return {}

    import math

    qnorm = math.sqrt(sum(v * v for v in qvec)) or 1.0
    lookup: dict[str, float] = {}
    for talent in db.query(Talent).filter(Talent.embedding.isnot(None)).all():
        vec = talent.embedding or []
        if len(vec) != len(qvec):
            continue
        dot = sum(a * b for a, b in zip(qvec, vec))
        tnorm = math.sqrt(sum(v * v for v in vec)) or 1.0
        cosine = dot / (qnorm * tnorm)
        lookup[talent.talent_id] = round(max(0.0, min(1.0, (cosine + 1) / 2)) * 100.0, 2)
    return lookup


def run_match(
    db: Session,
    requirement_id: str,
    *,
    top_k: int = 5,
    scenario_label: str = "baseline",
    params_override: dict[str, Any] | None = None,
    ranking_mode: str = "rules_only",
) -> MatchRun:
    req = db.get(Requirement, requirement_id)
    if not req:
        raise ValueError(f"Requirement {requirement_id} not found")

    if ranking_mode not in ("rules_only", "hybrid", "advisory"):
        raise ValueError(f"Unsupported ranking_mode: {ranking_mode}")

    overrides = params_override or {}
    effective = apply_requirement_overrides(req, overrides)

    run_weights = {
        "ranking_mode": ranking_mode,
        "scoring_weights": WEIGHTS,
        "hybrid": {
            "rule_weight": RULE_WEIGHT,
            "feedback_weight": FEEDBACK_WEIGHT,
        },
    }

    run = MatchRun(
        id=_next_match_id(db),
        requirement_id=requirement_id,
        created_at=datetime.utcnow(),
        weights=run_weights,
        scenario_label=scenario_label,
        params_override=overrides,
    )
    db.add(run)
    db.flush()

    db.add(
        AuditEvent(
            run_id=run.id,
            talent_id=None,
            event_type="match_started",
            message=f"Match started for {requirement_id} ({scenario_label})",
            detail={"overrides": overrides, "top_k": top_k, "ranking_mode": ranking_mode},
        )
    )

    availability_lookup = build_availability_lookup(db, effective)  # type: ignore[arg-type]
    audition_lookup = build_audition_lookup(db, requirement_id)

    talents = db.query(Talent).all()
    scored: list[dict[str, Any]] = []

    semantic_lookup = build_semantic_lookup(db, effective)  # type: ignore[arg-type]

    for talent in talents:
        aud = audition_lookup.get(talent.talent_id)
        result = compute_score(
            effective,  # type: ignore[arg-type]
            talent,
            availability_lookup=availability_lookup,
            audition_score=aud,
        )
        prior = feedback_prior(db, talent, req)
        breakdown = dict(result["breakdown"] or {})
        breakdown["feedback_prior"] = prior
        breakdown["ranking_mode"] = ranking_mode
        rule_score = float(result["score"] or 0.0)
        hybrid = hybrid_sort_score(rule_score, prior)
        breakdown["hybrid_score"] = hybrid

        # --- F01/F02 pilot layers (additive, advisory; parity untouched) ---
        raw_gate = result.pop("gate_result", None)
        if raw_gate is not None:
            report = gate_graph(effective, raw_gate)  # type: ignore[arg-type]
            breakdown["gate_graph"] = report
            breakdown["near_miss"] = near_miss_gaps(raw_gate, report)
        layers = four_layer_score(
            effective,  # type: ignore[arg-type]
            talent,
            result,
            feedback_prior_value=prior,
            semantic_score=semantic_lookup.get(talent.talent_id),
            audition_score=aud,
        )
        breakdown["layers"] = layers

        result["breakdown"] = breakdown
        if ranking_mode == "hybrid":
            result["sort_score"] = hybrid
        elif ranking_mode == "advisory":
            result["sort_score"] = layers["advisory_score"] if layers["advisory_score"] is not None else rule_score
        else:
            result["sort_score"] = rule_score
        scored.append({"talent": talent, **result})

        if result["eligible"]:
            db.add(
                AuditEvent(
                    run_id=run.id,
                    talent_id=talent.talent_id,
                    event_type="eligible",
                    message=f"{talent.talent_id} eligible with score {result['score']} ({result['match_category']})",
                    detail={"score": result["score"], "breakdown": result["breakdown"]},
                )
            )
        else:
            db.add(
                AuditEvent(
                    run_id=run.id,
                    talent_id=talent.talent_id,
                    event_type="rejected",
                    message=f"{talent.talent_id} rejected: {'; '.join(result['rejection_reasons'])}",
                    detail={
                        "failed_gates": result["failed_gates"],
                        "rejection_reasons": result["rejection_reasons"],
                    },
                )
            )

    # Only eligible + score >= 70 are "recommended", ranked, max top_k -- matches
    # the dataset's own recommendation rule exactly. Hybrid only reorders this pool.
    recommendable = [s for s in scored if s["eligible"] and (s["score"] or 0) >= 70]
    recommendable.sort(key=lambda x: (-(x["sort_score"] or 0), x["talent"].talent_id))
    recommendable_ids = {id(s) for s in recommendable}
    other_eligible = [s for s in scored if s["eligible"] and id(s) not in recommendable_ids]
    other_eligible.sort(key=lambda x: (-(x["sort_score"] or 0), x["talent"].talent_id))
    rejected = [s for s in scored if not s["eligible"]]
    rejected.sort(key=lambda x: x["talent"].talent_id)

    for idx, item in enumerate(recommendable, start=1):
        rank = idx if idx <= top_k else None
        db.add(_make_result(run.id, item, rank=rank))
    for item in other_eligible:
        db.add(_make_result(run.id, item, rank=None))
    for item in rejected:
        db.add(_make_result(run.id, item, rank=None))

    shortlist_ids = [e["talent"].talent_id for e in recommendable[:top_k]]
    db.add(
        AuditEvent(
            run_id=run.id,
            talent_id=None,
            event_type="match_completed",
            message=f"Shortlist: {', '.join(shortlist_ids) or '(none)'}",
            detail={
                "shortlist": shortlist_ids,
                "eligible_count": len(recommendable) + len(other_eligible),
                "recommended_count": len(recommendable),
                "rejected_count": len(rejected),
                "ranking_mode": ranking_mode,
            },
        )
    )
    db.commit()
    db.refresh(run)
    return run


def score_talent_against_requirement(
    db: Session,
    requirement_id: str,
    talent_id: str,
) -> dict[str, Any]:
    """Score a single talent against a requirement (no full pool scan)."""
    req = db.get(Requirement, requirement_id)
    if not req:
        raise ValueError(f"Requirement {requirement_id} not found")
    talent = db.get(Talent, talent_id)
    if not talent:
        raise ValueError(f"Talent {talent_id} not found")

    availability_lookup = build_availability_lookup(db, req)
    audition_lookup = build_audition_lookup(db, requirement_id)
    aud = audition_lookup.get(talent.talent_id)
    result = compute_score(
        req,
        talent,
        availability_lookup=availability_lookup,
        audition_score=aud,
    )

    raw_gate = result.pop("gate_result", None)
    gate_report = gate_graph(req, raw_gate) if raw_gate is not None else []
    near_miss = near_miss_gaps(raw_gate, gate_report) if raw_gate is not None else None
    prior = feedback_prior(db, talent, req)
    layers = four_layer_score(
        req,
        talent,
        result,
        feedback_prior_value=prior,
        audition_score=aud,
    )

    return {
        "talent_id": talent_id,
        "requirement_id": requirement_id,
        "eligible": result["eligible"],
        "score": result["score"],
        "match_category": result["match_category"],
        "failed_gates": result["failed_gates"],
        "positive_reasons": result["positive_match_reasons"],
        "rejection_reasons": result["rejection_reasons"],
        "risk_factors": result["risk_factors"],
        "breakdown": result["breakdown"],
        "distance_km": result["distance_km"],
        "gate_graph": gate_report,
        "near_miss": near_miss,
        "layers": layers,
    }


def _make_result(run_id: str, item: dict[str, Any], *, rank: int | None) -> MatchResult:
    return MatchResult(
        run_id=run_id,
        talent_id=item["talent"].talent_id,
        eligible=item["eligible"],
        rank=rank,
        score=item["score"],
        match_category=item["match_category"],
        breakdown=item["breakdown"],
        failed_gates=item["failed_gates"],
        positive_reasons=item["positive_match_reasons"],
        risk_factors=item["risk_factors"],
        rejection_reasons=item["rejection_reasons"],
        distance_km=item["distance_km"],
    )


def serialize_run(db: Session, run: MatchRun, top_k: int = 5) -> dict[str, Any]:
    from ..schemas import MatchResultOut, MatchRunOut, TalentOut

    results = db.query(MatchResult).filter(MatchResult.run_id == run.id).all()
    talent_map = {t.talent_id: t for t in db.query(Talent).all()}

    shortlist = []
    other_eligible = []
    rejected = []
    for r in results:
        talent = talent_map.get(r.talent_id)
        out = MatchResultOut(
            talent_id=r.talent_id,
            talent=TalentOut.model_validate(talent) if talent else None,
            eligible=r.eligible,
            rank=r.rank,
            score=r.score,
            match_category=r.match_category,
            breakdown=r.breakdown or {},
            failed_gates=r.failed_gates or [],
            positive_reasons=r.positive_reasons or [],
            risk_factors=r.risk_factors or [],
            rejection_reasons=r.rejection_reasons or [],
            distance_km=r.distance_km,
        )
        if r.eligible:
            if r.rank is not None and r.rank <= top_k:
                shortlist.append(out)
            else:
                other_eligible.append(out)
        else:
            rejected.append(out)

    shortlist.sort(key=lambda x: x.rank or 999)
    return MatchRunOut(
        id=run.id,
        requirement_id=run.requirement_id,
        created_at=run.created_at,
        scenario_label=run.scenario_label,
        params_override=run.params_override or {},
        shortlist=shortlist,
        other_eligible=other_eligible,
        rejected=rejected,
        eligible_count=len(shortlist) + len(other_eligible),
        rejected_count=len(rejected),
    )
