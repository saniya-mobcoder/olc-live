"""Job ingestion: parse casting briefs → validate/dedupe → confirm Requirement."""
from __future__ import annotations

import json
import re
from datetime import date, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..ai.providers import AIConfigError, TaskTier, chat
from ..database import get_db
from ..embeddings import OpenAIConfigError, cosine_similarity, embed_text
from ..models import Requirement
from ..schemas import (
    JobConfirmRequest,
    JobDedupeOut,
    JobDedupeRequest,
    JobParseOut,
    JobParseRequest,
    RequirementOut,
)

router = APIRouter(prefix="/jobs", tags=["jobs"])

_CITY_COORDS: dict[str, tuple[float, float, str]] = {
    "dubai": (25.2048, 55.2708, "UAE"),
    "abu dhabi": (24.4539, 54.3773, "UAE"),
    "london": (51.5074, -0.1278, "UK"),
    "paris": (48.8566, 2.3522, "France"),
    "new york": (40.7128, -74.006, "USA"),
    "los angeles": (34.0522, -118.2437, "USA"),
    "singapore": (1.3521, 103.8198, "Singapore"),
    "hong kong": (22.3193, 114.1694, "Hong Kong"),
}

_REQUIRED_CONFIRM = (
    "required_primary_role",
    "required_category",
    "country",
    "rehearsal_start_date",
    "performance_end_date",
    "weekly_budget_max_usd",
)


def _next_requirement_id(db: Session) -> str:
    rows = db.query(Requirement.requirement_id).all()
    max_n = 0
    for (rid,) in rows:
        m = re.match(r"REQ-(\d+)$", rid or "")
        if m:
            max_n = max(max_n, int(m.group(1)))
    return f"REQ-{max_n + 1:04d}"


def _parse_date(value: Any) -> date | None:
    if value is None or value == "":
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    s = str(value).strip()[:10]
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        return None


def _offline_parse(brief: str) -> dict[str, Any]:
    text = brief.strip()
    lower = text.lower()
    fields: dict[str, Any] = {
        "production_title": "Ingested casting brief",
        "production_type": "Spectacle",
        "required_category": "Performer",
        "required_primary_role": "Performer",
        "mandatory_skills": [],
        "preferred_skills": [],
        "required_languages": [],
        "city": "",
        "country": "",
        "weekly_budget_min_usd": 0.0,
        "weekly_budget_max_usd": 0.0,
        "special_instructions": text[:2000],
        "aerial_experience_required": "aerial" in lower,
        "aquatic_experience_required": "aquatic" in lower or "diving" in lower,
        "stunt_experience_required": "stunt" in lower,
        "visa_sponsorship_available": "visa" in lower and "sponsor" in lower,
        "overnight_rehearsal_required": "overnight" in lower,
    }

    title_m = re.search(
        r"(?:production|show|title)\s*[:\-]\s*(.+)", text, re.I
    )
    if title_m:
        fields["production_title"] = title_m.group(1).strip().split("\n")[0][:200]
    else:
        first_line = text.split("\n")[0].strip()
        if 8 <= len(first_line) <= 120:
            fields["production_title"] = first_line

    role_m = re.search(
        r"(?:role|looking for|seeking|need(?:s)?)\s*[:\-]?\s*"
        r"(aerial artist|stunt performer|diver|performer|acrobat|dancer|"
        r"singer|technician|stage manager|choreographer|[A-Za-z][A-Za-z ]{2,40})",
        text,
        re.I,
    )
    if role_m:
        fields["required_primary_role"] = role_m.group(1).strip().title()
    elif "aerial" in lower:
        fields["required_primary_role"] = "Aerial Artist"
    elif "stunt" in lower:
        fields["required_primary_role"] = "Stunt Performer"

    for city_key, (lat, lon, country) in _CITY_COORDS.items():
        if city_key in lower:
            fields["city"] = city_key.title()
            fields["country"] = country
            fields["latitude"] = lat
            fields["longitude"] = lon
            break

    budget_m = re.search(
        r"(?:budget|rate|weekly)\s*(?:max|up to|:)?\s*\$?\s*([\d,]+)",
        text,
        re.I,
    )
    if budget_m:
        fields["weekly_budget_max_usd"] = float(budget_m.group(1).replace(",", ""))

    dates = re.findall(r"(20\d{2}-\d{2}-\d{2})", text)
    if len(dates) >= 2:
        fields["rehearsal_start_date"] = dates[0]
        fields["performance_end_date"] = dates[-1]
        fields["performance_start_date"] = dates[1] if len(dates) > 2 else dates[0]
        fields["rehearsal_end_date"] = dates[0]
    elif len(dates) == 1:
        fields["rehearsal_start_date"] = dates[0]
        start = _parse_date(dates[0])
        if start:
            end = start + timedelta(days=30)
            fields["performance_end_date"] = end.isoformat()
            fields["performance_start_date"] = start.isoformat()
            fields["rehearsal_end_date"] = start.isoformat()

    langs = []
    for lang in ["Arabic", "English", "French", "Spanish", "Mandarin", "Hindi"]:
        if lang.lower() in lower:
            langs.append(lang)
    fields["required_languages"] = langs

    skills = []
    for skill in ["Aerial Silks", "Trampoline", "Diving", "Fire", "Wire", "Acrobatics"]:
        if skill.lower() in lower:
            skills.append(skill)
    fields["mandatory_skills"] = skills

    return fields


