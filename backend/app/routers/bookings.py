"""Bookings from hire decisions + schedule listing."""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import (
    AuditEvent,
    Booking,
    MatchDecision,
    MatchRun,
    Requirement,
    Talent,
)
from ..schemas import BookingCreateRequest, BookingOut

router = APIRouter(prefix="/bookings", tags=["bookings"])


def _next_booking_id(db: Session) -> str:
    count = db.query(Booking).count() + 1
    return f"BKG-{count:06d}"


def _to_out(db: Session, row: Booking) -> BookingOut:
    req = db.get(Requirement, row.requirement_id)
    talent = db.get(Talent, row.talent_id)
    return BookingOut(
        id=row.id,
        requirement_id=row.requirement_id,
        talent_id=row.talent_id,
        match_run_id=row.match_run_id,
        decision_id=row.decision_id,
        status=row.status,
        weekly_rate_usd=row.weekly_rate_usd,
        start_date=row.start_date,
        end_date=row.end_date,
        created_at=row.created_at,
        production_title=req.production_title if req else None,
        talent_name=talent.full_name if talent else None,
    )


@router.post("", response_model=BookingOut)
def create_booking(body: BookingCreateRequest, db: Session = Depends(get_db)):
    run = db.get(MatchRun, body.run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Match run not found")

    talent = db.get(Talent, body.talent_id)
    if not talent:
        raise HTTPException(status_code=404, detail="Talent not found")

    decision = (
        db.query(MatchDecision)
        .filter(
            MatchDecision.run_id == body.run_id,
            MatchDecision.talent_id == body.talent_id,
            MatchDecision.decision == "hire",
        )
        .order_by(MatchDecision.created_at.desc())
        .first()
    )
    if not decision:
        raise HTTPException(
            status_code=400,
            detail="Record a hire decision on this talent before creating a booking",
        )

    existing = (
        db.query(Booking)
        .filter(
            Booking.match_run_id == body.run_id,
            Booking.talent_id == body.talent_id,
            Booking.status == "confirmed",
        )
        .first()
    )
    if existing:
        return _to_out(db, existing)

    req = db.get(Requirement, run.requirement_id)
    if not req:
        raise HTTPException(status_code=404, detail="Requirement not found")

    row = Booking(
        id=_next_booking_id(db),
        requirement_id=run.requirement_id,
        talent_id=body.talent_id,
        match_run_id=body.run_id,
        decision_id=decision.id,
        status="confirmed",
        weekly_rate_usd=float(talent.weekly_contract_rate_usd or 0),
        start_date=req.rehearsal_start_date,
        end_date=req.performance_end_date,
        created_at=datetime.utcnow(),
    )
    db.add(row)
    db.add(
        AuditEvent(
            run_id=body.run_id,
            talent_id=body.talent_id,
            event_type="booking_created",
            message=f"Booking {row.id} created for {body.talent_id}",
            detail={"booking_id": row.id},
        )
    )
    db.commit()
    db.refresh(row)
    return _to_out(db, row)


@router.get("", response_model=list[BookingOut])
def list_bookings(db: Session = Depends(get_db), limit: int = 100):
    rows = (
        db.query(Booking)
        .order_by(Booking.created_at.desc())
        .limit(limit)
        .all()
    )
    return [_to_out(db, r) for r in rows]


@router.get("/schedule", response_model=list[BookingOut])
def schedule(
    requirement_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    q = db.query(Booking).filter(Booking.status == "confirmed")
    if requirement_id:
        q = q.filter(Booking.requirement_id == requirement_id)
    rows = q.order_by(Booking.start_date, Booking.id).all()
    return [_to_out(db, r) for r in rows]
