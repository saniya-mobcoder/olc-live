"""Executive operational + commercial reporting."""
from __future__ import annotations

import io
from collections import Counter, defaultdict
from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from openpyxl import Workbook
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy.orm import Session

from ..ai.narrate import narrate
from ..database import get_db
from ..engine.matcher import build_audition_lookup, build_availability_lookup
from ..engine.scoring import compute_score
from ..models import (
    ExecutiveReport,
    MatchDecision,
    MatchResult,
    MatchRun,
    ProductionCredit,
    Requirement,
    Talent,
)
from ..schemas import (
    ExecutiveReportOut,
    ExecutiveReportRequest,
    FillabilityOut,
    FillabilityRequest,
    NarrativeOut,
)

router = APIRouter(prefix="/reports", tags=["reports"])


def _next_report_id(db: Session) -> str:
    count = db.query(ExecutiveReport).count() + 1
    return f"RPT-{count:06d}"


def compute_executive_kpis(
    db: Session, period_start: date, period_end: date
) -> dict:
    if period_end < period_start:
        raise ValueError("period_end must be on or after period_start")

    reqs = db.query(Requirement).all()
    opened = [
        r
        for r in reqs
        if period_start <= r.booking_created_date <= period_end
    ]
    closed_statuses = {"Filled", "Closed", "Cancelled", "Completed"}
    closed = [
        r
        for r in reqs
        if r.requirement_status in closed_statuses
        and period_start <= r.application_deadline <= period_end
    ]

    runs = (
        db.query(MatchRun)
        .filter(
            MatchRun.created_at >= datetime.combine(period_start, datetime.min.time()),
            MatchRun.created_at
            <= datetime.combine(period_end, datetime.max.time()),
        )
        .all()
    )
    run_ids = [r.id for r in runs]
    results = (
        db.query(MatchResult).filter(MatchResult.run_id.in_(run_ids)).all()
        if run_ids
        else []
    )

    eligible_by_run: dict[str, int] = defaultdict(int)
    shortlist_by_run: dict[str, int] = defaultdict(int)
    gate_fails: Counter[str] = Counter()
    runs_by_req: Counter[str] = Counter()

    for run in runs:
        runs_by_req[run.requirement_id] += 1

    for row in results:
        if row.eligible:
            eligible_by_run[row.run_id] += 1
            if row.rank is not None and row.rank <= 5:
                shortlist_by_run[row.run_id] += 1
        for gate in row.failed_gates or []:
            gate_fails[gate] += 1

    match_run_count = len(runs)
    avg_eligible = (
        round(sum(eligible_by_run.values()) / match_run_count, 2)
        if match_run_count
        else 0.0
    )
    filled_runs = sum(1 for rid in run_ids if shortlist_by_run.get(rid, 0) >= 1)
    top5_fill_rate = (
        round(100.0 * filled_runs / match_run_count, 1) if match_run_count else 0.0
    )
    avg_runs_per_req = (
        round(sum(runs_by_req.values()) / len(runs_by_req), 2) if runs_by_req else 0.0
    )

    credits = (
        db.query(ProductionCredit)
        .filter(
            ProductionCredit.start_date <= period_end,
            ProductionCredit.end_date >= period_start,
        )
        .all()
    )
    contract_value_sum = round(sum(c.contract_value_usd for c in credits), 2)
    rehire_eligible = sum(1 for c in credits if c.rehire_eligible)
    rehire_share = (
        round(100.0 * rehire_eligible / len(credits), 1) if credits else 0.0
    )

    talents = db.query(Talent).all()
    avg_talent_rate = (
        round(
            sum(t.weekly_contract_rate_usd for t in talents) / max(1, len(talents)),
            2,
        )
        if talents
        else 0.0
    )
    avg_budget_max = (
        round(
            sum(r.weekly_budget_max_usd for r in reqs) / max(1, len(reqs)),
            2,
        )
        if reqs
        else 0.0
    )

    decisions = (
        db.query(MatchDecision)
        .join(MatchRun, MatchRun.id == MatchDecision.run_id)
        .filter(
            MatchRun.created_at >= datetime.combine(period_start, datetime.min.time()),
            MatchRun.created_at
            <= datetime.combine(period_end, datetime.max.time()),
        )
        .all()
    )
    decision_count = len(decisions)
    accepted = sum(1 for d in decisions if d.decision in ("hire", "hold"))
    decision_acceptance_pct = (
        round(100.0 * accepted / decision_count, 1) if decision_count else 0.0
    )

    return {
        "period": {
            "start": period_start.isoformat(),
            "end": period_end.isoformat(),
        },
        "operational": {
            "requirements_opened": len(opened),
            "requirements_closed": len(closed),
            "match_runs": match_run_count,
            "avg_eligible_per_run": avg_eligible,
            "top5_fill_rate_pct": top5_fill_rate,
            "avg_runs_per_requirement": avg_runs_per_req,
            "decision_count": decision_count,
            "decision_acceptance_pct": decision_acceptance_pct,
            "gate_fail_frequency": [
                {"gate": g, "count": c}
                for g, c in gate_fails.most_common(15)
            ],
        },
        "commercial": {
            "contract_value_usd": contract_value_sum,
            "credits_in_period": len(credits),
            "rehire_eligible_share_pct": rehire_share,
            "avg_weekly_budget_max_usd": avg_budget_max,
            "avg_talent_weekly_rate_usd": avg_talent_rate,
            "budget_vs_rate_delta_usd": round(avg_budget_max - avg_talent_rate, 2),
        },
    }


