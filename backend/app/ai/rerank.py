"""Advisory re-ranker (F02/F03) — local ML first, optional LLM one-liners."""
from __future__ import annotations

from typing import Any

from .guardrails import gate_guard_eligible
from .predictors import booking_success_prior


def ml_rerank(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Re-order eligible rows by hybrid of base score + booking-success prior.
    Does not change deterministic final_match_score — adds advisory_score + reason.
    """
    eligible = [r for r in rows if r.get("eligible")]
    ineligible = [r for r in rows if not r.get("eligible")]

    scored: list[tuple[float, dict[str, Any]]] = []
    for row in eligible:
        base = float(row.get("score") or 0)
        prior = booking_success_prior(row)
        advisory = round(0.75 * base + 0.25 * prior, 2)
        enriched = dict(row)
        enriched["advisory_score"] = advisory
        enriched["booking_success_prior"] = prior
        enriched["rerank_reason"] = (
            f"Base {base:.1f} + reliability prior {prior:.1f} → advisory {advisory:.1f}"
        )
        scored.append((advisory, enriched))

    scored.sort(key=lambda x: (-x[0], -(x[1].get("score") or 0), x[1].get("talent_id") or ""))
    ordered = [r for _, r in scored]
    # Gate guard: only eligible ids
    ids = gate_guard_eligible(
        [r["talent_id"] for r in ordered if r.get("talent_id")],
        {r["talent_id"] for r in ordered if r.get("talent_id")},
    )
    by_id = {r["talent_id"]: r for r in ordered}
    guarded = [by_id[i] for i in ids if i in by_id]
    return guarded + ineligible