def _llm_parse(brief: str) -> dict[str, Any]:
    system = (
        "Extract a live-production casting requirement as JSON. "
        "Use only these keys when known: production_title, production_type, "
        "required_category, required_primary_role, acceptable_secondary_roles, "
        "mandatory_skills, preferred_skills, city, country, venue_type, "
        "rehearsal_start_date, rehearsal_end_date, performance_start_date, "
        "performance_end_date, weekly_budget_min_usd, weekly_budget_max_usd, "
        "required_languages, aerial_experience_required, aquatic_experience_required, "
        "stunt_experience_required, visa_sponsorship_available, "
        "overnight_rehearsal_required, medical_clearance_required, "
        "special_instructions. Dates ISO YYYY-MM-DD. "
        "required_category one of Performer, Creative, Technical, Production. "
        "Return JSON only."
    )
    result = chat(
        [
            {"role": "system", "content": system},
            {"role": "user", "content": brief[:6000]},
        ],
        tier=TaskTier.CHEAP_CHAT,
        temperature=0.1,
        max_tokens=900,
        response_format={"type": "json_object"},
    )
    data = json.loads(result.content)
    if not isinstance(data, dict):
        raise RuntimeError("Parse did not return an object")
    return data


def _assess_fields(fields: dict[str, Any]) -> tuple[list[str], list[str]]:
    warnings: list[str] = []
    missing: list[str] = []
    for key in _REQUIRED_CONFIRM:
        val = fields.get(key)
        if val is None or val == "" or val == [] or val == 0 or val == 0.0:
            # budget 0 is missing; skills empty is warning only
            if key == "weekly_budget_max_usd" and val == 0:
                missing.append(key)
            elif key != "weekly_budget_max_usd":
                missing.append(key)

    if not fields.get("mandatory_skills"):
        warnings.append("mandatory_skills is empty — matching may reject many talents")

    r_start = _parse_date(fields.get("rehearsal_start_date"))
    p_end = _parse_date(fields.get("performance_end_date"))
    if r_start and p_end and r_start > p_end:
        warnings.append("rehearsal_start_date is after performance_end_date")

    bmin = float(fields.get("weekly_budget_min_usd") or 0)
    bmax = float(fields.get("weekly_budget_max_usd") or 0)
    if bmax and bmin and bmin > bmax:
        warnings.append("weekly_budget_min_usd exceeds weekly_budget_max_usd")

    return warnings, missing


def _requirement_document(req: Requirement) -> str:
    return " ".join(
        str(p)
        for p in [
            req.production_title,
            req.production_type,
            req.required_category,
            req.required_primary_role,
            " ".join(req.mandatory_skills or []),
            req.city,
            req.country,
            req.special_instructions or "",
        ]
        if p
    )


