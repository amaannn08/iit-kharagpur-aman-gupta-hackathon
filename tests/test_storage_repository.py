from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from sentinel.contracts.records import InputRecord, SourceType
from sentinel.replay.controller import ReplayStatus, RunState
from sentinel.replay.dedup import DedupDecision
from sentinel.storage.db import Base
from sentinel.storage.repository import ReplayRepository


def test_repository_run_and_record_lifecycle():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    repo = ReplayRepository(session)

    # 1. Upsert Run
    status = ReplayStatus(
        run_id="run-persist-1",
        scenario_id="svb_run_march2023",
        state=RunState.RUNNING,
        current_simulated_at=datetime(2023, 3, 10, 9, 30, tzinfo=timezone.utc),
        speed=5.0,
        total_records=10,
        pending_records=8,
        in_flight=0,
        processed_count=2,
        duplicate_count=1,
        error_count=0,
        step_count=2,
    )
    run_model = repo.upsert_run(status)
    assert run_model.run_id == "run-persist-1"
    assert run_model.status == "running"
    assert run_model.duplicate_count == 1

    # 2. Save Canonical Record
    r1 = InputRecord(
        record_id="rec-001",
        source_id="news_demo",
        source_type=SourceType.NEWS,
        text="SVB Financial shares plummet 60% following loss on securities portfolio.",
        simulated_at=datetime(2023, 3, 10, 9, 0, tzinfo=timezone.utc),
        sequence_number=1,
    )
    d1 = DedupDecision(
        is_duplicate=False,
        text_hash="hash-1",
        duplicate_group_id="dup-hash-1",
        canonical_record_id="rec-001",
        occurrence_index=1,
    )
    rec1 = repo.save_record(r1, d1, run_id="run-persist-1")
    assert rec1.record_id == "rec-001"
    assert not rec1.is_duplicate
    assert rec1.canonical_record_id == "rec-001"

    # 3. Save Duplicate Record
    r2 = InputRecord(
        record_id="rec-002",
        source_id="social_demo",
        source_type=SourceType.SOCIAL,
        text="svb financial shares plummet 60% following loss on securities portfolio",
        simulated_at=datetime(2023, 3, 10, 9, 15, tzinfo=timezone.utc),
        sequence_number=2,
    )
    d2 = DedupDecision(
        is_duplicate=True,
        text_hash="hash-1",
        duplicate_group_id="dup-hash-1",
        canonical_record_id="rec-001",
        occurrence_index=2,
    )
    rec2 = repo.save_record(r2, d2, run_id="run-persist-1")
    assert rec2.record_id == "rec-002"
    assert rec2.is_duplicate
    assert rec2.canonical_record_id == "rec-001"
    assert rec2.duplicate_group_id == "dup-hash-1"

    # 4. Query records for run
    recs = repo.get_records_for_run("run-persist-1")
    assert len(recs) == 2
    assert recs[0].record_id == "rec-001"
    assert recs[1].record_id == "rec-002"

    session.close()
