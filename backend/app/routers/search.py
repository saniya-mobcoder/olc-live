"""Natural language talent search -- hybrid BM25 + vector (F13)."""
from __future__ import annotations

import re

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..ai.query_planner import apply_plan_filters, plan_query
from ..ai.retrieval import hybrid_rank
from ..database import IS_POSTGRES, get_db
from ..embeddings import OpenAIConfigError, cosine_similarity, embed_text, talent_document
from ..engine.matcher import score_talent_against_requirement
from ..models import Talent, TalentAvailability
from ..schemas import ScoreAgainstOut, ScoreAgainstRequest, SearchRequest, TalentOut

router = APIRouter(prefix="/search", tags=["search"])


def parse_query(query: str) -> dict:
    q = query.lower()
    filters: dict = {"skills": [], "languages": [], "categories": [], "countries": []}

    if "elite" in q:
        filters["elite_only"] = True
    if "aquatic" in q or "diving" in q or "diver" in q:
        filters["aquatic"] = True
    if "aerial" in q:
        filters["aerial"] = True
    if "stunt" in q:
        filters["stunt"] = True

    for cat in ["performer", "creative", "technical", "production"]:
        if cat in q:
            filters["categories"].append(cat.capitalize())

    for lang in ["arabic", "english", "french", "spanish", "mandarin", "cantonese", "hindi", "japanese", "german"]:
        if lang in q:
            filters["languages"].append(lang.capitalize())

    return filters


def _filter_boost(talent: Talent, filters: dict, query: str) -> float:
    score = 0.0
    blob = " ".join(
        [
            talent.full_name,
            talent.profile_title,
            talent.talent_category,
            talent.primary_role,
            " ".join(talent.secondary_roles or []),
            " ".join(talent.primary_skills or []),
            " ".join(talent.languages or []),
            talent.country,
            talent.city,
        ]
    ).lower()

    for word in re.findall(r"[a-zA-Z]+", query.lower()):
        if len(word) > 2 and word in blob:
            score += 0.5

    if filters.get("elite_only"):
        score += 2.0 if talent.physical_skill_level == "Elite" else -1.0
    if filters.get("aquatic") and talent.aquatic_performance_experience:
        score += 2.0
    if filters.get("aerial") and talent.aerial_performance_experience:
        score += 2.0
    if filters.get("stunt") and talent.stunt_experience:
        score += 2.0

    for cat in filters["categories"]:
        if talent.talent_category == cat:
            score += 3.0

    for lang in filters["languages"]:
        if lang in (talent.languages or []):
            score += 1.5

    return score


@router.post("/talents", response_model=list[TalentOut])
def search_talents(body: SearchRequest, db: Session = Depends(get_db)):
    filters = parse_query(body.query)
    query_vec = None
    try:
        query_vec = embed_text(body.query)
    except OpenAIConfigError:
        query_vec = None
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Embed failed: {exc}") from exc

    if IS_POSTGRES and query_vec is not None:
        vec_literal = "[" + ",".join(str(float(x)) for x in query_vec) + "]"
        rows = db.execute(
            text(
                """
                SELECT talent_id, (embedding <=> CAST(:qvec AS vector)) AS distance
                FROM talents
                WHERE embedding IS NOT NULL
                ORDER BY embedding <=> CAST(:qvec AS vector)
                LIMIT :lim
                """
            ),
            {"qvec": vec_literal, "lim": max(body.limit * 5, 50)},
        ).fetchall()
        id_to_sim = {r.talent_id: 1.0 - float(r.distance) for r in rows}
        talents = (
            db.query(Talent).filter(Talent.talent_id.in_(list(id_to_sim.keys()))).all()
            if id_to_sim
            else []
        )
    else:
        talents = db.query(Talent).all()
        id_to_sim = {
            t.talent_id: cosine_similarity(query_vec, t.embedding or [])
            for t in talents
            if t.embedding and query_vec is not None
        }

    # Hybrid BM25 + vector RRF
    items = [
        {
            "id": t.talent_id,
            "text": talent_document(t),
            "vector": t.embedding,
            "talent": t,
        }
        for t in talents
    ]
    fused = hybrid_rank(
        body.query,
        items,
        query_vector=query_vec,
        limit=max(body.limit * 3, 30),
    )
    by_id = {t.talent_id: t for t in talents}
    scored: list[tuple[float, Talent]] = []
    for tid, rrf in fused:
        t = by_id.get(tid)
        if not t:
            continue
        boost = _filter_boost(t, filters, body.query)
        semantic = id_to_sim.get(tid, 0.0)
        total = rrf * 20.0 + semantic * 5.0 + boost
        if total > 0 or boost > 0:
            scored.append((total, t))

    # If hybrid empty (no embeddings), fall back to keyword boost only
    if not scored:
        for t in talents:
            boost = _filter_boost(t, filters, body.query)
            if boost > 0:
                scored.append((boost, t))

    scored.sort(key=lambda x: (-x[0], x[1].talent_id))
    return [TalentOut.model_validate(t) for _, t in scored[: body.limit]]