def compute_fillability_rows(db: Session, requirement_ids: list[str] | None, limit: int) -> list[dict]:
    """Live fillability per requirement: full 500-talent scan through the same
    deterministic gates + scoring used by run_match (no ground-truth reads).

    Status rule:
      Blocked   -> zero eligible candidates
      Critical  -> eligible < talent_required
      Attention -> recommended < talent_required OR eligible < 2x talent_required
      Healthy   -> otherwise
    """
    query = db.query(Requirement)
    if requirement_ids:
        query = query.filter(Requirement.requirement_id.in_(requirement_ids))
    reqs = query.order_by(Requirement.application_deadline).limit(limit).all()
    talents = db.query(Talent).all()

    rows: list[dict] = []
    for req in reqs:
        availability_lookup = build_availability_lookup(db, req)
        audition_lookup = build_audition_lookup(db, req.requirement_id)

        eligible = recommended = excellent = 0
        gate_fails: Counter[str] = Counter()
        shortlist: list[dict] = []
        for talent in talents:
            result = compute_score(
                req,
                talent,
                availability_lookup=availability_lookup,
                audition_score=audition_lookup.get(talent.talent_id),
            )
            if result["eligible"]:
                eligible += 1
                score = float(result["score"] or 0.0)
                if score >= 70:
                    recommended += 1
                    shortlist.append(
                        {
                            "talent_id": talent.talent_id,
                            "full_name": talent.full_name,
                            "score": score,
                            "match_category": result["match_category"],
                        }
                    )
                if score >= 85:
                    excellent += 1
            else:
                for gate in result["failed_gates"]:
                    gate_fails[gate] += 1

        needed = max(1, int(req.talent_required or 1))
        if eligible == 0:
            status = "Blocked"
            action = "No eligible candidates in the pool — relax constraints (what-if) or source externally via StageLync."
        elif eligible < needed:
            status = "Critical"
            action = f"Only {eligible} eligible for {needed} positions — immediate sourcing or requirement adjustment needed."
        elif recommended < needed or eligible < 2 * needed:
            status = "Attention Required"
            action = f"Shortlist depth is thin ({recommended} recommended / {eligible} eligible for {needed} positions) — widen search or review top gate failures."
        else:
            status = "Healthy"
            action = "Sufficient qualified talent — proceed to shortlist review."

        shortlist.sort(key=lambda s: -s["score"])
        rows.append(
            {
                "requirement_id": req.requirement_id,
                "production_title": req.production_title,
                "production_type": req.production_type,
                "city": req.city,
                "country": req.country,
                "required_primary_role": req.required_primary_role,
                "application_deadline": req.application_deadline,
                "talent_required": needed,
                "evaluated": len(talents),
                "eligible": eligible,
                "recommended": recommended,
                "excellent": excellent,
                "coverage_ratio": round(eligible / needed, 2),
                "status": status,
                "sourcing_action": action,
                "top_gate_fails": [
                    {"gate": g, "count": c} for g, c in gate_fails.most_common(3)
                ],
                "shortlist_preview": shortlist[:5],
            }
        )
    return rows


@router.post("/fillability", response_model=FillabilityOut)
def fillability_report(body: FillabilityRequest, db: Session = Depends(get_db)):
    rows = compute_fillability_rows(db, body.requirement_ids, body.limit)
    by_status = Counter(r["status"] for r in rows)
    return FillabilityOut(
        generated_at=datetime.utcnow(),
        rows=rows,
        summary={
            "requirements_analysed": len(rows),
            "healthy": by_status.get("Healthy", 0),
            "attention_required": by_status.get("Attention Required", 0),
            "critical": by_status.get("Critical", 0),
            "blocked": by_status.get("Blocked", 0),
            "total_positions": sum(r["talent_required"] for r in rows),
            "total_recommended": sum(r["recommended"] for r in rows),
        },
    )


