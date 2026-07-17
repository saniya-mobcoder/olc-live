"""Export CSV/JSON/Excel/PDF + StageLync stub."""
from __future__ import annotations

import csv
import io
import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response, StreamingResponse
from openpyxl import Workbook
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy.orm import Session

from ..database import get_db
from ..engine.matcher import serialize_run
from ..models import Booking, MatchResult, MatchRun, Requirement, StageLyncLink, Talent

router = APIRouter(prefix="/export", tags=["export"])


def _load_run(db: Session, run_id: str):
    run = db.get(MatchRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Match run not found")
    return run, serialize_run(db, run)


@router.get("/shortlist/{run_id}.csv")
def export_csv(run_id: str, db: Session = Depends(get_db)):
    _, data = _load_run(db, run_id)
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        ["rank", "talent_id", "name", "score", "match_category", "weekly_rate_usd", "distance_km"]
    )
    for row in data.shortlist:
        t = row.talent
        writer.writerow(
            [
                row.rank,
                row.talent_id,
                t.full_name if t else "",
                row.score,
                row.match_category,
                t.weekly_contract_rate_usd if t else "",
                row.distance_km,
            ]
        )
    return Response(
        content=buf.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{run_id}_shortlist.csv"'},
    )


@router.get("/shortlist/{run_id}.json")
def export_json(run_id: str, db: Session = Depends(get_db)):
    _, data = _load_run(db, run_id)
    payload = data.model_dump(mode="json")
    return Response(
        content=json.dumps(payload, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{run_id}_shortlist.json"'},
    )


@router.get("/shortlist/{run_id}.xlsx")
def export_xlsx(run_id: str, db: Session = Depends(get_db)):
    _, data = _load_run(db, run_id)
    wb = Workbook()
    ws = wb.active
    ws.title = "Shortlist"
    ws.append(["Rank", "Talent ID", "Name", "Score", "Category", "Weekly Rate", "Distance km"])
    for row in data.shortlist:
        t = row.talent
        ws.append(
            [
                row.rank,
                row.talent_id,
                t.full_name if t else "",
                row.score,
                row.match_category,
                t.weekly_contract_rate_usd if t else "",
                row.distance_km,
            ]
        )
    rej = wb.create_sheet("Rejected")
    rej.append(["Talent ID", "Name", "Failed Gates", "Reasons"])
    for row in data.rejected:
        t = row.talent
        rej.append(
            [
                row.talent_id,
                t.full_name if t else "",
                ", ".join(row.failed_gates),
                " | ".join(row.rejection_reasons),
            ]
        )
    out = io.BytesIO()
    wb.save(out)
    out.seek(0)
    return StreamingResponse(
        out,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="{run_id}_shortlist.xlsx"'
        },
    )


@router.get("/shortlist/{run_id}.pdf")
def export_pdf(run_id: str, db: Session = Depends(get_db)):
    run, data = _load_run(db, run_id)
    req = db.get(Requirement, run.requirement_id)
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4)
    styles = getSampleStyleSheet()
    story = [
        Paragraph("OLC Talent Matching -- Shortlist Report", styles["Title"]),
        Spacer(1, 12),
        Paragraph(f"Match ID: <b>{run.id}</b>", styles["Normal"]),
        Paragraph(f"Requirement: <b>{run.requirement_id}</b> -- {req.production_title if req else ''}", styles["Normal"]),
        Paragraph(f"Generated: {datetime.utcnow().isoformat()}Z", styles["Normal"]),
        Spacer(1, 16),
        Paragraph("Top Candidates", styles["Heading2"]),
    ]
    table_data = [["Rank", "Talent", "Score", "Category", "Weekly Rate", "Distance km"]]
    for row in data.shortlist:
        t = row.talent
        table_data.append(
            [
                str(row.rank),
                f"{row.talent_id} {t.full_name if t else ''}",
                str(row.score),
                row.match_category,
                str(t.weekly_contract_rate_usd if t else ""),
                str(row.distance_km),
            ]
        )
    table = Table(table_data, colWidths=[40, 160, 60, 90, 80, 80])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0B3D2E")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#E8F2EE")]),
            ]
        )
    )
    story.append(table)
    story.append(Spacer(1, 20))
    story.append(Paragraph("Rejected (sample)", styles["Heading2"]))
    for row in data.rejected[:8]:
        reason = row.rejection_reasons[0] if row.rejection_reasons else "-"
        story.append(
            Paragraph(
                f"<b>{row.talent_id}</b>: {reason}",
                styles["Normal"],
            )
        )
    doc.build(story)
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{run_id}_shortlist.pdf"'},
    )


