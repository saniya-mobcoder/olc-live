"""Audit trail endpoints (F19)."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import AuditEvent, MatchRun
from ..schemas import AuditEventOut

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("/{run_id}", response_model=list[AuditEventOut])
def get_audit(run_id: str, db: Session = Depends(get_db)):
    run = db.get(MatchRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Match run not found")
    events = (
        db.query(AuditEvent)
        .filter(AuditEvent.run_id == run_id)
        .order_by(AuditEvent.id)
        .all()
    )
    return events
