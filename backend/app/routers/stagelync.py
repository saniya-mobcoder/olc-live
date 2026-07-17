"""StageLync mirror sync, import into OLC talent pool, and discovery."""
from __future__ import annotations

import json
import re
from datetime import date, datetime, timedelta
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..embeddings import OpenAIConfigError, cosine_similarity, embed_text, embed_texts
from ..models import StageLyncLink, StageLyncPerson, Talent
from ..schemas import (
    StageLyncImportOut,
    StageLyncPersonOut,
    StageLyncSyncOut,
    TalentOut,
)

router = APIRouter(prefix="/stagelync", tags=["stagelync"])
DATA_DIR = Path(__file__).resolve().parents[3] / "data"
FIXTURE = DATA_DIR / "stagelync_people.json"


def _person_document(person: StageLyncPerson) -> str:
    return " ".join(
        p
        for p in [
            person.display_name,
            person.primary_role,
            " ".join(person.secondary_roles or []),
            " ".join(person.skills or []),
            " ".join(person.languages or []),
            person.city,
            person.country,
            person.profile_summary or "",
            "aerial" if person.aerial else "",
            "aquatic" if person.aquatic else "",
            "stunt" if person.stunt else "",
            person.physical_skill_level,
        ]
        if p
    )


def _link_map(db: Session) -> dict[str, StageLyncLink]:
    return {link.stagelync_person_id: link for link in db.query(StageLyncLink).all()}


def _serialize_person(
    person: StageLyncPerson, link: StageLyncLink | None
) -> StageLyncPersonOut:
    status = "mirrored"
    talent_id = None
    if link:
        talent_id = link.talent_id
        status = link.status
    return StageLyncPersonOut(
        stagelync_person_id=person.stagelync_person_id,
        display_name=person.display_name,
        primary_role=person.primary_role,
        secondary_roles=person.secondary_roles or [],
        skills=person.skills or [],
        city=person.city,
        country=person.country,
        latitude=person.latitude,
        longitude=person.longitude,
        languages=person.languages or [],
        weekly_rate_usd=person.weekly_rate_usd,
        experience_years=person.experience_years,
        physical_skill_level=person.physical_skill_level,
        aquatic=person.aquatic,
        aerial=person.aerial,
        stunt=person.stunt,
        certifications=person.certifications or [],
        work_authorizations=person.work_authorizations or [],
        profile_summary=person.profile_summary or "",
        synced_at=person.synced_at,
        link_status=status,
        talent_id=talent_id,
    )


def _next_sl_talent_id(db: Session) -> str:
    existing = {
        t.talent_id
        for t in db.query(Talent.talent_id)
        .filter(Talent.talent_id.like("TAL-SL-%"))
        .all()
    }
    n = 1
    while f"TAL-SL-{n:04d}" in existing:
        n += 1
    return f"TAL-SL-{n:04d}"


