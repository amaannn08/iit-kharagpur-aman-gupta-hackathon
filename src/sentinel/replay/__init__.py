"""Deterministic replay and deduplication engine for S&P Sentinel."""

from sentinel.replay.clock import (
    LogicalClock,
    ReplaySpeed,
    record_sort_key,
    sort_records_deterministically,
)
from sentinel.replay.controller import (
    RecordProcessor,
    ReplayController,
    ReplayStatus,
    ReplayStepResult,
    RunState,
)
from sentinel.replay.dedup import (
    DedupDecision,
    ExactTextDeduplicator,
    compute_normalized_hash,
    normalize_text_for_dedup,
)

__all__ = [
    "DedupDecision",
    "ExactTextDeduplicator",
    "LogicalClock",
    "RecordProcessor",
    "ReplayController",
    "ReplaySpeed",
    "ReplayStatus",
    "ReplayStepResult",
    "RunState",
    "compute_normalized_hash",
    "normalize_text_for_dedup",
    "record_sort_key",
    "sort_records_deterministically",
]
