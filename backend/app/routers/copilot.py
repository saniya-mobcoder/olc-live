"""Conversational producer copilot -- match-grounded or FAQ support mode (tiered)."""
from __future__ import annotations

import json
import re
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..ai.agent import run_copilot_chat
from ..database import get_db
from ..embeddings import OpenAIConfigError, cosine_similarity, embed_text
from ..engine.matcher import serialize_run
from ..models import MatchRun, Talent
from ..schemas import CopilotRequest, CopilotResponse

router = APIRouter(prefix="/copilot", tags=["copilot"])

_TALENT_ID_RE = re.compile(r"(TAL-\d+)", re.I)
_FAQ_DIR = Path(__file__).resolve().parents[3] / "data" / "faq"


def _talent_ids_in_message(message: str) -> list[str]:
    found = _TALENT_ID_RE.findall(message)
    seen: set[str] = set()
    out: list[str] = []
    for raw in found:
        tid = raw.upper()
        if tid not in seen:
            seen.add(tid)
            out.append(tid)
    return out


def _row_dump(row) -> dict:
    return row.model_dump(mode="json")


def _load_faq_docs() -> list[dict[str, str]]:
    docs: list[dict[str, str]] = []
    if not _FAQ_DIR.exists():
        return docs
    for path in sorted(_FAQ_DIR.glob("*.md")):
        docs.append({"source": path.name, "text": path.read_text(encoding="utf-8")})
    return docs


def _retrieve_faq(message: str, top_k: int = 3) -> tuple[str, list[str]]:
    docs = _load_faq_docs()
    if not docs:
        return "No FAQ documents available.", []

    scored: list[tuple[float, dict[str, str]]] = []
    try:
        qvec = embed_text(message)
        for doc in docs:
            dvec = embed_text(doc["text"][:4000])
            scored.append((cosine_similarity(qvec, dvec), doc))
    except OpenAIConfigError:
        tokens = {t for t in re.findall(r"[a-zA-Z]{3,}", message.lower())}
        for doc in docs:
            blob = doc["text"].lower()
            overlap = sum(1 for t in tokens if t in blob)
            scored.append((float(overlap), doc))

    scored.sort(key=lambda x: -x[0])
    top = [doc for _, doc in scored[:top_k]]
    chunks = [f"SOURCE {d['source']}:\n{d['text']}" for d in top]
    sources = [d["source"] for d in top]
    return "\n\n".join(chunks), sources


