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

from ..database import get_db
from ..models import (
    ExecutiveReport,
    MatchDecision,
    MatchResult,
    MatchRun,
    ProductionCredit,
    Requirement,
    Talent,
)
from ..schemas import ExecutiveReportOut, ExecutiveReportRequest

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


@router.post("/executive", response_model=ExecutiveReportOut)
def generate_executive_report(
    body: ExecutiveReportRequest, db: Session = Depends(get_db)
):
    try:
        payload = compute_executive_kpis(db, body.period_start, body.period_end)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

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
