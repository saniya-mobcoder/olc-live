"""Talent pool analytics + optional insight narrative (F18)."""
from collections import defaultdict
from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..ai.narrate import narrate
from ..database import get_db
from ..models import Talent, TalentAvailability
from ..schemas import NarrativeOut, PoolAnalyticsOut

router = APIRouter(prefix="/analytics", tags=["analytics"])


def _compute_pool(db: Session, month: str) -> PoolAnalyticsOut:
    talents = db.query(Talent).all()
    by_region: dict[str, int] = defaultdict(int)
    by_role: dict[str, int] = defaultdict(int)
    by_category: dict[str, int] = defaultdict(int)

    year, mon = map(int, month.split("-"))
    month_start = date(year, mon, 1)
    month_end = date(year + (1 if mon == 12 else 0), 1 if mon == 12 else mon + 1, 1)

    for t in talents:
        by_region[t.country] += 1
        by_role[t.primary_role] += 1
        by_category[t.talent_category] += 1

    blocked_ids = {
        r.talent_id
        for r in db.query(TalentAvailability.talent_id)
        .filter(
            TalentAvailability.availability_date >= month_start,
            TalentAvailability.availability_date < month_end,
            TalentAvailability.availability_status != "Available",
        )
        .distinct()
    }
    available_in_month = len(talents) - len(blocked_ids)
    unavailable_in_month = len(blocked_ids)

    gaps = [
        {"role": role, "count": count, "gap": max(0, 5 - count)}
        for role, count in sorted(by_role.items())
        if count < 5
    ]

    return PoolAnalyticsOut(
        by_region=[{"region": k, "count": v} for k, v in sorted(by_region.items())],
        by_role=[{"role": k, "count": v} for k, v in sorted(by_role.items())],
        by_category=[{"category": k, "count": v} for k, v in sorted(by_category.items())],
        gaps=gaps,
        totals={
            "talent_count": len(talents),
            "elite_count": sum(
                1 for t in talents if t.physical_skill_level == "Elite"
            ),
            "avg_audition": round(
                sum(t.audition_readiness_score for t in talents)
                / max(1, len(talents)),
                1,
            ),
            "available_in_month": available_in_month,
            "partially_blocked_in_month": unavailable_in_month,
            "avg_experience_years": round(
                sum(t.experience_years for t in talents) / max(1, len(talents)), 1
            ),
            "avg_director_rating": round(
                sum(t.average_director_rating or 0 for t in talents)
                / max(
                    1,
                    sum(1 for t in talents if t.average_director_rating is not None),
                ),
                2,
            ),
        },
    )


@router.get("/pool", response_model=PoolAnalyticsOut)
def pool_analytics(db: Session = Depends(get_db), month: str = "2026-10"):
    return _compute_pool(db, month)


@router.post("/pool/narrative", response_model=NarrativeOut)
def pool_narrative(db: Session = Depends(get_db), month: str = "2026-10"):
    pool = _compute_pool(db, month)
    result = narrate(
        {
            "month": month,
            "total_talents": pool.totals.get("talent_count"),
            "gaps": pool.gaps[:8],
            "by_region": pool.by_region[:10],
            "totals": pool.totals,
        },
        kind="pool",
        client_facing=False,
    )
    return NarrativeOut(
        narrative=result["narrative"],
        provider=result.get("provider"),
        model=result.get("model"),
        cost_usd=result.get("cost_usd"),
        used_llm=bool(result.get("used_llm")),
    )
