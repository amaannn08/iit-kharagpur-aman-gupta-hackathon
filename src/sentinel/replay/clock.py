"""Logical replay clock and deterministic ordering for S&P Sentinel."""

from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional, Tuple

from sentinel.contracts.records import InputRecord


class ReplaySpeed(float, Enum):
    REALTIME = 1.0
    FAST = 5.0
    MAX = 20.0


def record_sort_key(record: InputRecord) -> Tuple[datetime, int, str]:
    """Deterministic tie-breaking key for input records.

    Order:
      1. simulated_at (or published_at, or epoch if missing)
      2. sequence_number (or 0 if missing)
      3. record_id (guarantees strict deterministic total ordering)
    """
    epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)
    ts = record.simulated_at or record.published_at
    if ts is None:
        ts = epoch
    elif ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)

    seq = record.sequence_number if record.sequence_number is not None else 0
    return (ts, seq, record.record_id)


def sort_records_deterministically(records: List[InputRecord]) -> List[InputRecord]:
    """Sort a list of InputRecords into strict deterministic replay order."""
    return sorted(records, key=record_sort_key)


class LogicalClock:
    """Logical clock tracking simulated replay time with configurable speed."""

    def __init__(
        self,
        initial_time: Optional[datetime] = None,
        speed: ReplaySpeed = ReplaySpeed.REALTIME,
    ) -> None:
        self._current_time: Optional[datetime] = (
            initial_time.replace(tzinfo=timezone.utc)
            if initial_time and initial_time.tzinfo is None
            else initial_time
        )
        self._speed: float = float(speed.value if isinstance(speed, ReplaySpeed) else speed)
        self._step_count: int = 0

    @property
    def current_time(self) -> Optional[datetime]:
        return self._current_time

    @property
    def speed(self) -> float:
        return self._speed

    @property
    def step_count(self) -> int:
        return self._step_count

    def set_speed(self, speed: float) -> None:
        if speed <= 0:
            raise ValueError(f"Replay speed must be positive, got {speed}")
        self._speed = float(speed)

    def advance_to(self, target_time: datetime) -> None:
        """Advance the logical clock forward to target_time.

        Monotonicity is enforced: target_time cannot be behind current_time.
        """
        if target_time.tzinfo is None:
            target_time = target_time.replace(tzinfo=timezone.utc)

        if self._current_time is not None and target_time < self._current_time:
            raise ValueError(
                f"Clock cannot move backwards: target {target_time.isoformat()} < "
                f"current {self._current_time.isoformat()}"
            )
        self._current_time = target_time
        self._step_count += 1

    def advance_record(self, record: InputRecord) -> datetime:
        """Advance the logical clock based on the incoming record's timestamp."""
        ts = record.simulated_at or record.published_at
        if ts is None:
            # Synthetic sequence time advancement when timestamp missing
            if self._current_time is None:
                ts = datetime(2023, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
            else:
                from datetime import timedelta

                ts = self._current_time + timedelta(seconds=1)
        elif ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)

        if self._current_time is None or ts > self._current_time:
            self.advance_to(ts)
        else:
            self._step_count += 1
        return self._current_time

    def reset(self, initial_time: Optional[datetime] = None) -> None:
        self._current_time = (
            initial_time.replace(tzinfo=timezone.utc)
            if initial_time and initial_time.tzinfo is None
            else initial_time
        )
        self._step_count = 0
