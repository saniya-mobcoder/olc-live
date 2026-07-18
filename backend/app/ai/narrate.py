"""L2 narratives for reports / pool insights (F14/F18) — quality_chat when client-facing."""
from __future__ import annotations

import json
from typing import Any

from .guardrails import enforce
from .providers import AIConfigError, TaskTier, chat


def fallback_narrative(payload: dict[str, Any], kind: str = "report") -> str:
    if kind == "pool":
        return (
            f"Talent pool snapshot: {payload.get('total_talents', 'n/a')} profiles. "
            f"Top gaps and regional supply are summarized in the dashboard numbers."
        )
    kpis = payload.get("kpis") or payload
    return (
        f"Executive summary for {payload.get('period_start', '')} → {payload.get('period_end', '')}: "
        f"match runs and fill rates are in the KPI pack. "
        f"Key gate pressure: {kpis.get('top_gate_fails') or kpis.get('gate_fail_top') or 'see chart'}."
    )


def narrate(
    payload: dict[str, Any],
    *,
    kind: str = "report",
    client_facing: bool = True,
) -> dict[str, Any]:
    """Generate a short executive narrative. Quality tier when client_facing."""
    system = (
        "You write a concise executive narrative for live-production casting leaders. "
        "Use ONLY numbers and facts from the JSON. 3-5 sentences. No markdown. "
        "Do not invent metrics."
    )
    tier = TaskTier.QUALITY_CHAT if client_facing else TaskTier.CHEAP_CHAT
    try:
        result = chat(
            [
                {"role": "system", "content": system},
                {
                    "role": "user",
                    "content": f"KIND={kind}\n{json.dumps(payload, default=str)[:5000]}",
                },
            ],
            tier=tier,
            temperature=0.3,
            max_tokens=350,
        )
        raw = result.content or fallback_narrative(payload, kind)
        # F26: narratives were previously unguarded — now validated like all output.
        text, verdict, used_fallback = enforce(
            raw, payload, fallback=lambda: fallback_narrative(payload, kind)
        )
        return {
            "narrative": text,
            "provider": "template" if used_fallback else result.provider,
            "model": result.model,
            "cost_usd": result.cost_usd,
            "guardrail": verdict,
            "used_llm": not used_fallback,
        }
    except (AIConfigError, Exception):
        return {
            "narrative": fallback_narrative(payload, kind),
            "provider": "template",
            "model": "none",
            "cost_usd": 0.0,
            "used_llm": False,
        }
