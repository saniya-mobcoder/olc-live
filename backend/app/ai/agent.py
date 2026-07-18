"""F16 copilot agent helpers — cheap FAQ / match Q&A, quality for multi-step."""
from __future__ import annotations

import json
import re
from typing import Any

from .guardrails import enforce
from .providers import AIConfigError, TaskTier, chat

_TOOLISH = re.compile(
    r"\b(what[- ]?if|compare|suggest|scenario|run match|shortlist|report|analyze)\b",
    re.I,
)


def needs_quality_tier(message: str, *, mode: str = "match") -> bool:
    """Escalate to Grok quality_chat for multi-step / tool-like producer asks."""
    if mode == "support":
        return False
    return bool(_TOOLISH.search(message or ""))


def run_copilot_chat(
    *,
    system: str,
    context: str,
    message: str,
    mode: str = "match",
) -> dict[str, Any]:
    tier = (
        TaskTier.QUALITY_CHAT
        if needs_quality_tier(message, mode=mode)
        else TaskTier.CHEAP_CHAT
    )
    user_content = f"CONTEXT:\n{context[:8000]}\n\nPRODUCER QUESTION:\n{message}"
    try:
        result = chat(
            [
                {"role": "system", "content": system},
                {"role": "user", "content": user_content},
            ],
            tier=tier,
            temperature=0.2,
            max_tokens=700,
        )
        # F26: copilot replies are validated against the tool-provided context.
        # Numbers must come from CONTEXT (or the user's own question); protected
        # attributes are blocked. Gate polarity check applies when context
        # carries an `eligible` flag.
        facts = {"context": context, "question": message}
        reply, verdict, used_fallback = enforce(
            result.content or "",
            facts,
            fallback=lambda: (
                "I could not produce a verified answer from the available data. "
                "Please check the score breakdown and audit trail, or rephrase the question."
            ),
        )
        return {
            "reply": reply,
            "provider": "template" if used_fallback else result.provider,
            "model": result.model,
            "tier": tier.value,
            "cost_usd": result.cost_usd,
            "guardrail": verdict,
            "used_llm": not used_fallback,
        }
    except AIConfigError as exc:
        return {
            "reply": None,
            "error": str(exc),
            "used_llm": False,
            "tier": tier.value,
        }


def suggest_whatif_scenarios(requirement_facts: dict[str, Any]) -> dict[str, Any]:
    """F17 — cheap_chat suggests high-impact param overrides; sim stays deterministic."""
    system = (
        "Suggest 3 what-if casting scenarios as JSON: "
        '{"scenarios":[{"label":"...","params_override":{...},"rationale":"..."}]}. '
        "Allowed override keys: visa_sponsorship_available (bool), "
        "weekly_budget_max_usd (number), minimum_audition_score (number), "
        "overnight_rehearsal_required (bool). Use only realistic deltas from the facts."
    )
    try:
        result = chat(
            [
                {"role": "system", "content": system},
                {
                    "role": "user",
                    "content": json.dumps(requirement_facts, default=str)[:4000],
                },
            ],
            tier=TaskTier.CHEAP_CHAT,
            temperature=0.3,
            max_tokens=500,
            response_format={"type": "json_object"},
        )
        data = json.loads(result.content)
        scenarios = data.get("scenarios") if isinstance(data, dict) else None
        if not isinstance(scenarios, list):
            scenarios = _default_scenarios(requirement_facts)
        return {
            "scenarios": scenarios[:3],
            "provider": result.provider,
            "model": result.model,
            "cost_usd": result.cost_usd,
            "used_llm": True,
        }
    except Exception:
        return {
            "scenarios": _default_scenarios(requirement_facts),
            "provider": "template",
            "model": "none",
            "cost_usd": 0.0,
            "used_llm": False,
        }


def _default_scenarios(facts: dict[str, Any]) -> list[dict[str, Any]]:
    budget = float(facts.get("weekly_budget_max_usd") or 3000)
    return [
        {
            "label": "Enable visa sponsorship",
            "params_override": {"visa_sponsorship_available": True},
            "rationale": "Often unlocks more eligible international talent.",
        },
        {
            "label": "Raise weekly budget 15%",
            "params_override": {"weekly_budget_max_usd": round(budget * 1.15, 2)},
            "rationale": "Relaxes budget gate for stronger shortlist.",
        },
        {
            "label": "Lower audition threshold",
            "params_override": {
                "minimum_audition_score": max(
                    0,
                    float(facts.get("minimum_audition_score") or 70) - 5,
                )
            },
            "rationale": "Widens audition-ready pool slightly.",
        },
    ]
