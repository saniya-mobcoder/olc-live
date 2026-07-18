"""L2 grounded explanations (F11) — cheap_chat tier."""
from __future__ import annotations

import json
from typing import Any

from .guardrails import is_grounded, strip_ungrounded_numbers
from .providers import AIConfigError, TaskTier, chat

_SYSTEM = (
    "You explain a talent-matching decision for a live-production producer. "
    "You are given VERIFIED FACTS as JSON. Rules: "
    "(1) Use ONLY facts present in the JSON — never invent skills, dates, certs, or scores. "
    "(2) If eligible, explain why in 2-3 sentences citing the strongest positive_reasons. "
    "(3) If not eligible, state the exact failing gate(s) from rejection_reasons in plain English. "
    "(4) Mention risk_factors if present. Be concise, warm, non-technical. No markdown."
)


def fallback_explain(facts: dict[str, Any]) -> str:
    """Deterministic template if no API key — never leave the user without an answer."""
    if not facts.get("eligible"):
        reasons = facts.get("rejection_reasons") or []
        gates = facts.get("failed_gates") or []
        if reasons:
            return f"Not eligible: {'; '.join(str(r) for r in reasons[:3])}."
        if gates:
            return f"Not eligible due to: {', '.join(str(g) for g in gates)}."
        return "Not eligible: a mandatory requirement was not met."
    reasons = "; ".join(facts.get("positive_reasons") or []) or "meets all mandatory requirements"
    risk = facts.get("risk_factors") or []
    tail = f" Watch-outs: {'; '.join(str(r) for r in risk[:3])}." if risk else ""
    score = facts.get("score") or facts.get("final_match_score")
    cat = facts.get("match_category") or ""
    return f"Recommended ({cat}, score {score}): {reasons}.{tail}"


def explain_match(facts: dict[str, Any], *, skip_llm_if_clear_reject: bool = True) -> dict[str, Any]:
    """Return {explanation, provider, model, cost_usd, grounded, used_llm}."""
    if skip_llm_if_clear_reject and not facts.get("eligible") and (
        facts.get("failed_gates") or facts.get("rejection_reasons")
    ):
        text = fallback_explain(facts)
        return {
            "explanation": text,
            "provider": "template",
            "model": "none",
            "cost_usd": 0.0,
            "grounded": True,
            "used_llm": False,
        }

    try:
        result = chat(
            [
                {"role": "system", "content": _SYSTEM},
                {"role": "user", "content": json.dumps(facts, default=str)[:6000]},
            ],
            tier=TaskTier.CHEAP_CHAT,
            temperature=0.2,
            max_tokens=280,
        )
        text = result.content or fallback_explain(facts)
        grounded = is_grounded(text, facts)
        if not grounded:
            text = strip_ungrounded_numbers(text, facts)
            grounded = is_grounded(text, facts)
            if not grounded:
                text = fallback_explain(facts)
                grounded = True
        return {
            "explanation": text,
            "provider": result.provider,
            "model": result.model,
            "cost_usd": result.cost_usd,
            "grounded": grounded,
            "used_llm": True,
            "tokens_in": result.tokens_in,
            "tokens_out": result.tokens_out,
            "latency_ms": result.latency_ms,
        }
    except (AIConfigError, Exception):
        text = fallback_explain(facts)
        return {
            "explanation": text,
            "provider": "template",
            "model": "none",
            "cost_usd": 0.0,
            "grounded": True,
            "used_llm": False,
        }
