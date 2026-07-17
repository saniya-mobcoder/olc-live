from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..engine.matcher import run_match, serialize_run
from ..models import AuditEvent, MatchDecision, MatchRun, Talent
from ..schemas import (
    MatchDecisionOut,
    MatchDecisionRequest,
    MatchRequest,
    MatchRunOut,
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
    return serialize_run(db, run, top_k=body.top_k)


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
