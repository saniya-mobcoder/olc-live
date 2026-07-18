"""AI cost / observability dashboard (F19)."""
from fastapi import APIRouter

from ..ai.providers import ai_cost_summary
from ..schemas import AiCostSummaryOut

router = APIRouter(prefix="/ai", tags=["ai"])


@router.get("/costs", response_model=AiCostSummaryOut)
def get_ai_costs():
    return AiCostSummaryOut(**ai_cost_summary())
