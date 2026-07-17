"""What-if scenario comparison -- vary requirement fields (budget, sponsorship,
minimum thresholds, ...) and compare eligible pools against a baseline run."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..engine.matcher import run_match, serialize_run
from ..schemas import WhatIfOut, WhatIfRequest

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
