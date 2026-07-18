"""L4 guardrails — groundedness + gate-guard."""
from __future__ import annotations

import re
from typing import Any


def is_grounded(explanation: str, facts: dict[str, Any]) -> bool:
    """Cheap check: any number the LLM cites must exist in the facts payload."""
    nums_in_text = set(re.findall(r"\d+(?:\.\d+)?", explanation))
    allowed = set(re.findall(r"\d+(?:\.\d+)?", str(facts)))
    return nums_in_text.issubset(allowed) if nums_in_text else True


def strip_ungrounded_numbers(explanation: str, facts: dict[str, Any]) -> str:
    """Replace numbers not present in facts with '[score]' placeholders."""
    allowed = set(re.findall(r"\d+(?:\.\d+)?", str(facts)))

    def repl(m: re.Match[str]) -> str:
        return m.group(0) if m.group(0) in allowed else "[n]"

    return re.sub(r"\d+(?:\.\d+)?", repl, explanation)


def gate_guard_eligible(ai_recommended_ids: list[str], eligible_ids: set[str]) -> list[str]:
    """Drop any AI-ranked talent that failed deterministic gates."""
    return [tid for tid in ai_recommended_ids if tid in eligible_ids]


def assert_gates_unchanged(
    before_failed: list[str], after_failed: list[str]
) -> bool:
    return sorted(before_failed or []) == sorted(after_failed or [])
