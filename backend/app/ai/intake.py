"""F21 Requirement Intake — vocabulary-grounded brief extraction (P1).

Upgrades the basic jobs parser with:
- dataset vocabulary grounding: extracted skills/roles/certs/languages must map
  to values that actually exist in the data — otherwise they land in
  `unmapped_terms` instead of silently producing a requirement that rejects
  everyone;
- per-field confidence (LLM-stated when available, heuristic otherwise);
- clarifying questions for missing critical fields (null + question is correct
  behaviour — the system never guesses budgets or dates).
"""
from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from ..models import Requirement, Talent
from .providers import TaskTier, chat

# Fields the review UI treats as critical (question if absent).
CRITICAL_FIELDS = (
    "required_primary_role",
    "required_category",
    "city",
    "country",
    "rehearsal_start_date",
    "performance_start_date",
    "performance_end_date",
    "weekly_budget_max_usd",
    "talent_required",
)

_QUESTION_TEXT: dict[str, str] = {
    "required_primary_role": "Which primary role is this casting for?",
    "required_category": "Is this a Performer, Creative, Technical or Production role?",
    "city": "Which city will rehearsals and performances take place in?",
    "country": "Which country is the production in?",
    "rehearsal_start_date": "When do rehearsals start (date)?",
    "performance_start_date": "When is the first performance (date)?",
    "performance_end_date": "When is the final performance (date)?",
    "weekly_budget_max_usd": "What is the maximum weekly budget per talent (USD)?",
    "talent_required": "How many talents are needed for this role?",
    "mandatory_skills": "Which skills are strictly mandatory for this role?",
}

_VOCAB_FIELDS: dict[str, str] = {
    # requirement field -> vocab key
    "required_category": "categories",
    "required_primary_role": "roles",
    "production_type": "production_types",
    "venue_type": "venue_types",
}

_VOCAB_LIST_FIELDS: dict[str, str] = {
    "acceptable_secondary_roles": "roles",
    "mandatory_skills": "skills",
    "preferred_skills": "skills",
    "required_safety_certifications": "certifications",
    "required_languages": "languages",
}


def build_requirement_vocab(db: Session) -> dict[str, list[str]]:
    """Canonical vocabulary from BOTH sides of the dataset (profiles + reqs)."""
    roles: set[str] = set()
    skills: set[str] = set()
    certs: set[str] = set()
    langs: set[str] = set()
    for t in db.query(Talent).all():
        roles.add(t.primary_role)
        roles.update(t.secondary_roles or [])
        skills.update(t.primary_skills or [])
        skills.update(t.secondary_skills or [])
        certs.update(t.professional_certifications or [])
        langs.update(t.languages or [])
    prod_types: set[str] = set()
    venues: set[str] = set()
    cats: set[str] = set()
    for r in db.query(Requirement).all():
        roles.add(r.required_primary_role)
        roles.update(r.acceptable_secondary_roles or [])
        skills.update(r.mandatory_skills or [])
        skills.update(r.preferred_skills or [])
        certs.update(r.required_safety_certifications or [])
        langs.update(r.required_languages or [])
        prod_types.add(r.production_type)
        venues.add(r.venue_type)
        cats.add(r.required_category)
    return {
        "roles": sorted(roles),
        "skills": sorted(skills),
        "certifications": sorted(certs),
        "languages": sorted(langs),
        "production_types": sorted(prod_types),
        "venue_types": sorted(venues),
        "categories": sorted(cats) or ["Performer", "Creative", "Technical", "Production"],
    }


def _canonical(value: str, allowed: list[str]) -> str | None:
    """Exact (case-insensitive) match first, then unique containment match."""
    v = (value or "").strip().lower()
    if not v:
        return None
    for a in allowed:
        if a.lower() == v:
            return a
    contains = [a for a in allowed if v in a.lower() or a.lower() in v]
    if len(contains) == 1:
        return contains[0]
    return None


def ground_fields(fields: dict[str, Any], vocab: dict[str, list[str]]) -> tuple[dict[str, Any], list[str]]:
    """Map extracted values onto dataset vocabulary; collect unmapped terms."""
    unmapped: list[str] = []
    out = dict(fields)

    for field, key in _VOCAB_FIELDS.items():
        raw = out.get(field)
        if raw is None or raw == "":
            continue
        mapped = _canonical(str(raw), vocab[key])
        if mapped:
            out[field] = mapped
        else:
            unmapped.append(f"{field}: '{raw}'")

    for field, key in _VOCAB_LIST_FIELDS.items():
        raw_list = out.get(field) or []
        if not isinstance(raw_list, list):
            raw_list = [raw_list]
        mapped_list: list[str] = []
        for raw in raw_list:
            mapped = _canonical(str(raw), vocab[key])
            if mapped:
                if mapped not in mapped_list:
                    mapped_list.append(mapped)
            else:
                unmapped.append(f"{field}: '{raw}'")
        out[field] = mapped_list

    return out, unmapped