@router.post("/parse", response_model=JobParseOut)
def parse_job(body: JobParseRequest):
    brief = (body.brief_text or "").strip()
    if len(brief) < 20:
        raise HTTPException(status_code=400, detail="brief_text too short")

    used_llm = False
    try:
        fields = _llm_parse(brief)
        used_llm = True
    except (OpenAIConfigError, AIConfigError, Exception):
        fields = _offline_parse(brief)

    # Enrich city coords if missing
    city = str(fields.get("city") or "").strip().lower()
    if city in _CITY_COORDS and "latitude" not in fields:
        lat, lon, country = _CITY_COORDS[city]
        fields["latitude"] = lat
        fields["longitude"] = lon
        fields.setdefault("country", country)

    fields.setdefault("special_instructions", brief[:2000])
    warnings, missing = _assess_fields(fields)
    if not used_llm:
        warnings.append("Parsed offline (no API key or LLM failed)")

    return JobParseOut(fields=fields, warnings=warnings, missing_fields=missing)


@router.post("/dedupe", response_model=JobDedupeOut)
def dedupe_job(body: JobDedupeRequest, db: Session = Depends(get_db)):
    query = (body.brief_text or body.title or "").strip()
    if not query:
        raise HTTPException(status_code=400, detail="brief_text or title required")

    open_reqs = (
        db.query(Requirement)
        .filter(Requirement.requirement_status.in_(["Open", "open", "Active"]))
        .all()
    )
    if not open_reqs:
        open_reqs = db.query(Requirement).limit(50).all()

    matches: list[dict[str, Any]] = []
    try:
        qvec = embed_text(query[:4000])
        for req in open_reqs:
            doc = _requirement_document(req)
            try:
                rvec = embed_text(doc[:4000])
                sim = cosine_similarity(qvec, rvec)
            except Exception:
                continue
            if sim >= 0.85:
                matches.append(
                    {
                        "requirement_id": req.requirement_id,
                        "production_title": req.production_title,
                        "similarity": round(sim, 4),
                    }
                )
    except OpenAIConfigError:
        # Keyword fallback
        tokens = {t for t in re.findall(r"[a-zA-Z]{4,}", query.lower())}
        for req in open_reqs:
            blob = _requirement_document(req).lower()
            overlap = sum(1 for t in tokens if t in blob)
            score = overlap / max(1, len(tokens))
            if score >= 0.35:
                matches.append(
                    {
                        "requirement_id": req.requirement_id,
                        "production_title": req.production_title,
                        "similarity": round(score, 4),
                    }
                )

    matches.sort(key=lambda m: -m["similarity"])
    return JobDedupeOut(similar=matches[:10])


