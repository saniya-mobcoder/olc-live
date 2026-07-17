"""Marketing draft generation (draft-only, no publish)."""
from __future__ import annotations

from datetime import datetime

import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..config import get_settings
from ..database import get_db
from ..embeddings import OpenAIConfigError, require_api_key
from ..engine.matcher import serialize_run
from ..models import Booking, MarketingDraft, MatchRun, Requirement, Talent
from ..schemas import MarketingDraftOut, MarketingDraftRequest

router = APIRouter(prefix="/marketing", tags=["marketing"])
settings = get_settings()


def _next_draft_id(db: Session) -> str:
    count = db.query(MarketingDraft).count() + 1
    return f"MKT-{count:06d}"


def _facts_from_booking(db: Session, booking: Booking) -> dict:
    req = db.get(Requirement, booking.requirement_id)
    talent = db.get(Talent, booking.talent_id)
    return {
        "production_title": req.production_title if req else "",
        "role": req.required_primary_role if req else "",
        "city": req.city if req else "",
        "country": req.country if req else "",
        "talent_name": talent.full_name if talent else booking.talent_id,
        "talent_id": booking.talent_id,
        "weekly_rate_usd": booking.weekly_rate_usd,
        "start_date": booking.start_date.isoformat(),
        "end_date": booking.end_date.isoformat(),
        "source": booking.id,
    }


def _facts_from_match(db: Session, run: MatchRun) -> dict:
    req = db.get(Requirement, run.requirement_id)
    data = serialize_run(db, run)
    top = data.shortlist[0] if data.shortlist else None
    return {
        "production_title": req.production_title if req else "",
        "role": req.required_primary_role if req else "",
        "city": req.city if req else "",
        "country": req.country if req else "",
        "talent_name": top.talent.full_name if top and top.talent else (top.talent_id if top else ""),
        "talent_id": top.talent_id if top else "",
        "score": top.score if top else None,
        "source": run.id,
    }


def _offline_draft(channel: str, facts: dict) -> str:
    title = facts.get("production_title") or "our upcoming production"
    role = facts.get("role") or "performer"
    city = facts.get("city") or "the venue city"
    name = facts.get("talent_name") or "our shortlisted talent"
    if channel == "newsletter":
        return (
            f"Casting update — {title}\n\n"
            f"We are advancing {name} for the {role} role in {city}. "
            f"Dates: {facts.get('start_date', 'TBC')} → {facts.get('end_date', 'TBC')}. "
            f"OLC matching kept hard eligibility gates first, then ranked fit.\n\n"
            f"— OLC Talent Matching"
        )
    return (
        f"Excited to move forward on {title} in {city}. "
        f"Our OLC shortlist highlighted {name} for {role} — "
        f"explainable gates + score, not a black box. "
        f"#LiveProduction #Casting #OLC"
    )


def _llm_draft(channel: str, facts: dict) -> str:
    api_key = require_api_key()
    style = (
        "Write a short LinkedIn post (under 120 words)."
        if channel == "linkedin"
        else "Write a short newsletter blurb (under 150 words)."
    )
    resp = httpx.post(
        "https://api.openai.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {api_key}"},
        json={
            "model": settings.openai_chat_model,
            "temperature": 0.4,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You draft marketing copy for OLC live-production casting. "
                        "Use only provided facts. No false claims. Draft only."
                    ),
                },
                {
                    "role": "user",
                    "content": f"{style}\n\nFACTS:\n{facts}",
                },
            ],
        },
        timeout=60.0,
    )
    if resp.status_code >= 400:
        raise RuntimeError(f"OpenAI draft failed: {resp.status_code}")
    return resp.json()["choices"][0]["message"]["content"].strip()


@router.post("/draft", response_model=MarketingDraftOut)
def create_draft(body: MarketingDraftRequest, db: Session = Depends(get_db)):
    channel = (body.channel or "").strip().lower()
    if channel not in ("linkedin", "newsletter"):
        raise HTTPException(status_code=400, detail="channel must be linkedin or newsletter")

    if body.booking_id:
        booking = db.get(Booking, body.booking_id)
        if not booking:
            raise HTTPException(status_code=404, detail="Booking not found")
        facts = _facts_from_booking(db, booking)
        source_ref = booking.id
    elif body.match_run_id:
        run = db.get(MatchRun, body.match_run_id)
        if not run:
            raise HTTPException(status_code=404, detail="Match run not found")
        facts = _facts_from_match(db, run)
        source_ref = run.id
    else:
        raise HTTPException(status_code=400, detail="booking_id or match_run_id required")

    try:
        text = _llm_draft(channel, facts)
    except (OpenAIConfigError, Exception):
        text = _offline_draft(channel, facts)

    row = MarketingDraft(
        id=_next_draft_id(db),
        channel=channel,
        body=text,
        source_ref=source_ref,
        created_at=datetime.utcnow(),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return MarketingDraftOut.model_validate(row)


@router.get("/drafts", response_model=list[MarketingDraftOut])
def list_drafts(db: Session = Depends(get_db), limit: int = 50):
    rows = (
        db.query(MarketingDraft)
        .order_by(MarketingDraft.created_at.desc())
        .limit(limit)
        .all()
    )
    return [MarketingDraftOut.model_validate(r) for r in rows]