def _availability_filter(db: Session, talents: list[Talent], date_from: str, date_until: str) -> list[Talent]:
    """Keep only talents fully 'Available' across the requested window."""
    from datetime import date as _date

    try:
        start = _date.fromisoformat(date_from)
        end = _date.fromisoformat(date_until)
    except ValueError:
        return talents
    if end < start:
        return talents
    window_days = (end - start).days + 1
    ids = [t.talent_id for t in talents]
    rows = (
        db.query(TalentAvailability.talent_id)
        .filter(
            TalentAvailability.talent_id.in_(ids),
            TalentAvailability.availability_date >= start,
            TalentAvailability.availability_date <= end,
            TalentAvailability.availability_status == "Available",
            TalentAvailability.partially_available.is_(False),
        )
        .all()
    )
    counts: dict[str, int] = {}
    for (tid,) in rows:
        counts[tid] = counts.get(tid, 0) + 1
    return [t for t in talents if counts.get(t.talent_id, 0) >= window_days]


@router.post("/planned")
def search_planned(body: SearchRequest, db: Session = Depends(get_db)):
    """F13 upgrade — LLM Query Planner (heuristic fallback) + structured
    filters + hybrid semantic ranking. Returns the plan for full transparency."""
    plan = plan_query(db, body.query)

    pool = db.query(Talent).all()
    filtered = apply_plan_filters(pool, plan.filters)
    if plan.filters.available_from and plan.filters.available_until:
        filtered = _availability_filter(
            db, filtered, plan.filters.available_from, plan.filters.available_until
        )

    semantic_q = plan.semantic_query or body.query
    query_vec = None
    try:
        query_vec = embed_text(semantic_q)
    except Exception:
        query_vec = None

    items = [
        {"id": t.talent_id, "text": talent_document(t), "vector": t.embedding}
        for t in filtered
    ]
    fused = hybrid_rank(semantic_q, items, query_vector=query_vec, limit=max(body.limit * 3, 30))
    by_id = {t.talent_id: t for t in filtered}
    ordered: list[Talent] = [by_id[tid] for tid, _ in fused if tid in by_id]
    seen = {t.talent_id for t in ordered}
    ordered.extend(t for t in filtered if t.talent_id not in seen)

    return {
        "plan": plan.model_dump(),
        "result_count": min(len(ordered), body.limit),
        "filtered_pool": len(filtered),
        "total_pool": len(pool),
        "results": [TalentOut.model_validate(t) for t in ordered[: body.limit]],
    }


@router.post("/score-against", response_model=ScoreAgainstOut)
def score_against(body: ScoreAgainstRequest, db: Session = Depends(get_db)):
    try:
        return score_talent_against_requirement(db, body.requirement_id, body.talent_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
