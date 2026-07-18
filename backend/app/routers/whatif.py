"""What-if scenario comparison + AI scenario suggestions (F17)."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..ai.agent import suggest_whatif_scenarios
from ..database import get_db
from ..engine.matcher import run_match, serialize_run
from ..models import Requirement
from ..schemas import WhatIfOut, WhatIfRequest, WhatIfSuggestOut

router = APIRouter(prefix="/what-if", tags=["what-if"])


@router.post("", response_model=WhatIfOut)
def what_if(body: WhatIfRequest, db: Session = Depends(get_db)):
    try:
        baseline = run_match(
            db,
            body.requirement_id,
            top_k=body.top_k,
            scenario_label=body.baseline_label,
            params_override={},
        )
        scenario = run_match(
            db,
            body.requirement_id,
            top_k=body.top_k,
            scenario_label=body.scenario_label,
            params_override=body.params_override,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    base_out = serialize_run(db, baseline, top_k=body.top_k)
    scen_out = serialize_run(db, scenario, top_k=body.top_k)

    from ..models import MatchResult

    base_eligible = {
        r.talent_id
        for r in db.query(MatchResult).filter(
            MatchResult.run_id == baseline.id, MatchResult.eligible.is_(True)
        )
    }
    scen_eligible = {
        r.talent_id
        for r in db.query(MatchResult).filter(
            MatchResult.run_id == scenario.id, MatchResult.eligible.is_(True)
        )
    }

    return WhatIfOut(
        baseline=base_out,
        scenario=scen_out,
        eligible_delta=len(scen_eligible) - len(base_eligible),
        new_talent_ids=sorted(scen_eligible - base_eligible),
        lost_talent_ids=sorted(base_eligible - scen_eligible),
    )


@router.post("/suggest", response_model=WhatIfSuggestOut)
def suggest_scenarios(requirement_id: str, db: Session = Depends(get_db)):
    req = db.get(Requirement, requirement_id)
    if not req:
        raise HTTPException(status_code=404, detail="Requirement not found")
    facts = {
        "requirement_id": req.requirement_id,
        "production_title": req.production_title,
        "role": req.required_primary_role,
        "city": req.city,
        "country": req.country,
        "weekly_budget_max_usd": req.weekly_budget_max_usd,
        "visa_sponsorship_available": req.visa_sponsorship_available,
        "minimum_audition_score": req.minimum_audition_score,
        "overnight_rehearsal_required": req.overnight_rehearsal_required,
    }
    result = suggest_whatif_scenarios(facts)
    return WhatIfSuggestOut(
        requirement_id=requirement_id,
        scenarios=result.get("scenarios") or [],
        provider=result.get("provider"),
        model=result.get("model"),
        cost_usd=result.get("cost_usd"),
        used_llm=bool(result.get("used_llm")),
    )