@router.post("/sync", response_model=StageLyncSyncOut)
def sync_stagelync(db: Session = Depends(get_db)):
    if not FIXTURE.exists():
        raise HTTPException(status_code=404, detail="StageLync fixture not found")
    with open(FIXTURE, encoding="utf-8") as f:
        rows = json.load(f)

    now = datetime.utcnow()
    synced = 0
    for row in rows:
        pid = row["stagelync_person_id"]
        person = db.get(StageLyncPerson, pid)
        if not person:
            person = StageLyncPerson(stagelync_person_id=pid)
            db.add(person)
            synced += 1
        person.display_name = row["display_name"]
        person.primary_role = row["primary_role"]
        person.secondary_roles = row.get("secondary_roles", [])
        person.skills = row.get("skills", [])
        person.city = row["city"]
        person.country = row["country"]
        person.latitude = float(row.get("latitude", 0))
        person.longitude = float(row.get("longitude", 0))
        person.languages = row.get("languages", [])
        person.weekly_rate_usd = float(row.get("weekly_rate_usd", 0))
        person.experience_years = float(row.get("experience_years", 0))
        person.physical_skill_level = row.get("physical_skill_level", "Standard")
        person.aquatic = bool(row.get("aquatic", False))
        person.aerial = bool(row.get("aerial", False))
        person.stunt = bool(row.get("stunt", False))
        person.certifications = row.get("certifications", [])
        person.work_authorizations = row.get("work_authorizations", [])
        person.profile_summary = row.get("profile_summary", "")
        person.synced_at = now

        link = (
            db.query(StageLyncLink)
            .filter(StageLyncLink.stagelync_person_id == pid)
            .first()
        )
        if not link:
            db.add(
                StageLyncLink(
                    stagelync_person_id=pid,
                    talent_id=None,
                    status="mirrored",
                )
            )

    db.flush()
    people = db.query(StageLyncPerson).all()
    missing = [p for p in people if not p.embedding]
    if missing:
        try:
            vectors = embed_texts([_person_document(p) for p in missing])
            for person, vec in zip(missing, vectors):
                person.embedding = vec
        except OpenAIConfigError:
            # Keyword discovery still works without embeddings
            pass
        except Exception:
            pass

    db.commit()
    return StageLyncSyncOut(
        synced=synced,
        total=len(rows),
        message=f"Synced {len(rows)} StageLync people ({synced} new).",
    )


@router.get("/people", response_model=list[StageLyncPersonOut])
def list_people(
    db: Session = Depends(get_db),
    role: str | None = None,
    country: str | None = None,
    status: str | None = None,
):
    links = _link_map(db)
    people = db.query(StageLyncPerson).order_by(StageLyncPerson.stagelync_person_id).all()
    out: list[StageLyncPersonOut] = []
    for person in people:
        link = links.get(person.stagelync_person_id)
        item = _serialize_person(person, link)
        if role and person.primary_role.lower() != role.lower():
            continue
        if country and person.country.lower() != country.lower():
            continue
        if status and item.link_status != status:
            continue
        out.append(item)
    return out


