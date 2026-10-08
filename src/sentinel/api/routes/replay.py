"""Replay control and run inspection API endpoints (PRD Section 8 & 16 M2)."""

from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from sentinel.contracts.records import InputRecord
from sentinel.ingestion.adapters import NewsAdapter, SocialAdapter
from sentinel.replay.controller import (
    ReplayController,
    ReplayStatus,
    ReplayStepResult,
)
from sentinel.storage.db import get_db
from sentinel.storage.repository import ReplayRepository

router = APIRouter(prefix="/replay", tags=["Replay Controller"])

# Singleton controller instance for backend runtime
replay_controller = ReplayController()


class LoadScenarioRequest(BaseModel):
    scenario_id: str
    sources: List[str] = ["news_demo", "social_demo"]


class SetSpeedRequest(BaseModel):
    speed: float


class PersistedRunResponse(BaseModel):
    run_id: str
    scenario_id: Optional[str]
    status: str
    speed: float
    total_records: int
    processed_records: int
    duplicate_count: int
    error_count: int


class PersistedRecordResponse(BaseModel):
    record_id: str
    source_id: str
    source_type: str
    text: str
    is_duplicate: bool
    duplicate_group_id: Optional[str]
    canonical_record_id: Optional[str]
    sequence_number: Optional[int]


@router.get("/status", response_model=ReplayStatus)
def get_replay_status() -> ReplayStatus:
    """Return live status of the logical replay clock and run queue."""
    return replay_controller.get_status()


@router.post("/load", response_model=ReplayStatus)
def load_replay_scenario(
    req: LoadScenarioRequest,
    db: Session = Depends(get_db),
) -> ReplayStatus:
    """Load scenario records into the bounded replay queue."""
    repo = ReplayRepository(db)
    all_records: List[InputRecord] = []
    base_data_dir = Path("data")

    if "news_demo" in req.sources:
        news_file = base_data_dir / "news_demo.csv"
        if news_file.exists():
            all_records.extend(NewsAdapter.load_from_csv(news_file))

    if "social_demo" in req.sources:
        social_file = base_data_dir / "social_demo.csv"
        if social_file.exists():
            all_records.extend(SocialAdapter.load_from_csv(social_file))

    if not all_records:
        raise HTTPException(
            status_code=400,
            detail="No records found for specified sources in data/ directory.",
        )

    replay_controller.load_scenario(req.scenario_id, all_records)
    status = replay_controller.get_status()
    repo.upsert_run(status)
    return status


@router.post("/step", response_model=Optional[ReplayStepResult])
async def step_replay(
    db: Session = Depends(get_db),
) -> Optional[ReplayStepResult]:
    """Deterministically advance one record from the replay queue."""
    repo = ReplayRepository(db)

    async def persist_step(record: InputRecord, dedup):
        repo.save_record(record, dedup, run_id=replay_controller.run_id)

    step_result = await replay_controller.step(processor=persist_step)
    repo.upsert_run(replay_controller.get_status())
    return step_result


@router.post("/pause", response_model=ReplayStatus)
def pause_replay(db: Session = Depends(get_db)) -> ReplayStatus:
    """Pause replay execution."""
    replay_controller.pause()
    status = replay_controller.get_status()
    ReplayRepository(db).upsert_run(status)
    return status


@router.post("/resume", response_model=ReplayStatus)
def resume_replay(db: Session = Depends(get_db)) -> ReplayStatus:
    """Resume replay execution."""
    replay_controller.resume()
    status = replay_controller.get_status()
    ReplayRepository(db).upsert_run(status)
    return status


@router.post("/reset", response_model=ReplayStatus)
def reset_replay(db: Session = Depends(get_db)) -> ReplayStatus:
    """Reset replay controller, clear queue, and assign a clean run ID."""
    replay_controller.reset()
    status = replay_controller.get_status()
    ReplayRepository(db).upsert_run(status)
    return status


@router.post("/speed", response_model=ReplayStatus)
def set_replay_speed(
    req: SetSpeedRequest,
    db: Session = Depends(get_db),
) -> ReplayStatus:
    """Configure logical clock replay speed (e.g. 1.0, 5.0, 20.0)."""
    if req.speed <= 0:
        raise HTTPException(status_code=400, detail="Speed must be positive")
    replay_controller.set_speed(req.speed)
    status = replay_controller.get_status()
    ReplayRepository(db).upsert_run(status)
    return status


@router.get("/runs", response_model=List[PersistedRunResponse])
def list_persisted_runs(db: Session = Depends(get_db)) -> List[PersistedRunResponse]:
    """List historical replay runs persisted in SQLite."""
    runs = ReplayRepository(db).list_runs()
    return [
        PersistedRunResponse(
            run_id=r.run_id,
            scenario_id=r.scenario_id,
            status=r.status,
            speed=r.speed,
            total_records=r.total_records,
            processed_records=r.processed_records,
            duplicate_count=r.duplicate_count,
            error_count=r.error_count,
        )
        for r in runs
    ]


@router.get("/runs/{run_id}/records", response_model=List[PersistedRecordResponse])
def get_run_records(
    run_id: str,
    db: Session = Depends(get_db),
) -> List[PersistedRecordResponse]:
    """Retrieve audit trail of records processed in a run including deduplication."""
    recs = ReplayRepository(db).get_records_for_run(run_id)
    return [
        PersistedRecordResponse(
            record_id=r.record_id,
            source_id=r.source_id,
            source_type=r.source_type,
            text=r.text,
            is_duplicate=r.is_duplicate,
            duplicate_group_id=r.duplicate_group_id,
            canonical_record_id=r.canonical_record_id,
            sequence_number=r.sequence_number,
        )
        for r in recs
    ]