def _build_requirement(db: Session, fields: dict[str, Any]) -> Requirement:
    warnings, missing = _assess_fields(fields)
    hard_missing = [m for m in missing if m in _REQUIRED_CONFIRM]
    if hard_missing:
        raise HTTPException(
            status_code=400,
            detail=f"Missing required fields: {', '.join(hard_missing)}",
        )

    r_start = _parse_date(fields.get("rehearsal_start_date"))
    p_end = _parse_date(fields.get("performance_end_date"))
    if not r_start or not p_end:
        raise HTTPException(status_code=400, detail="Invalid date fields")
    if r_start > p_end:
        raise HTTPException(
            status_code=400, detail="rehearsal_start_date must be on or before performance_end_date"
        )

    bmin = float(fields.get("weekly_budget_min_usd") or 0)
    bmax = float(fields.get("weekly_budget_max_usd") or 0)
    if bmax <= 0:
        raise HTTPException(status_code=400, detail="weekly_budget_max_usd required")
    if bmin > bmax:
        raise HTTPException(status_code=400, detail="weekly_budget_min_usd exceeds max")

    r_end = _parse_date(fields.get("rehearsal_end_date")) or r_start
    p_start = _parse_date(fields.get("performance_start_date")) or r_start
    tech_start = _parse_date(fields.get("technical_rehearsal_start_date")) or r_end
    tech_end = _parse_date(fields.get("technical_rehearsal_end_date")) or tech_start

    today = date.today()
    city = str(fields.get("city") or "").strip() or "Unknown"
    country = str(fields.get("country") or "").strip()
    lat = float(fields.get("latitude") or 0.0)
    lon = float(fields.get("longitude") or 0.0)
    if city.lower() in _CITY_COORDS:
        lat, lon, ctry = _CITY_COORDS[city.lower()]
        country = country or ctry

    req_id = _next_requirement_id(db)
    prod_id = f"PROD-ING-{req_id.split('-')[1]}"
    title = str(fields.get("production_title") or "Ingested production")[:200]

    return Requirement(
        requirement_id=req_id,
        production_id=prod_id,
        production_title=title,
        production_type=str(fields.get("production_type") or "Spectacle")[:80],
        fictional_client_id=str(fields.get("fictional_client_id") or "CLI-INGEST"),
        required_category=str(fields.get("required_category") or "Performer")[:60],
        required_primary_role=str(fields.get("required_primary_role"))[:80],
        acceptable_secondary_roles=list(fields.get("acceptable_secondary_roles") or []),
        mandatory_skills=list(fields.get("mandatory_skills") or []),
        preferred_skills=list(fields.get("preferred_skills") or []),
        city=city[:120],
        country=country[:80],
        latitude=lat,
        longitude=lon,
        venue_type=str(fields.get("venue_type") or "Arena")[:80],
        rehearsal_start_date=r_start,
        rehearsal_end_date=r_end,
        technical_rehearsal_start_date=tech_start,
        technical_rehearsal_end_date=tech_end,
        performance_start_date=p_start,
        performance_end_date=p_end,
        number_of_performances=int(fields.get("number_of_performances") or 10),
        contract_duration_days=max(1, (p_end - r_start).days + 1),
        talent_required=int(fields.get("talent_required") or 1),
        ensemble_or_solo=str(fields.get("ensemble_or_solo") or "Solo")[:40],
        minimum_experience_years=float(fields.get("minimum_experience_years") or 0),
        minimum_director_rating=float(fields.get("minimum_director_rating") or 0),
        minimum_showreel_score=float(fields.get("minimum_showreel_score") or 0),
        minimum_audition_score=float(fields.get("minimum_audition_score") or 0),
        physical_skill_requirement=str(fields.get("physical_skill_requirement") or "Standard")[:20],
        aquatic_experience_required=bool(fields.get("aquatic_experience_required") or False),
        aerial_experience_required=bool(fields.get("aerial_experience_required") or False),
        stunt_experience_required=bool(fields.get("stunt_experience_required") or False),
        required_safety_certifications=list(fields.get("required_safety_certifications") or []),
        medical_clearance_required=bool(fields.get("medical_clearance_required") or False),
        audition_required=bool(fields.get("audition_required") or False),
        passport_validity_months_required=int(fields.get("passport_validity_months_required") or 6),
        visa_sponsorship_available=bool(fields.get("visa_sponsorship_available") or False),
        required_languages=list(fields.get("required_languages") or []),
        overnight_rehearsal_required=bool(fields.get("overnight_rehearsal_required") or False),
        weekly_budget_min_usd=bmin,
        weekly_budget_max_usd=bmax,
        travel_provided=bool(fields.get("travel_provided") or False),
        accommodation_provided=bool(fields.get("accommodation_provided") or False),
        per_diem_usd=float(fields.get("per_diem_usd") or 0),
        production_risk_level=str(fields.get("production_risk_level") or "Medium")[:20],
        urgency_level=str(fields.get("urgency_level") or "Standard")[:20],
        booking_created_date=today,
        application_deadline=r_start - timedelta(days=7) if r_start > today else today,
        special_instructions=str(fields.get("special_instructions") or "")[:5000],
        requirement_status="Open",
    )


@router.post("/confirm", response_model=RequirementOut)
def confirm_job(body: JobConfirmRequest, db: Session = Depends(get_db)):
    req = _build_requirement(db, body.fields)
    db.add(req)
    db.commit()
    db.refresh(req)
    return RequirementOut.model_validate(req)
