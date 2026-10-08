"""Risk signals inspection API endpoints (PRD Section 6.2)."""

import json
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from sentinel.contracts.signals import RiskSignal
from sentinel.storage.db import get_db
from sentinel.storage.repository import ReplayRepository

router = APIRouter(prefix="/signals", tags=["Risk Signals"])


@router.get("", response_model=List[Dict[str, Any]])
def list_latest_signals(
    limit: int = Query(default=50, ge=1, le=500),
    db: Session = Depends(get_db),
) -> List[Dict[str, Any]]:
    """Return latest emitted risk signals across replay runs."""
    repo = ReplayRepository(db)
    models = repo.list_signals(limit=limit)
    results = []
    for m in models:
        if m.raw_json:
            results.append(json.loads(m.raw_json))
        else:
            results.append({
                "signal_id": m.signal_id,
                "run_id": m.run_id,
                "record_id": m.record_id,
                "entity": {"name": m.entity_name, "ticker": m.entity_ticker},
                "sentiment": {"score": m.sentiment_score, "label": m.sentiment_label},
                "event": {"label": m.event_label, "confidence": m.event_confidence},
                "impact": {"score": m.impact_score},
                "eligible_for_action": m.eligible_for_action,
            })
    return results


@router.get("/{signal_id}", response_model=RiskSignal)
def get_signal_by_id(
    signal_id: str,
    db: Session = Depends(get_db),
) -> RiskSignal:
    """Retrieve full structured RiskSignal contract by ID."""
    repo = ReplayRepository(db)
    sig_model = repo.get_signal(signal_id)
    if not sig_model or not sig_model.raw_json:
        raise HTTPException(status_code=404, detail=f"RiskSignal {signal_id} not found.")

    payload = json.loads(sig_model.raw_json)
    return RiskSignal.model_validate(payload)


@router.get("/run/{run_id}", response_model=List[Dict[str, Any]])
def get_signals_by_run(
    run_id: str,
    db: Session = Depends(get_db),
) -> List[Dict[str, Any]]:
    """Retrieve all signals emitted during a specific replay run."""
    repo = ReplayRepository(db)
    models = repo.get_signals_for_run(run_id)
    return [json.loads(m.raw_json) for m in models if m.raw_json]