def clarifying_questions(fields: dict[str, Any]) -> list[str]:
    questions: list[str] = []
    for key in CRITICAL_FIELDS:
        val = fields.get(key)
        if val is None or val == "" or val == [] or (key == "weekly_budget_max_usd" and not val):
            questions.append(_QUESTION_TEXT.get(key, f"Please provide {key}."))
    if not fields.get("mandatory_skills"):
        questions.append(_QUESTION_TEXT["mandatory_skills"])
    return questions


def assign_confidence(
    fields: dict[str, Any],
    *,
    llm_confidence: dict[str, float] | None,
    used_llm: bool,
) -> dict[str, float]:
    """Per-field confidence: LLM-stated when valid, else presence heuristic."""
    conf: dict[str, float] = {}
    for key, value in fields.items():
        stated = (llm_confidence or {}).get(key)
        if isinstance(stated, (int, float)) and 0.0 <= float(stated) <= 1.0:
            conf[key] = round(float(stated), 2)
            continue
        if value is None or value == "" or value == []:
            conf[key] = 0.0
        elif used_llm:
            conf[key] = 0.75
        else:
            conf[key] = 0.6  # regex/heuristic extraction
    return conf


_P1_SYSTEM = """You are the Requirement Intake Agent for OLC's casting platform. Convert a free-text
casting brief into a production requirement. Return ONLY valid JSON:
{"fields": {...}, "field_confidence": {"<field>": 0.0-1.0}, "questions": ["..."]}

Allowed keys in "fields": production_title, production_type, required_category,
required_primary_role, acceptable_secondary_roles, mandatory_skills, preferred_skills,
city, country, venue_type, rehearsal_start_date, rehearsal_end_date,
technical_rehearsal_start_date, technical_rehearsal_end_date, performance_start_date,
performance_end_date, number_of_performances, contract_duration_days, talent_required,
ensemble_or_solo, minimum_experience_years, minimum_director_rating,
minimum_showreel_score, minimum_audition_score, physical_skill_requirement,
aquatic_experience_required, aerial_experience_required, stunt_experience_required,
required_safety_certifications, medical_clearance_required, audition_required,
passport_validity_months_required, visa_sponsorship_available, required_languages,
overnight_rehearsal_required, weekly_budget_min_usd, weekly_budget_max_usd,
travel_provided, accommodation_provided, per_diem_usd, production_risk_level,
urgency_level, application_deadline, special_instructions.

Rules:
- Roles, skills, certifications and languages MUST come from the provided vocabulary
  lists. A term not in the vocabulary goes into "questions" as a clarification — never
  invent or force-map it.
- Dates ISO-8601. NEVER guess budgets or dates: unknown -> omit the key and add a
  question. required_category one of Performer, Creative, Technical, Production.
- physical_skill_requirement one of Standard, Athletic, Elite.
- Include "field_confidence" for every key you output."""


def llm_extract(brief: str, vocab: dict[str, list[str]]) -> dict[str, Any]:
    """P1 extraction — quality tier, temp 0, JSON mode. Raises on any failure
    (caller falls back to the offline parser)."""
    vocab_msg = json.dumps(
        {
            "roles": vocab["roles"],
            "skills": vocab["skills"],
            "certifications": vocab["certifications"],
            "languages": vocab["languages"],
            "production_types": vocab["production_types"],
            "venue_types": vocab["venue_types"],
        }
    )
    result = chat(
        [
            {"role": "system", "content": _P1_SYSTEM},
            {"role": "user", "content": f"VOCAB: {vocab_msg}\nBRIEF:\n\"\"\"{brief[:6000]}\"\"\""},
        ],
        tier=TaskTier.QUALITY_CHAT,
        temperature=0.0,
        max_tokens=1400,
        response_format={"type": "json_object"},
    )
    payload = json.loads(result.content)
    if not isinstance(payload, dict) or not isinstance(payload.get("fields"), dict):
        raise RuntimeError("Intake extraction did not return the expected shape")
    return payload