@router.post("/executive", response_model=ExecutiveReportOut)
def generate_executive_report(
    body: ExecutiveReportRequest, db: Session = Depends(get_db)
):
    try:
        payload = compute_executive_kpis(db, body.period_start, body.period_end)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if body.include_narrative:
        narr = narrate(
            {
                "period_start": body.period_start.isoformat(),
                "period_end": body.period_end.isoformat(),
                "kpis": payload,
                "top_gate_fails": (payload.get("operational") or {}).get(
                    "gate_fail_frequency", []
                )[:5],
            },
            kind="report",
            client_facing=True,
        )
        payload = {**payload, "narrative": narr}

    report = ExecutiveReport(
        id=_next_report_id(db),
        period_start=body.period_start,
        period_end=body.period_end,
        created_at=datetime.utcnow(),
        scenario_label=body.scenario_label,
        payload=payload,
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


@router.post("/{report_id}/narrate", response_model=NarrativeOut)
def narrate_report(report_id: str, db: Session = Depends(get_db)):
    report = _get_report_or_404(db, report_id)
    payload = report.payload or {}
    result = narrate(
        {
            "period_start": report.period_start.isoformat(),
            "period_end": report.period_end.isoformat(),
            "kpis": payload,
            "top_gate_fails": (payload.get("operational") or {}).get(
                "gate_fail_frequency", []
            )[:5],
        },
        kind="report",
        client_facing=True,
    )
    payload = {**payload, "narrative": result}
    report.payload = payload
    db.add(report)
    db.commit()
    return NarrativeOut(
        narrative=result["narrative"],
        provider=result.get("provider"),
        model=result.get("model"),
        cost_usd=result.get("cost_usd"),
        used_llm=bool(result.get("used_llm")),
    )


@router.get("", response_model=list[ExecutiveReportOut])
def list_reports(db: Session = Depends(get_db), limit: int = 20):
    return (
        db.query(ExecutiveReport)
        .order_by(ExecutiveReport.created_at.desc())
        .limit(limit)
        .all()
    )


def _get_report_or_404(db: Session, report_id: str) -> ExecutiveReport:
    report = db.get(ExecutiveReport, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


@router.get("/{report_id}.xlsx")
def export_report_xlsx(report_id: str, db: Session = Depends(get_db)):
    report = _get_report_or_404(db, report_id)
    payload = report.payload or {}
    ops = payload.get("operational", {})
    commercial = payload.get("commercial", {})

    wb = Workbook()
    summary = wb.active
    summary.title = "Summary"
    summary.append(["OLC Executive Report", report.id])
    summary.append(["Period", f"{report.period_start} → {report.period_end}"])
    summary.append(["Generated", report.created_at.isoformat()])
    summary.append([])
    summary.append(["Operational KPIs"])
    for key, value in ops.items():
        if key == "gate_fail_frequency":
            continue
        summary.append([key, value])
    summary.append([])
    summary.append(["Commercial KPIs"])
    for key, value in commercial.items():
        summary.append([key, value])

    gates = wb.create_sheet("Gate Fails")
    gates.append(["Gate", "Count"])
    for row in ops.get("gate_fail_frequency", []):
        gates.append([row.get("gate"), row.get("count")])

    out = io.BytesIO()
    wb.save(out)
    out.seek(0)
    return StreamingResponse(
        out,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="{report_id}_executive.xlsx"'
        },
    )


@router.get("/{report_id}.pdf")
def export_report_pdf(report_id: str, db: Session = Depends(get_db)):
    report = _get_report_or_404(db, report_id)
    payload = report.payload or {}
    ops = payload.get("operational", {})
    commercial = payload.get("commercial", {})

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4)
    styles = getSampleStyleSheet()
    story = [
        Paragraph("OLC Executive Report", styles["Title"]),
        Spacer(1, 10),
        Paragraph(f"Report ID: <b>{report.id}</b>", styles["Normal"]),
        Paragraph(
            f"Period: <b>{report.period_start}</b> → <b>{report.period_end}</b>",
            styles["Normal"],
        ),
        Paragraph(f"Generated: {report.created_at.isoformat()}Z", styles["Normal"]),
        Spacer(1, 16),
        Paragraph("Operational", styles["Heading2"]),
    ]
    op_rows = [["Metric", "Value"]]
    for key, value in ops.items():
        if key == "gate_fail_frequency":
            continue
        op_rows.append([key.replace("_", " "), str(value)])
    op_table = Table(op_rows, colWidths=[280, 160])
    op_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0B3D2E")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                (
                    "ROWBACKGROUNDS",
                    (0, 1),
                    (-1, -1),
                    [colors.white, colors.HexColor("#E8F2EE")],
                ),
            ]
        )
    )
    story.append(op_table)
    story.append(Spacer(1, 16))
    story.append(Paragraph("Commercial", styles["Heading2"]))
    com_rows = [["Metric", "Value"]] + [
        [k.replace("_", " "), str(v)] for k, v in commercial.items()
    ]
    com_table = Table(com_rows, colWidths=[280, 160])
    com_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0B3D2E")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                (
                    "ROWBACKGROUNDS",
                    (0, 1),
                    (-1, -1),
                    [colors.white, colors.HexColor("#E8F2EE")],
                ),
            ]
        )
    )
    story.append(com_table)
    story.append(Spacer(1, 16))
    story.append(Paragraph("Top gate failures", styles["Heading2"]))
    for row in ops.get("gate_fail_frequency", [])[:8]:
        story.append(
            Paragraph(
                f"<b>{row.get('gate')}</b>: {row.get('count')}",
                styles["Normal"],
            )
        )
    doc.build(story)
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{report_id}_executive.pdf"'
        },
    )


@router.get("/{report_id}", response_model=ExecutiveReportOut)
def get_report(report_id: str, db: Session = Depends(get_db)):
    return _get_report_or_404(db, report_id)
