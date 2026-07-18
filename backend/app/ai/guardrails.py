"""L4 guardrails (F26) — every LLM output is validated before display.

Checks (all deterministic, zero API cost):
- invented_number: every number in TEXT must exist in SOURCE
- protected_attribute: no gender/age/ethnicity/religion/appearance language
- gate_contradiction: TEXT may not contradict the deterministic eligibility

`enforce()` is the single entry point: validate → (optional) one regenerate →
deterministic fallback. An LLM sentence never reaches the screen unchecked.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Callable

# Single source of truth for protected-attribute patterns (query_planner and
# intake import from here).
PROTECTED_PATTERNS: list[tuple[str, str]] = [
    (r"\b(female|male|woman|women|man|men|girl|boy)s?\b", "gender"),
    (r"\b(young|elderly|middle.?aged|under \d{2} years old|age \d{2})\b", "age"),
    (r"\b(white|black|asian|hispanic|latino|latina|caucasian|african)\b", "ethnicity"),
    (r"\b(christian|muslim|hindu|jewish|buddhist)\b", "religion"),
    (r"\b(attractive|beautiful|handsome|pretty|good.?looking|slim|thin)\b", "appearance"),
]

_POSITIVE_VERDICT_RE = re.compile(
    r"\b(recommended|is eligible|excellent match|strong match|good match|shortlist(?:ed)?)\b", re.I
)
_NEGATIVE_VERDICT_RE = re.compile(r"\bnot eligible\b|\bineligible\b|\brejected\b", re.I)


@dataclass
class GuardrailVerdict:
    verdict: str = "pass"  # "pass" | "fail"
    violations: list[dict[str, str]] = field(default_factory=list)

    def add(self, vtype: str, detail: str) -> None:
        self.verdict = "fail"
        self.violations.append({"type": vtype, "detail": detail})

    def as_dict(self) -> dict[str, Any]:
        return {"verdict": self.verdict, "violations": self.violations}


def _numbers(text: str) -> set[str]:
    """Extract numbers, normalising thousands separators (5,000 == 5000)."""
    return {n.replace(",", "") for n in re.findall(r"\d[\d,]*(?:\.\d+)?", text or "")}


def is_grounded(explanation: str, facts: dict[str, Any]) -> bool:
    """Every number the LLM cites must exist in the facts payload."""
    nums_in_text = _numbers(explanation)
    allowed = _numbers(str(facts))
    # Rounding leniency: 87 is fine when source has 87.75
    truncated = {a.split(".")[0] for a in allowed}
    return all(n in allowed or n in truncated for n in nums_in_text) if nums_in_text else True


def protected_attribute_hits(text: str) -> list[str]:
    hits: list[str] = []
    lower = (text or "").lower()
    for pattern, label in PROTECTED_PATTERNS:
        if re.search(pattern, lower):
            hits.append(label)
    return hits


def contradicts_gates(text: str, facts: dict[str, Any]) -> str | None:
    """Detect narrative polarity contradicting deterministic eligibility."""
    eligible = facts.get("eligible")
    if eligible is None:
        return None
    if eligible is False and _POSITIVE_VERDICT_RE.search(text or "") and not _NEGATIVE_VERDICT_RE.search(text or ""):
        return "text implies a positive outcome but the candidate is not eligible"
    if eligible is True and _NEGATIVE_VERDICT_RE.search(text or "") and not _POSITIVE_VERDICT_RE.search(text or ""):
        return "text implies rejection but the candidate is eligible"
    return None


def validate_output(text: str, facts: dict[str, Any]) -> GuardrailVerdict:
    """F26 core check — deterministic, applied to EVERY LLM output."""
    verdict = GuardrailVerdict()
    if not is_grounded(text, facts):
        verdict.add("invented_number", "text cites a number not present in the source data")
    for label in protected_attribute_hits(text):
        verdict.add("protected_attribute", f"references '{label}' — not permitted in outputs")
    contradiction = contradicts_gates(text, facts)
    if contradiction:
        verdict.add("gate_contradiction", contradiction)
    return verdict


def enforce(
    text: str,
    facts: dict[str, Any],
    *,
    fallback: Callable[[], str],
    regenerate: Callable[[], str] | None = None,
) -> tuple[str, dict[str, Any], bool]:
    """Validate → one regenerate attempt → deterministic fallback.

    Returns (safe_text, verdict_dict, used_fallback). The returned text ALWAYS
    passes validation — fallbacks are template-built from facts, so they cannot
    fail; if one somehow does, we degrade to a fixed neutral sentence.
    """
    verdict = validate_output(text, facts)
    if verdict.verdict == "pass":
        return text, verdict.as_dict(), False

    if regenerate is not None:
        try:
            retry = regenerate()
            retry_verdict = validate_output(retry, facts)
            if retry_verdict.verdict == "pass":
                out = retry_verdict.as_dict()
                out["regenerated"] = True
                return retry, out, False
        except Exception:
            pass

    safe = fallback()
    final = validate_output(safe, facts)
    if final.verdict != "pass":
        safe = "See the computed score breakdown and gate results for this candidate."
    out = verdict.as_dict()
    out["fallback_used"] = True
    return safe, out, True


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
