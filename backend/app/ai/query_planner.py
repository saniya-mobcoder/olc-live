"""F13/F27 Query Planner — NL search → structured filters + semantic query.

LLM-first (Groq 70B, JSON mode, temp 0) with a deterministic heuristic
fallback so search works offline and in tests. Both paths emit the same
QueryPlan shape and both pass through the fairness screen: protected
attributes are never allowed to become filters.
"""
from __future__ import annotations

import json
import re
from typing import Any

from pydantic import BaseModel, Field, ValidationError
from sqlalchemy.orm import Session

from ..models import Talent
from .providers import AIConfigError, TaskTier, chat

# ---------------------------------------------------------------------------
# Plan schema
# ---------------------------------------------------------------------------


class PlanFilters(BaseModel):
    talent_category: str | None = None
    primary_role: str | None = None
    country: str | None = None
    city: str | None = None
    languages: list[str] = Field(default_factory=list)
    physical_skill_level: str | None = None       # Standard | Athletic | Elite
    safety_training_level: str | None = None
    max_weekly_rate_usd: float | None = None
    min_experience_years: float | None = None
    travel_ready: bool | None = None
    relocation_available: bool | None = None
    aerial_performance_experience: bool | None = None
    aquatic_performance_experience: bool | None = None
    stunt_experience: bool | None = None
    available_from: str | None = None             # ISO date
    available_until: str | None = None


class QueryPlan(BaseModel):
    filters: PlanFilters = Field(default_factory=PlanFilters)
    semantic_query: str | None = None
    unsupported: list[str] = Field(default_factory=list)
    planner: str = "heuristic"                    # "llm" | "heuristic"


# ---------------------------------------------------------------------------
# Fairness screen — protected attributes never become filters
# ---------------------------------------------------------------------------

# Single source of truth lives in guardrails (F26).
from .guardrails import PROTECTED_PATTERNS as _PROTECTED_PATTERNS


def fairness_screen(query: str) -> list[str]:
    hits: list[str] = []
    q = (query or "").lower()
    for pattern, label in _PROTECTED_PATTERNS:
        if re.search(pattern, q):
            hits.append(f"'{label}' is not a permitted search criterion")
    return hits


def strip_protected_terms(query: str) -> str:
    q = query
    for pattern, _ in _PROTECTED_PATTERNS:
        q = re.sub(pattern, " ", q, flags=re.I)
    return re.sub(r"\s+", " ", q).strip()


# ---------------------------------------------------------------------------
# Vocabulary (grounds both LLM and validation)
# ---------------------------------------------------------------------------


def build_vocab(db: Session) -> dict[str, list[str]]:
    talents = db.query(Talent).all()
    roles: set[str] = set()
    langs: set[str] = set()
    for t in talents:
        roles.add(t.primary_role)
        roles.update(t.secondary_roles or [])
        langs.update(t.languages or [])
    return {
        "talent_category": sorted({t.talent_category for t in talents}),
        "primary_role": sorted(roles),
        "country": sorted({t.country for t in talents}),
        "city": sorted({t.city for t in talents}),
        "languages": sorted(langs),
        "physical_skill_level": ["Standard", "Athletic", "Elite"],
        "safety_training_level": sorted({t.safety_training_level for t in talents if t.safety_training_level}),
    }


def _validate_against_vocab(filters: PlanFilters, vocab: dict[str, list[str]]) -> tuple[PlanFilters, list[str]]:
    """Drop values not in vocabulary — never invent, never fuzzy-force."""
    dropped: list[str] = []

    def check(field: str, value: str | None) -> str | None:
        if value is None:
            return None
        allowed = vocab.get(field, [])
        for candidate in allowed:
            if candidate.lower() == value.lower():
                return candidate
        dropped.append(f"{field}='{value}' not in vocabulary")
        return None

    filters.talent_category = check("talent_category", filters.talent_category)
    filters.primary_role = check("primary_role", filters.primary_role)
    filters.country = check("country", filters.country)
    filters.city = check("city", filters.city)
    filters.physical_skill_level = check("physical_skill_level", filters.physical_skill_level)
    filters.safety_training_level = check("safety_training_level", filters.safety_training_level)
    filters.languages = [
        lang for lang in (check("languages", item) for item in filters.languages) if lang
    ]
    return filters, dropped


# ---------------------------------------------------------------------------
# LLM planner (P2)
# ---------------------------------------------------------------------------

_SYSTEM = """Convert a recruiter's natural-language talent search into structured filters plus an
optional semantic query. Return ONLY JSON:
{"filters": {"talent_category": null, "primary_role": null, "country": null, "city": null,
 "languages": [], "physical_skill_level": null, "safety_training_level": null,
 "max_weekly_rate_usd": null, "min_experience_years": null, "travel_ready": null,
 "relocation_available": null, "aerial_performance_experience": null,
 "aquatic_performance_experience": null, "stunt_experience": null,
 "available_from": null, "available_until": null},
 "semantic_query": "<free text for embedding search or null>",
 "unsupported": []}
Only include filters the user actually implied. Filter values MUST match the provided
vocabulary exactly. Anything about ethnicity, gender, age, religion or appearance goes to
"unsupported" with the note "not a permitted search criterion". Dates ISO-8601. Rates in
USD ("under $5k" -> max_weekly_rate_usd 5000)."""


