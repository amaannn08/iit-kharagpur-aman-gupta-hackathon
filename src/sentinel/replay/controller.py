"""Replay run controller and state machine conforming to PRD Section 8."""

import asyncio
from datetime import datetime
from enum import Enum
from typing import Callable, Coroutine, List, Optional, Union
from uuid import uuid4

from pydantic import BaseModel, Field

from sentinel.contracts.records import InputRecord
from sentinel.contracts.signals import RiskSignal
from sentinel.replay.clock import LogicalClock, ReplaySpeed, sort_records_deterministically
from sentinel.replay.dedup import DedupDecision, ExactTextDeduplicator


class RunState(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    DRAINING = "draining"
    COMPLETED = "completed"
    FAILED = "failed"


class ReplayStatus(BaseModel):
    """Snapshot of replay controller status."""

    run_id: str
    scenario_id: Optional[str] = None
    state: RunState
    current_simulated_at: Optional[datetime] = None
    speed: float
    total_records: int
    pending_records: int
    in_flight: int
    processed_count: int
    duplicate_count: int
    error_count: int
    step_count: int


class ReplayStepResult(BaseModel):
    """Result returned after single record processed in replay."""

    record: InputRecord
    dedup: DedupDecision
    signal: Optional[RiskSignal] = None  # primary entity signal (backwards compatible)
    signals: List[RiskSignal] = Field(default_factory=list)  # one per resolved entity
    simulated_at: Optional[datetime] = None
    success: bool = True
    error_message: Optional[str] = None


RecordProcessor = Callable[
    [InputRecord, DedupDecision],
    Coroutine[None, None, Union[RiskSignal, List[RiskSignal], None]],
]


class ReplayController:
    """Manages replay runs, queue progression, pause/resume, and deduplication."""

    def __init__(
        self,
        max_queue_size: int = 10000,
        default_speed: ReplaySpeed = ReplaySpeed.REALTIME,
    ) -> None:
        self.max_queue_size = max_queue_size
        self._run_id: str = f"run-{uuid4().hex[:12]}"
        self._scenario_id: Optional[str] = None
        self._state: RunState = RunState.IDLE
        self._clock = LogicalClock(speed=default_speed)
        self._dedup = ExactTextDeduplicator()

        self._queue: List[InputRecord] = []
        self._total_records: int = 0
        self._processed_count: int = 0
        self._in_flight: int = 0
        self._error_count: int = 0

        self._run_task: Optional[asyncio.Task] = None
        self._pause_event = asyncio.Event()
        self._pause_event.set()  # Not paused by default

    @property
    def run_id(self) -> str:
        return self._run_id

    @property
    def state(self) -> RunState:
        return self._state

    @property
    def clock(self) -> LogicalClock:
        return self._clock

    @property
    def dedup(self) -> ExactTextDeduplicator:
        return self._dedup

    def get_status(self) -> ReplayStatus:
        return ReplayStatus(
            run_id=self._run_id,
            scenario_id=self._scenario_id,
            state=self._state,
            current_simulated_at=self._clock.current_time,
            speed=self._clock.speed,
            total_records=self._total_records,
            pending_records=len(self._queue),
            in_flight=self._in_flight,
            processed_count=self._processed_count,
            duplicate_count=self._dedup.total_duplicates,
            error_count=self._error_count,
            step_count=self._clock.step_count,
        )

    def load_scenario(self, scenario_id: str, records: List[InputRecord]) -> None:
        """Initialize or reset controller with a sorted set of scenario records."""
        if len(records) > self.max_queue_size:
            raise ValueError(
                f"Record count ({len(records)}) exceeds maximum bounded queue size "
                f"({self.max_queue_size})"
            )
        self.reset()
        self._scenario_id = scenario_id
        # Strict deterministic ordering
        self._queue = sort_records_deterministically(records)
        self._total_records = len(self._queue)
        self._state = RunState.IDLE

    def set_speed(self, speed: float) -> None:
        self._clock.set_speed(speed)

    def pause(self) -> None:
        """Pause replay progression."""
        if self._state == RunState.RUNNING:
            self._state = RunState.DRAINING
            self._pause_event.clear()
            self._state = RunState.PAUSED

    def resume(self) -> None:
        """Resume replay progression from PAUSED state."""
        if self._state == RunState.PAUSED:
            self._state = RunState.RUNNING
            self._pause_event.set()

    def reset(self) -> None:
        """Reset replay controller state, assign fresh run ID, clear queue and dedup."""
        if self._run_task and not self._run_task.done():
            self._run_task.cancel()
            self._run_task = None

        self._run_id = f"run-{uuid4().hex[:12]}"
        self._scenario_id = None
        self._state = RunState.IDLE
        self._clock.reset()
        self._dedup.reset()
        self._queue.clear()
        self._total_records = 0
        self._processed_count = 0
        self._in_flight = 0
        self._error_count = 0
        self._pause_event.set()

    async def step(
        self,
        processor: Optional[RecordProcessor] = None,
    ) -> Optional[ReplayStepResult]:
        """Advance exactly one record from the replay queue deterministically."""
        if not self._queue:
            if self._state == RunState.RUNNING:
                self._state = RunState.COMPLETED
            return None

        record = self._queue.pop(0)
        self._in_flight += 1

        try:
            # Advance logical clock
            sim_time = self._clock.advance_record(record)
            # Check deduplication
            dedup_decision = self._dedup.process(
                record.record_id, record.text, timestamp=record.simulated_at or record.published_at
            )

            # Invoke downstream processor if provided
            produced = await processor(record, dedup_decision) if processor else None
            signals = produced if isinstance(produced, list) else [produced] if produced else []

            self._processed_count += 1
            if not self._queue and self._state == RunState.RUNNING:
                self._state = RunState.COMPLETED

            return ReplayStepResult(
                record=record,
                dedup=dedup_decision,
                signal=signals[0] if signals else None,
                signals=signals,
                simulated_at=sim_time,
                success=True,
            )
        except Exception as exc:
            self._error_count += 1
            return ReplayStepResult(
                record=record,
                dedup=DedupDecision(
                    is_duplicate=False,
                    text_hash="",
                    duplicate_group_id="",
                    canonical_record_id=record.record_id,
                    occurrence_index=1,
                ),
                simulated_at=self._clock.current_time,
                success=False,
                error_message=str(exc),
            )
        finally:
            self._in_flight -= 1
