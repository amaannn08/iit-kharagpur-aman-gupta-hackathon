"""Export API routes conforming to PRD Section 9.5 & 12."""

import csv
import io
import json

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from sentinel.storage.db import get_db
from sentinel.storage.repository import ReplayRepository

router = APIRouter(prefix="/exports", tags=["Exports & Audit Lineage"])


@router.get("/{run_id}")
def export_run_data(
    run_id: str,
    format: str = Query(default="json", pattern="^(json|csv)$"),
    db: Session = Depends(get_db),
) -> Response:
    """Export complete audit records and stress lineage for a replay run as JSON or CSV."""
    repo = ReplayRepository(db)
    run = repo.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found.")

    records = repo.get_records_for_run(run_id)
    signals = repo.get_signals_for_run(run_id)
    stress_runs = repo.list_stress_runs(run_id=run_id, limit=100)

    signals_map = {s.record_id: s for s in signals}

    if format == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(
            [
                "run_id",
                "record_id",
                "source_id",
                "source_type",
                "text",
                "is_duplicate",
                "duplicate_group_id",
                "entity_name",
                "entity_ticker",
                "sentiment_label",
                "sentiment_score",
                "event_label",
                "event_confidence",
                "impact_score",
                "eligible_for_action",
                "action_block_reasons",
            ]
        )

        for rec in records:
            sig = signals_map.get(rec.record_id)
            writer.writerow(
                [
                    run_id,
                    rec.record_id,
                    rec.source_id,
                    rec.source_type,
                    rec.text,
                    rec.is_duplicate,
                    rec.duplicate_group_id or "",
                    sig.entity_name if sig else "",
                    sig.entity_ticker if sig else "",
                    sig.sentiment_label if sig else "",
                    sig.sentiment_score if sig else "",
                    sig.event_label if sig else "",
                    sig.event_confidence if sig else "",
                    sig.impact_score if sig else "",
                    sig.eligible_for_action if sig else "",
                    sig.action_block_reasons if sig else "",
                ]
            )

        csv_content = output.getvalue()
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="sentinel_run_{run_id}.csv"'},
        )

    # Default JSON audit export
    payload = {
        "export_metadata": {
            "run_id": run_id,
            "status": run.status,
            "speed": run.speed,
            "total_records": run.total_records,
            "processed_records": run.processed_records,
            "duplicate_count": run.duplicate_count,
            "error_count": run.error_count,
        },
        "records": [
            {
                "record_id": r.record_id,
                "source_id": r.source_id,
                "source_type": r.source_type,
                "text": r.text,
                "is_duplicate": r.is_duplicate,
                "duplicate_group_id": r.duplicate_group_id,
            }
            for r in records
        ],
        "signals": [json.loads(s.raw_json) for s in signals if s.raw_json],
        "stress_runs": [json.loads(sr.raw_json) for sr in stress_runs if sr.raw_json],
    }

    return JSONResponse(
        content=payload,
        headers={"Content-Disposition": f'attachment; filename="sentinel_run_{run_id}.json"'},
    )