@router.post("/import/{stagelync_person_id}", response_model=StageLyncImportOut)
def import_person(stagelync_person_id: str, db: Session = Depends(get_db)):
    person = db.get(StageLyncPerson, stagelync_person_id)
    if not person:
        raise HTTPException(status_code=404, detail="StageLync person not found")

    link = (
        db.query(StageLyncLink)
        .filter(StageLyncLink.stagelync_person_id == stagelync_person_id)
        .first()
    )
    created = False
    if link and link.talent_id:
        talent = db.get(Talent, link.talent_id)
        if not talent:
            talent = None
    else:
        talent = None

    if talent is None:
        talent_id = _next_sl_talent_id(db)
        talent = Talent(
            talent_id=talent_id,
            full_name=person.display_name,
            profile_title=f"StageLync {person.primary_role}",
            talent_category="Performer",
            primary_role=person.primary_role,
            secondary_roles=person.secondary_roles or [],
            primary_skills=person.skills or [],
            secondary_skills=[],
            experience_years=person.experience_years,
            city=person.city,
            country=person.country,
            latitude=person.latitude,
            longitude=person.longitude,
            home_market_region=person.country,
            travel_ready=True,
            relocation_available=True,
            passport_valid_until=date.today() + timedelta(days=365 * 3),
            work_authorized_countries=person.work_authorizations or [],
            weekly_contract_rate_usd=person.weekly_rate_usd,
            rehearsal_day_rate_usd=round(person.weekly_rate_usd / 7, 2),
            performance_fee_usd=round(person.weekly_rate_usd / 5, 2),
            buyout_rate_usd=person.weekly_rate_usd * 2,
            languages=person.languages or [],
            showreel_quality_score=80.0,
            audition_readiness_score=82.0,
            physical_skill_level=person.physical_skill_level,
            aquatic_performance_experience=person.aquatic,
            aerial_performance_experience=person.aerial,
            stunt_experience=person.stunt,
            medical_clearance_status="Cleared",
            safety_training_level="Intermediate",
            professional_certifications=person.certifications or [],
            portfolio_quality_score=78.0,
            average_director_rating=4.2,
            completed_productions=3,
            completed_performances=20,
            rehire_rate=0.5,
            rehearsal_attendance_rate=0.95,
            safety_incident_rate=0.0,
            cancellation_rate=0.0,
            response_time_hours=4.0,
            profile_completion_percentage=90.0,
            identity_verified=True,
            professional_references_verified=True,
            preferred_production_types=[],
            overnight_rehearsal_available=True,
            weekend_available=True,
            last_active_date=date.today(),
            profile_status="Active",
        )
        db.add(talent)
        created = True
    else:
        talent.full_name = person.display_name
        talent.primary_role = person.primary_role
        talent.secondary_roles = person.secondary_roles or []
        talent.primary_skills = person.skills or []
        talent.city = person.city
        talent.country = person.country
        talent.latitude = person.latitude
        talent.longitude = person.longitude
        talent.languages = person.languages or []
        talent.weekly_contract_rate_usd = person.weekly_rate_usd
        talent.physical_skill_level = person.physical_skill_level
        talent.aquatic_performance_experience = person.aquatic
        talent.aerial_performance_experience = person.aerial
        talent.stunt_experience = person.stunt
        talent.professional_certifications = person.certifications or []
        talent.work_authorized_countries = person.work_authorizations or []

    try:
        from ..embeddings import talent_document

        talent.embedding = embed_text(talent_document(talent))
    except Exception:
        pass

    if not link:
        link = StageLyncLink(stagelync_person_id=stagelync_person_id)
        db.add(link)
    link.talent_id = talent.talent_id
    link.status = "imported"
    link.imported_at = datetime.utcnow()
    db.commit()

    return StageLyncImportOut(
        stagelync_person_id=stagelync_person_id,
        talent_id=talent.talent_id,
        status="imported",
        created=created,
    )


@router.get("/discover", response_model=list[StageLyncPersonOut])
def discover(
    q: str = Query("", min_length=0),
    limit: int = 20,
    db: Session = Depends(get_db),
):
    people = db.query(StageLyncPerson).all()
    links = _link_map(db)
    if not q.strip():
        return [
            _serialize_person(p, links.get(p.stagelync_person_id))
            for p in people[:limit]
        ]

    query = q.lower()
    scored: list[tuple[float, StageLyncPerson]] = []

    query_vec = None
    try:
        query_vec = embed_text(q)
    except Exception:
        query_vec = None

    for person in people:
        score = 0.0
        blob = _person_document(person).lower()
        for word in re.findall(r"[a-zA-Z]+", query):
            if len(word) > 2 and word in blob:
                score += 1.0
        if person.primary_role.lower() in query:
            score += 5.0
        if person.country.lower() in query:
            score += 3.0
        if "elite" in query and person.physical_skill_level == "Elite":
            score += 2.0
        if "aerial" in query and person.aerial:
            score += 3.0
        if "aquatic" in query and person.aquatic:
            score += 3.0
        if query_vec and person.embedding:
            score += cosine_similarity(query_vec, person.embedding) * 10.0
        if score > 0:
            scored.append((score, person))

    scored.sort(key=lambda x: (-x[0], x[1].stagelync_person_id))
    return [
        _serialize_person(p, links.get(p.stagelync_person_id))
        for _, p in scored[:limit]
    ]


@router.get("/imported-talents", response_model=list[TalentOut])
def imported_talents(db: Session = Depends(get_db)):
    links = (
        db.query(StageLyncLink)
        .filter(StageLyncLink.talent_id.isnot(None), StageLyncLink.status == "imported")
        .all()
    )
    talents = []
    for link in links:
        talent = db.get(Talent, link.talent_id)
        if talent:
            talents.append(TalentOut.model_validate(talent))
    return talents
