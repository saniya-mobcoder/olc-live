from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import ProductionCredit, Requirement, Talent
from ..schemas import ProductionCreditOut, RequirementOut, TalentOut

router = APIRouter(tags=["catalog"])


@router.get("/requirements", response_model=list[RequirementOut])
def list_requirements(db: Session = Depends(get_db), limit: int = 200):
    return (
        db.query(Requirement)
        .order_by(Requirement.requirement_id)
        .limit(limit)
        .all()
    )


@router.get("/requirements/{req_id}", response_model=RequirementOut)
def get_requirement(req_id: str, db: Session = Depends(get_db)):
    req = db.get(Requirement, req_id)
    if not req:
        raise HTTPException(status_code=404, detail="Requirement not found")
    return req


@router.get("/talents", response_model=list[TalentOut])
def list_talents(db: Session = Depends(get_db), limit: int = 500):
    return (
        db.query(Talent)
        .order_by(Talent.talent_id)
        .limit(limit)
        .all()
    )


@router.get("/talents/{talent_id}", response_model=TalentOut)
def get_talent(talent_id: str, db: Session = Depends(get_db)):
    talent = db.get(Talent, talent_id)
    if not talent:
        raise HTTPException(status_code=404, detail="Talent not found")
    return talent


@router.get("/talents/{talent_id}/credits", response_model=list[ProductionCreditOut])
def get_talent_credits(talent_id: str, db: Session = Depends(get_db)):
    return (
        db.query(ProductionCredit)
        .filter(ProductionCredit.talent_id == talent_id)
        .order_by(ProductionCredit.end_date.desc())
        .all()
    )