@router.get("/stagelync/{run_id}.json")
def export_stagelync(run_id: str, db: Session = Depends(get_db)):
    """StageLync-shaped export -- prefers linked StageLync IDs when present."""
    run, data = _load_run(db, run_id)
    req = db.get(Requirement, run.requirement_id)
    talent_to_sl = {
        link.talent_id: link.stagelync_person_id
        for link in db.query(StageLyncLink)
        .filter(StageLyncLink.talent_id.isnot(None))
        .all()
    }
    payload = {
        "format": "StageLyncShortlist.v1",
        "exported_at": datetime.utcnow().isoformat() + "Z",
        "production": {
            "external_req_id": run.requirement_id,
            "title": req.production_title if req else "",
            "venue": req.city if req else "",
            "start_date": req.rehearsal_start_date.isoformat() if req else None,
            "end_date": req.performance_end_date.isoformat() if req else None,
        },
        "candidates": [
            {
                "stagelync_person_id": talent_to_sl.get(row.talent_id, row.talent_id),
                "olc_talent_id": row.talent_id,
                "display_name": row.talent.full_name if row.talent else "",
                "match_rank": row.rank,
                "match_score": row.score,
                "weekly_rate_usd": row.talent.weekly_contract_rate_usd if row.talent else None,
                "role": row.talent.primary_role if row.talent else "",
                "notes": row.match_category,
                "linked": row.talent_id in talent_to_sl,
            }
            for row in data.shortlist
        ],
        "field_mapping": {
            "stagelync_person_id": "StageLyncLink.stagelync_person_id or Talent.talent_id",
            "olc_talent_id": "Talent.talent_id",
            "match_score": "MatchResult.score",
            "weekly_rate_usd": "Talent.weekly_contract_rate_usd",
        },
    }
    return Response(
        content=json.dumps(payload, indent=2),
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="{run_id}_stagelync.json"'
        },
    )


@router.get("/callsheet/{booking_id}.pdf")
def export_callsheet(booking_id: str, db: Session = Depends(get_db)):
    booking = db.get(Booking, booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    req = db.get(Requirement, booking.requirement_id)
    talent = db.get(Talent, booking.talent_id)
    result = (
        db.query(MatchResult)
        .filter(
            MatchResult.run_id == booking.match_run_id,
            MatchResult.talent_id == booking.talent_id,
        )
        .first()
    )

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4)
    styles = getSampleStyleSheet()
    story = [
        Paragraph("OLC Call Sheet", styles["Title"]),
        Spacer(1, 12),
        Paragraph(f"<b>Booking</b>: {booking.id}", styles["Normal"]),
        Paragraph(
            f"<b>Production</b>: {req.production_title if req else '—'}",
            styles["Normal"],
        ),
        Paragraph(
            f"<b>Role</b>: {req.required_primary_role if req else '—'}",
            styles["Normal"],
        ),
        Paragraph(
            f"<b>Talent</b>: {talent.full_name if talent else booking.talent_id} ({booking.talent_id})",
            styles["Normal"],
        ),
        Paragraph(
            f"<b>Venue</b>: {req.city if req else '—'}, {req.country if req else '—'}",
            styles["Normal"],
        ),
        Paragraph(
            f"<b>Dates</b>: {booking.start_date.isoformat()} → {booking.end_date.isoformat()}",
            styles["Normal"],
        ),
        Paragraph(
            f"<b>Weekly rate</b>: USD {booking.weekly_rate_usd:,.2f}",
            styles["Normal"],
        ),
        Spacer(1, 12),
    ]
    if result:
        story.append(Paragraph("Match snapshot", styles["Heading2"]))
        story.append(
            Paragraph(
                f"Score {result.score} · {result.match_category} · rank {result.rank}",
                styles["Normal"],
            )
        )
        if result.positive_reasons:
            story.append(
                Paragraph(
                    "Strengths: " + "; ".join(result.positive_reasons[:4]),
                    styles["Normal"],
                )
            )
    doc.build(story)
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{booking_id}_callsheet.pdf"'
        },
    )
