"""Manual text analysis endpoint."""

import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from sentinel.api.routes.replay import emit_signal, nlp_engine, replay_controller
from sentinel.contracts.records import InputRecord
from sentinel.contracts.signals import RiskSignal
from sentinel.contracts.stress import StressRunResult
from sentinel.nlp.cascade import CascadeEventClassifier
from sentinel.replay.dedup import ExactTextDeduplicator
from sentinel.storage.db import get_db
from sentinel.storage.repository import ReplayRepository

router = APIRouter(tags=["Analysis Engine"])

deduplicator = ExactTextDeduplicator()
cascade_classifier = CascadeEventClassifier()


class AnalyzeRequest(BaseModel):
    text: str = Field(..., min_length=5, description="Financial news headline or social post")
    source_type: str = Field("news", description="news or social")
    source_id: str = Field("manual_input", description="Identifier of input channel")
    run_id: Optional[str] = Field(None, description="Optional associated run ID")


class AnalyzeResponse(BaseModel):
    record: InputRecord
    signal: RiskSignal  # primary (first-mentioned) entity
    signals: List[RiskSignal] = Field(default_factory=list)  # one per resolved entity
    stress_run: Optional[StressRunResult] = None
    stress_runs: List[StressRunResult] = Field(default_factory=list)
    is_duplicate: bool
    duplicate_group_id: Optional[str] = None


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_manual_text(
    req: AnalyzeRequest,
    db: Session = Depends(get_db),
) -> AnalyzeResponse:
    """Analyze single financial news or social text through the offline pipeline."""
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

    repo = ReplayRepository(db)
    repo.save_record(record, dedup, run_id=run_id)
    signals = nlp_engine.process_record_multi(record=record, run_id=run_id, dedup_decision=dedup)
    stress_runs = [r for sig in signals if (r := await emit_signal(repo, record, sig))]

    return AnalyzeResponse(
        record=record,
        signal=signals[0],
        signals=signals,
        stress_run=stress_runs[0] if stress_runs else None,
        stress_runs=stress_runs,
        is_duplicate=dedup.is_duplicate,
        duplicate_group_id=dedup.duplicate_group_id if dedup.is_duplicate else None,
    )


@router.post("/analyze/cascade")
def analyze_cascade(req: AnalyzeRequest) -> dict:
    """Classify text through the cost-aware NLP cascade (Fast Tier 1 vs Deep Tier 2)."""
    res = cascade_classifier.classify(req.text)
    return {
        "text": req.text,
        "label": res.label,
        "confidence": res.confidence,
        "tier_used": res.tier_used,
        "routing_reason": res.routing_reason,
        "latency_ms": res.latency_ms,
        "stats": cascade_classifier.stats.to_dict(),
    }


@router.get("/analyze/cascade/stats")
def get_cascade_stats() -> dict:
    """Return cumulative cascade routing and verification statistics."""
    return cascade_classifier.stats.to_dict()