def _llm_plan(query: str, vocab: dict[str, list[str]]) -> QueryPlan:
    result = chat(
        [
            {"role": "system", "content": _SYSTEM},
            {"role": "user", "content": f"VOCAB: {json.dumps(vocab)}\nQUERY: \"{query}\""},
        ],
        tier=TaskTier.CHEAP_CHAT,
        temperature=0.0,
        max_tokens=500,
        response_format={"type": "json_object"},
    )
    payload = json.loads(result.content)
    plan = QueryPlan(
        filters=PlanFilters(**(payload.get("filters") or {})),
        semantic_query=payload.get("semantic_query"),
        unsupported=list(payload.get("unsupported") or []),
        planner="llm",
    )
    return plan


# ---------------------------------------------------------------------------
# Heuristic fallback (offline / tests / LLM failure)
# ---------------------------------------------------------------------------

_RATE_RE = re.compile(r"(?:under|below|max|less than|<)\s*\$?\s*([\d,.]+)\s*(k)?", re.I)
_EXP_RE = re.compile(r"(\d+)\s*\+?\s*years?", re.I)


def _heuristic_plan(query: str, vocab: dict[str, list[str]]) -> QueryPlan:
    q = query.lower()
    f = PlanFilters()

    if "elite" in q:
        f.physical_skill_level = "Elite"
    if re.search(r"\baquatic|\bdiving|\bdiver|\bswim", q):
        f.aquatic_performance_experience = True
    if "aerial" in q:
        f.aerial_performance_experience = True
    if "stunt" in q:
        f.stunt_experience = True
    if "travel" in q and ("ready" in q or "-ready" in q):
        f.travel_ready = True

    for cat in vocab.get("talent_category", []):
        if cat.lower() in q:
            f.talent_category = cat
            break
    for role in vocab.get("primary_role", []):
        if role.lower() in q:
            f.primary_role = role
            break
    for country in vocab.get("country", []):
        if re.search(rf"\b{re.escape(country.lower())}\b", q):
            f.country = country
            break
    f.languages = [lang for lang in vocab.get("languages", []) if re.search(rf"\b{re.escape(lang.lower())}\b", q)]

    m = _RATE_RE.search(q)
    if m:
        value = float(m.group(1).replace(",", ""))
        if m.group(2):
            value *= 1000
        f.max_weekly_rate_usd = value

    m = _EXP_RE.search(q)
    if m and ("experience" in q or "+" in m.group(0)):
        f.min_experience_years = float(m.group(1))

    return QueryPlan(filters=f, semantic_query=strip_protected_terms(query), planner="heuristic")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def plan_query(db: Session, query: str) -> QueryPlan:
    """NL query → validated QueryPlan. LLM-first, heuristic fallback, always
    fairness-screened and vocabulary-validated."""
    vocab = build_vocab(db)
    violations = fairness_screen(query)

    plan: QueryPlan
    try:
        plan = _llm_plan(query, vocab)
    except Exception:
        # AIConfigError (no key), JSON/schema errors, network — all fall back.
        plan = _heuristic_plan(query, vocab)

    plan.filters, dropped = _validate_against_vocab(plan.filters, vocab)
    plan.unsupported = list(dict.fromkeys([*plan.unsupported, *violations, *dropped]))
    if plan.semantic_query:
        plan.semantic_query = strip_protected_terms(plan.semantic_query)
    return plan


def apply_plan_filters(talents: list[Talent], f: PlanFilters) -> list[Talent]:
    """Deterministic in-memory filter application (pool = 500, trivially fast).
    On Postgres these become WHERE clauses; behaviour is identical."""
    out: list[Talent] = []
    for t in talents:
        if f.talent_category and t.talent_category != f.talent_category:
            continue
        if f.primary_role and f.primary_role not in {t.primary_role, *(t.secondary_roles or [])}:
            continue
        if f.country and t.country != f.country:
            continue
        if f.city and t.city != f.city:
            continue
        if f.languages and not set(f.languages).issubset(set(t.languages or [])):
            continue
        if f.physical_skill_level:
            rank = {"Standard": 1, "Athletic": 2, "Elite": 3}
            if rank.get(t.physical_skill_level, 0) < rank.get(f.physical_skill_level, 0):
                continue
        if f.safety_training_level and t.safety_training_level != f.safety_training_level:
            continue
        if f.max_weekly_rate_usd is not None and float(t.weekly_contract_rate_usd or 0) > f.max_weekly_rate_usd:
            continue
        if f.min_experience_years is not None and float(t.experience_years or 0) < f.min_experience_years:
            continue
        if f.travel_ready is not None and bool(t.travel_ready) != f.travel_ready:
            continue
        if f.relocation_available is not None and bool(t.relocation_available) != f.relocation_available:
            continue
        if f.aerial_performance_experience and not t.aerial_performance_experience:
            continue
        if f.aquatic_performance_experience and not t.aquatic_performance_experience:
            continue
        if f.stunt_experience and not t.stunt_experience:
            continue
        out.append(t)
    return out
