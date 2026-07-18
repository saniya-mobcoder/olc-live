from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..ai.explain import explain_match
from ..ai.predictors import predict_signals
from ..ai.rerank import ml_rerank
from ..database import get_db
from ..engine.matcher import run_match, serialize_run
from ..models import AuditEvent, MatchDecision, MatchResult, MatchRun, Talent
from ..schemas import (
    ExplainOut,
    ExplainRequest,
    MatchDecisionOut,
    MatchDecisionRequest,
    MatchRequest,
    MatchRunOut,
    PredictSignalsOut,
)

router = APIRouter(prefix="/matches", tags=["matches"])

_ALLOWED_DECISIONS = {"hire", "hold", "reject"}


@router.post("", response_model=MatchRunOut)
def create_match(body: MatchRequest, db: Session = Depends(get_db)):
    try:
        run = run_match(
            db,
            body.requirement_id,
            top_k=body.top_k,
            scenario_label=body.scenario_label,
            params_override=body.params_override,
            ranking_mode=body.ranking_mode,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    out = serialize_run(db, run, top_k=body.top_k)

    if body.ranking_mode == "hybrid" or body.include_ml_signals:
        rows = [
            {
                "talent_id": r.talent_id,
                "eligible": r.eligible,
                "score": r.score,
                "talent": r.talent.model_dump() if r.talent else {},
            }
            for r in out.shortlist
        ]
        reranked = ml_rerank(rows)
        advice = {r["talent_id"]: r for r in reranked if r.get("eligible")}
        for row in out.shortlist:
            tip = advice.get(row.talent_id)
            if tip and row.talent:
                sig = predict_signals(row.talent)
                row.breakdown = {
                    **(row.breakdown or {}),
                    "advisory_score": tip.get("advisory_score"),
                    "booking_success_prior": tip.get("booking_success_prior"),
                    "rerank_reason": tip.get("rerank_reason"),
                    "ml_signals": sig,
                }
    return out


@router.get("/{run_id}", response_model=MatchRunOut)
def get_match(run_id: str, db: Session = Depends(get_db)):
    run = db.get(MatchRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Match run not found")
    return serialize_run(db, run)


@router.get("", response_model=list[MatchRunOut])
def list_matches(db: Session = Depends(get_db), limit: int = 20):
    runs = (
        db.query(MatchRun)
        .order_by(MatchRun.created_at.desc())
        .limit(limit)
        .all()
    )
    return [serialize_run(db, r) for r in runs]


@router.post("/explain", response_model=ExplainOut)
def explain_candidate(body: ExplainRequest, db: Session = Depends(get_db)):
    """F11 grounded explanation for one match result row."""
    run = db.get(MatchRun, body.match_run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Match run not found")

    row = (
        db.query(MatchResult)
        .filter(
            MatchResult.run_id == body.match_run_id,
            MatchResult.talent_id == body.talent_id,
        )
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Match result not found")

    talent = db.get(Talent, body.talent_id)
    facts = {
        "talent_id": row.talent_id,
        "name": talent.full_name if talent else body.talent_id,
        "eligible": row.eligible,
        "score": row.score,
        "match_category": row.match_category,
        "failed_gates": row.failed_gates or [],
        "positive_reasons": row.positive_reasons or [],
        "risk_factors": row.risk_factors or [],
        "rejection_reasons": row.rejection_reasons or [],
        "rank": row.rank,
    }
    result = explain_match(facts)
    db.add(
        AuditEvent(
            run_id=body.match_run_id,
            talent_id=body.talent_id,
            event_type="ai_explanation",
            message=result["explanation"][:500],
            detail={
                "provider": result.get("provider"),
                "model": result.get("model"),
                "cost_usd": result.get("cost_usd"),
                "grounded": result.get("grounded"),
                "used_llm": result.get("used_llm"),
                "tokens_in": result.get("tokens_in"),
                "tokens_out": result.get("tokens_out"),
                "latency_ms": result.get("latency_ms"),
            },
        )
    )
    db.commit()
    return ExplainOut(
        talent_id=body.talent_id,
        match_run_id=body.match_run_id,
        explanation=result["explanation"],
        provider=result.get("provider"),
        model=result.get("model"),
        cost_usd=result.get("cost_usd"),
        grounded=result.get("grounded", True),
        used_llm=result.get("used_llm", False),
    )


@router.get("/{run_id}/signals/{talent_id}", response_model=PredictSignalsOut)
def talent_signals(run_id: str, talent_id: str, db: Session = Depends(get_db)):
    run = db.get(MatchRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Match run not found")
    talent = db.get(Talent, talent_id)
    if not talent:
        raise HTTPException(status_code=404, detail="Talent not found")
    sig = predict_signals(talent)
    return PredictSignalsOut(talent_id=talent_id, match_run_id=run_id, **sig)


@router.post("/{run_id}/decisions", response_model=MatchDecisionOut)
def create_decision(
    run_id: str, body: MatchDecisionRequest, db: Session = Depends(get_db)
):
    run = db.get(MatchRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Match run not found")

    decision = body.decision.strip().lower()
    if decision not in _ALLOWED_DECISIONS:
        raise HTTPException(
            status_code=400,
            detail=f"decision must be one of: {', '.join(sorted(_ALLOWED_DECISIONS))}",
        )

    talent = db.get(Talent, body.talent_id)
    if not talent:
        raise HTTPException(status_code=404, detail="Talent not found")

    row = MatchDecision(
        run_id=run_id,
        talent_id=body.talent_id,
        decision=decision,
        reason=body.reason or "",
        created_at=datetime.utcnow(),
    )
    db.add(row)
    db.add(
        AuditEvent(
            run_id=run_id,
            talent_id=body.talent_id,
            event_type="decision_recorded",
            message=f"{body.talent_id} marked {decision}",
            detail={"decision": decision, "reason": body.reason or ""},
        )
    )
    db.commit()
    db.refresh(row)
    return MatchDecisionOut.model_validate(row)


@router.get("/{run_id}/decisions", response_model=list[MatchDecisionOut])
def list_decisions(run_id: str, db: Session = Depends(get_db)):
    run = db.get(MatchRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Match run not found")
    rows = (
        db.query(MatchDecision)
        .filter(MatchDecision.run_id == run_id)
        .order_by(MatchDecision.created_at.desc())
        .all()
    )
    return [MatchDecisionOut.model_validate(r) for r in rows]
