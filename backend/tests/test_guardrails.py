"""F26 guardrail validator: invented numbers, protected attributes, gate
contradictions, enforce() fallback chain. All offline/deterministic."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.ai.explain import explain_match
from app.ai.guardrails import (
    contradicts_gates,
    enforce,
    is_grounded,
    protected_attribute_hits,
    validate_output,
)

FACTS = {
    "eligible": True,
    "score": 87.75,
    "match_category": "Excellent Match",
    "positive_reasons": ["Meets all mandatory production skills"],
    "risk_factors": [],
    "weekly_rate": 5000,
}


def test_grounded_numbers_pass():
    assert is_grounded("Scored 87.75 with a rate of $5,000.", FACTS)
    # Truncated citation of a source decimal is allowed
    assert is_grounded("Scored 87 overall.", FACTS)


def test_invented_number_fails():
    verdict = validate_output("Scored 92.5 overall.", FACTS)
    assert verdict.verdict == "fail"
    assert any(v["type"] == "invented_number" for v in verdict.violations)


def test_protected_attribute_blocked():
    hits = protected_attribute_hits("A strong young female performer")
    assert "gender" in hits and "age" in hits
    verdict = validate_output("She is a beautiful performer scoring 87.75", FACTS)
    assert any(v["type"] == "protected_attribute" for v in verdict.violations)


def test_gate_contradiction_detected():
    ineligible = {"eligible": False, "score": 40.0}
    assert contradicts_gates("This candidate is recommended for shortlist.", ineligible)
    assert contradicts_gates("Not eligible due to missing certification.", ineligible) is None
    verdict = validate_output("Strong match — recommended.", ineligible)
    assert any(v["type"] == "gate_contradiction" for v in verdict.violations)


def test_enforce_falls_back_and_reports():
    text, verdict, used_fallback = enforce(
        "Scored 99.9 — recommended!",  # invented number
        {"eligible": False, "score": 40.0, "rejection_reasons": ["Missing mandatory production skill"]},
        fallback=lambda: "Not eligible: Missing mandatory production skill.",
    )
    assert used_fallback is True
    assert verdict["verdict"] == "fail"
    assert verdict.get("fallback_used") is True
    assert "Not eligible" in text


def test_enforce_regenerate_path():
    calls = {"n": 0}

    def regen() -> str:
        calls["n"] += 1
        return "Scored 87.75 — Excellent Match, recommended."

    text, verdict, used_fallback = enforce(
        "Scored 99.9!",
        FACTS,
        fallback=lambda: "fallback",
        regenerate=regen,
    )
    assert calls["n"] == 1
    assert used_fallback is False
    assert verdict.get("regenerated") is True
    assert "87.75" in text


def test_explain_match_offline_is_guarded_shape():
    facts = {
        "eligible": False,
        "failed_gates": ["mandatory_skills_met"],
        "rejection_reasons": ["Missing mandatory production skill"],
    }
    out = explain_match(facts)
    assert out["grounded"] is True
    assert "explanation" in out and out["explanation"]
