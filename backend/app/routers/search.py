"""Natural language talent search -- pgvector semantic + keyword filter hybrid."""
from __future__ import annotations

import re

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..database import IS_POSTGRES, get_db
from ..embeddings import OpenAIConfigError, cosine_similarity, embed_text
from ..engine.matcher import score_talent_against_requirement
from ..models import Talent
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
    try:
        query_vec = embed_text(body.query)
    except OpenAIConfigError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"OpenAI embed failed: {exc}") from exc

    if IS_POSTGRES:
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
            {"qvec": vec_literal, "lim": max(body.limit * 3, 30)},
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
            if t.embedding
        }

    scored: list[tuple[float, Talent]] = []
    for t in talents:
        semantic = id_to_sim.get(t.talent_id, 0.0)
        boost = _filter_boost(t, filters, body.query)
        total = semantic * 10.0 + boost
        if total > 0:
            scored.append((total, t))

    scored.sort(key=lambda x: (-x[0], x[1].talent_id))
    return [TalentOut.model_validate(t) for _, t in scored[: body.limit]]


@router.post("/score-against", response_model=ScoreAgainstOut)
def score_against(body: ScoreAgainstRequest, db: Session = Depends(get_db)):
    try:
        return score_talent_against_requirement(db, body.requirement_id, body.talent_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
