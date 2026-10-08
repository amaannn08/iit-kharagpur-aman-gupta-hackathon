"""Manual text analysis endpoint conforming to PRD Section 11.1 & 12."""

import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from sentinel.api.events import broadcaster
from sentinel.api.routes.replay import nlp_engine, replay_controller
from sentinel.api.routes.stress import stress_engine
from sentinel.contracts.records import InputRecord
from sentinel.contracts.signals import RiskSignal
from sentinel.contracts.stress import StressRunResult
from sentinel.replay.dedup import ExactTextDeduplicator
from sentinel.storage.db import get_db
from sentinel.storage.repository import ReplayRepository

router = APIRouter(tags=["Analysis Engine"])

deduplicator = ExactTextDeduplicator()


class AnalyzeRequest(BaseModel):
    text: str = Field(..., min_length=5, description="Financial news headline or social post")
    source_type: str = Field("news", description="news or social")
    source_id: str = Field("manual_input", description="Identifier of input channel")
    run_id: Optional[str] = Field(None, description="Optional associated run ID")


class AnalyzeResponse(BaseModel):
    record: InputRecord
    signal: RiskSignal
    stress_run: Optional[StressRunResult] = None
    is_duplicate: bool
    duplicate_group_id: Optional[str] = None


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_manual_text(
    req: AnalyzeRequest,
    db: Session = Depends(get_db),
) -> AnalyzeResponse:
    """Analyze single financial news or social text through the offline pipeline (PRD 12)."""
    text_clean = req.text.strip()

    if not text_clean:
        raise HTTPException(status_code=400, detail="Text must not be empty or blank.")

    run_id = req.run_id or replay_controller.run_id
    record_id = f"manual-{uuid.uuid4().hex[:10]}"
    now = datetime.utcnow()

    record = InputRecord(
        record_id=record_id,
        source_id=req.source_id,
        source_type=req.source_type,
        text=text_clean,
        published_at=now,
        timestamp_quality="original",
        simulated_at=now,
        is_synthetic=False,
    )

    dedup = deduplicator.process(record_id=record.record_id, text=record.text)

    # Execute learned NLP pipeline
    sig = nlp_engine.process_record(
        record=record,
        run_id=run_id,
        dedup_decision=dedup,
    )

    repo = ReplayRepository(db)
    repo.save_record(record, dedup, run_id=run_id)
    repo.save_signal(sig)

    # Evaluate automated stress trigger
    stress_res: Optional[StressRunResult] = None
    if stress_engine.should_trigger(sig):
        stress_res = stress_engine.trigger_from_signal(sig)
        if stress_res:
            repo.save_stress_run(stress_res)

    # Broadcast to live SSE stream
    await broadcaster.broadcast(
        event_type="signal_emitted",
        data={
            "signal": sig.model_dump(mode="json"),
            "record": record.model_dump(mode="json"),
            "stress_run": stress_res.model_dump(mode="json") if stress_res else None,
        },
    )

    return AnalyzeResponse(
        record=record,
        signal=sig,
        stress_run=stress_res,
        is_duplicate=dedup.is_duplicate,
        duplicate_group_id=dedup.duplicate_group_id if dedup.is_duplicate else None,
    )
