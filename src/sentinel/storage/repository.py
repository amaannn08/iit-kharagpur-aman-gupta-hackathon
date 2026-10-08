"""Data access repository for runs, records, signals, and audit lineage."""

from typing import List, Optional

from sqlalchemy.orm import Session

from sentinel.contracts.records import InputRecord
from sentinel.replay.controller import ReplayStatus
from sentinel.replay.dedup import DedupDecision
from sentinel.storage.models import RecordModel, RunModel


class ReplayRepository:
    """Encapsulates persistence operations for replay runs and records."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def upsert_run(self, status: ReplayStatus) -> RunModel:
        """Create or update a replay run record in SQLite."""
        run = self.session.query(RunModel).filter_by(run_id=status.run_id).first()
        if not run:
            run = RunModel(
                run_id=status.run_id,
                scenario_id=status.scenario_id,
                status=status.state.value,
                speed=status.speed,
                current_simulated_at=status.current_simulated_at,
                total_records=status.total_records,
                processed_records=status.processed_count,
                duplicate_count=status.duplicate_count,
                error_count=status.error_count,
            )
            self.session.add(run)
        else:
            run.status = status.state.value
            run.speed = status.speed
            run.current_simulated_at = status.current_simulated_at
            run.total_records = status.total_records
            run.processed_records = status.processed_count
            run.duplicate_count = status.duplicate_count
            run.error_count = status.error_count

        self.session.commit()
        self.session.refresh(run)
        return run

    def save_record(
        self,
        record: InputRecord,
        dedup: DedupDecision,
        run_id: Optional[str] = None,
    ) -> RecordModel:
        """Store ingested record along with its deduplication audit state."""
        existing = (
            self.session.query(RecordModel)
            .filter_by(record_id=record.record_id, run_id=run_id)
            .first()
        )
        if existing:
            return existing

        rec_model = RecordModel(
            record_id=record.record_id,
            run_id=run_id,
            source_id=record.source_id,
            source_type=record.source_type.value,
            text=record.text,
            sequence_number=record.sequence_number,
            published_at=record.published_at,
            simulated_at=record.simulated_at,
            is_synthetic=record.is_synthetic,
            is_duplicate=dedup.is_duplicate,
            duplicate_group_id=dedup.duplicate_group_id,
            canonical_record_id=dedup.canonical_record_id,
        )
        self.session.add(rec_model)
        self.session.commit()
        self.session.refresh(rec_model)
        return rec_model

    def get_run(self, run_id: str) -> Optional[RunModel]:
        return self.session.query(RunModel).filter_by(run_id=run_id).first()

    def list_runs(self) -> List[RunModel]:
        return self.session.query(RunModel).order_by(RunModel.created_at.desc()).all()

    def get_records_for_run(self, run_id: str) -> List[RecordModel]:
        return (
            self.session.query(RecordModel)
            .filter_by(run_id=run_id)
            .order_by(RecordModel.sequence_number.asc())
            .all()
        )