def _gather_match_context(db: Session, body: CopilotRequest) -> tuple[str, list[str]]:
    if not body.match_run_id:
        raise HTTPException(
            status_code=400,
            detail="Run match first and pass match_run_id to the copilot.",
        )

    run = db.get(MatchRun, body.match_run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Match run not found")

    data = serialize_run(db, run)
    sources: list[str] = [run.id]
    chunks: list[str] = []

    shortlist = [
        {
            "rank": r.rank,
            "talent_id": r.talent_id,
            "name": r.talent.full_name if r.talent else None,
            "score": r.score,
            "category": r.match_category,
            "failed_gates": r.failed_gates,
        }
        for r in data.shortlist
    ]
    rejected = [
        {
            "talent_id": r.talent_id,
            "name": r.talent.full_name if r.talent else None,
            "score": r.score,
            "failed_gates": r.failed_gates,
            "reasons": r.rejection_reasons,
        }
        for r in data.rejected[:40]
    ]
    chunks.append("SHORTLIST:\n" + json.dumps(shortlist, indent=2))
    chunks.append("REJECTED:\n" + json.dumps(rejected, indent=2))

    focus_ids = _talent_ids_in_message(body.message)
    if body.talent_id:
        focus_ids = [
            body.talent_id.upper(),
            *[t for t in focus_ids if t != body.talent_id.upper()],
        ]

    all_rows = list(data.shortlist) + list(data.other_eligible) + list(data.rejected)
    by_id = {r.talent_id: r for r in all_rows}

    for tid in focus_ids[:2]:
        row = by_id.get(tid)
        if row:
            label = "COMPARE_TALENT" if len(focus_ids) > 1 else "FOCUS_TALENT"
            chunks.append(f"{label}:\n" + json.dumps(_row_dump(row), indent=2))
            sources.append(tid)
            for gate in row.failed_gates or []:
                if gate not in sources:
                    sources.append(gate)
        else:
            talent = db.get(Talent, tid)
            if talent:
                chunks.append(
                    "TALENT_PROFILE:\n"
                    + json.dumps(
                        {
                            "talent_id": talent.talent_id,
                            "name": talent.full_name,
                            "role": talent.primary_role,
                            "skills": talent.primary_skills,
                            "weekly_rate_usd": talent.weekly_contract_rate_usd,
                            "city": talent.city,
                            "country": talent.country,
                        },
                        indent=2,
                    )
                )
                sources.append(tid)

    return "\n\n".join(chunks), sources


def _offline_match_reply(context: str, message: str, sources: list[str]) -> str:
    lines = [
        "Offline copilot (no API keys) — answer grounded on match context only.",
        f"Question: {message}",
        "",
    ]
    try:
        for block in context.split("\n\n"):
            if "failed_gates" in block and (
                block.startswith("FOCUS_TALENT:") or block.startswith("COMPARE_TALENT:")
            ):
                payload = json.loads(block.split(":", 1)[1].strip())
                gates = payload.get("failed_gates") or []
                reasons = payload.get("rejection_reasons") or payload.get("reasons") or []
                tid = payload.get("talent_id", "talent")
                if gates or reasons:
                    lines.append(f"{tid} failed gates: {', '.join(gates) or 'none'}.")
                    if reasons:
                        lines.append("Reasons: " + "; ".join(reasons[:4]))
                    lines.append(f"Sources: {', '.join(sources)}")
                    return "\n".join(lines)
        if "SHORTLIST:" in context:
            short_json = context.split("SHORTLIST:\n", 1)[1].split("\n\n", 1)[0]
            shortlist = json.loads(short_json)
            if shortlist:
                lines.append("Shortlist summary:")
                for row in shortlist[:5]:
                    lines.append(
                        f"- Rank {row.get('rank')}: {row.get('talent_id')} "
                        f"({row.get('name')}) score={row.get('score')} "
                        f"[{row.get('category')}]"
                    )
                lines.append(f"Sources: {', '.join(sources)}")
                return "\n".join(lines)
    except Exception:
        pass
    lines.append(context[:1200])
    lines.append(f"Sources: {', '.join(sources)}")
    return "\n".join(lines)


def _offline_support_reply(context: str, message: str, sources: list[str]) -> str:
    body = context
    if "SOURCE " in context:
        first = context.split("SOURCE ", 1)[1]
        if ":\n" in first:
            body = first.split(":\n", 1)[1].split("\n\nSOURCE ", 1)[0]
    return (
        f"Offline support answer for: {message}\n\n"
        f"{body.strip()[:1500]}\n\n"
        f"Sources: {', '.join(sources)}"
    )


@router.post("/chat", response_model=CopilotResponse)
def chat_endpoint(body: CopilotRequest, db: Session = Depends(get_db)):
    mode = (body.mode or "match").strip().lower()
    if mode not in ("match", "support"):
        raise HTTPException(status_code=400, detail="mode must be match or support")

    if mode == "support":
        context, sources = _retrieve_faq(body.message)
        system = (
            "You are the OLC product support copilot. "
            "Answer only from the provided FAQ sources. "
            "Cite the source filenames. If the FAQ does not cover the question, say so."
        )
        offline = _offline_support_reply
    else:
        context, sources = _gather_match_context(db, body)
        system = (
            "You are the OLC Talent Matching copilot for live-production producers. "
            "Answer only from the provided match context. Be concise and specific. "
            "If explaining a rejection, cite the failed gate names and plain-English reasons. "
            "If comparing talents, use scores and failed_gates from context only. "
            "Do not invent talent IDs, scores, or gates."
        )
        offline = _offline_match_reply

    outcome = run_copilot_chat(
        system=system, context=context, message=body.message, mode=mode
    )
    if not outcome.get("used_llm") or not outcome.get("reply"):
        return CopilotResponse(
            reply=offline(context, body.message, sources),
            sources=sources,
            provider="template",
            model="none",
            tier=outcome.get("tier"),
            cost_usd=0.0,
        )

    return CopilotResponse(
        reply=outcome["reply"],
        sources=sources,
        provider=outcome.get("provider"),
        model=outcome.get("model"),
        tier=outcome.get("tier"),
        cost_usd=outcome.get("cost_usd"),
    )
