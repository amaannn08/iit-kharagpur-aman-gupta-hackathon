"""Data access repository for runs, records, signals, and audit lineage."""

from typing import TYPE_CHECKING, List, Optional

from sqlalchemy.orm import Session

from sentinel.contracts.records import InputRecord
from sentinel.replay.controller import ReplayStatus
from sentinel.replay.dedup import DedupDecision
from sentinel.storage.models import RecordModel, RunModel, SignalModel, StressRunModel

if TYPE_CHECKING:
    from sentinel.contracts.signals import RiskSignal
    from sentinel.contracts.stress import StressRunResult



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

    def save_signal(self, signal: "RiskSignal") -> SignalModel:
        """Store emitted RiskSignal and its JSON contract in SQLite."""
        import json

        sig_model = SignalModel(
            signal_id=signal.signal_id,
            run_id=signal.run_id,
            record_id=signal.record_id,
            entity_name=signal.entity.name,
            entity_ticker=signal.entity.ticker,
            sentiment_score=signal.sentiment.score,
            sentiment_label=signal.sentiment.label,
            event_label=signal.event.label,
            event_confidence=signal.event.confidence,
            impact_score=signal.impact.score,
            processed_at=signal.processed_at,
            duplicate_group_id=signal.duplicate_group_id,
            eligible_for_action=signal.eligible_for_action,
            action_block_reasons=",".join(signal.action_block_reasons),
            raw_json=json.dumps(signal.model_dump(mode="json")),
        )
        self.session.add(sig_model)
        self.session.commit()
        self.session.refresh(sig_model)
        return sig_model

    def get_signals_for_run(self, run_id: str) -> List[SignalModel]:
        return (
            self.session.query(SignalModel)
            .filter_by(run_id=run_id)
            .order_by(SignalModel.processed_at.asc())
            .all()
        )

    def get_signal(self, signal_id: str) -> Optional[SignalModel]:
        return self.session.query(SignalModel).filter_by(signal_id=signal_id).first()

    def list_signals(self, limit: int = 50) -> List[SignalModel]:
        return (
            self.session.query(SignalModel)
            .order_by(SignalModel.processed_at.desc())
            .limit(limit)
            .all()
        )

    def save_stress_run(self, result: "StressRunResult") -> StressRunModel:
        """Store executed StressRunResult in SQLite with JSON contract."""
        import json
        from datetime import datetime

        stress_model = StressRunModel(
            stress_id=result.stress_id,
            run_id=result.run_id,
            scenario_id=result.target_scope,
            trigger_signal_id=result.trigger_signal_id,
            baseline_value_usd=result.baseline_total_book_value_usd,
            stressed_value_usd=result.stressed_total_book_value_usd,
            total_loss_usd=result.total_pnl_usd,
            executed_at=datetime.fromisoformat(result.executed_at),
            raw_json=json.dumps(result.model_dump(mode="json")),
        )
        self.session.add(stress_model)
        self.session.commit()
        self.session.refresh(stress_model)
        return stress_model

    def get_stress_run(self, stress_id: str) -> Optional[StressRunModel]:
        return self.session.query(StressRunModel).filter_by(stress_id=stress_id).first()

    def list_stress_runs(
        self, run_id: Optional[str] = None, limit: int = 50
    ) -> List[StressRunModel]:
        query = self.session.query(StressRunModel)

        if run_id:
            query = query.filter_by(run_id=run_id)
        return query.order_by(StressRunModel.executed_at.desc()).limit(limit).all()

