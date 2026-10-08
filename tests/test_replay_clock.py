from datetime import datetime, timezone

import pytest

from sentinel.contracts.records import InputRecord, SourceType, TimestampQuality
from sentinel.replay.clock import (
    LogicalClock,
    ReplaySpeed,
    sort_records_deterministically,
)


def test_replay_speed_values():
    assert ReplaySpeed.REALTIME.value == 1.0
    assert ReplaySpeed.FAST.value == 5.0
    assert ReplaySpeed.MAX.value == 20.0


def test_clock_initialization_and_speed():
    t0 = datetime(2023, 3, 10, 9, 0, tzinfo=timezone.utc)
    clock = LogicalClock(initial_time=t0, speed=ReplaySpeed.FAST)
    assert clock.current_time == t0
    assert clock.speed == 5.0
    assert clock.step_count == 0

    clock.set_speed(20.0)
    assert clock.speed == 20.0

    with pytest.raises(ValueError, match="Replay speed must be positive"):
        clock.set_speed(0)


def test_clock_advance_and_monotonicity():
    t0 = datetime(2023, 3, 10, 9, 0, tzinfo=timezone.utc)
    t1 = datetime(2023, 3, 10, 9, 5, tzinfo=timezone.utc)
    t_past = datetime(2023, 3, 10, 8, 59, tzinfo=timezone.utc)

    clock = LogicalClock(initial_time=t0)
    clock.advance_to(t1)
    assert clock.current_time == t1
    assert clock.step_count == 1

    # Attempting to move backward must raise ValueError
    with pytest.raises(ValueError, match="cannot move backwards"):
        clock.advance_to(t_past)


def test_deterministic_record_ordering():
    r1 = InputRecord(
        record_id="rec-003",
        source_id="news_demo",
        source_type=SourceType.NEWS,
        text="News item three with later timestamp",
        simulated_at=datetime(2023, 3, 10, 10, 0, tzinfo=timezone.utc),
        sequence_number=3,
    )
    r2 = InputRecord(
        record_id="rec-001",
        source_id="news_demo",
        source_type=SourceType.NEWS,
        text="News item one with earlier timestamp",
        simulated_at=datetime(2023, 3, 10, 9, 0, tzinfo=timezone.utc),
        sequence_number=1,
    )
    r3 = InputRecord(
        record_id="rec-002",
        source_id="news_demo",
        source_type=SourceType.NEWS,
        text="News item two with same timestamp as rec-001 but higher sequence",
        simulated_at=datetime(2023, 3, 10, 9, 0, tzinfo=timezone.utc),
        sequence_number=2,
    )

    sorted_records = sort_records_deterministically([r1, r2, r3])
    assert [r.record_id for r in sorted_records] == ["rec-001", "rec-002", "rec-003"]


def test_clock_advance_record_with_missing_timestamps():
    clock = LogicalClock()
    r = InputRecord(
        record_id="rec-no-ts",
        source_id="manual",
        source_type=SourceType.MANUAL,
        text="Manual entry without publication timestamp",
        timestamp_quality=TimestampQuality.MISSING,
    )
    cur = clock.advance_record(r)
    assert cur is not None
    assert clock.step_count == 1
