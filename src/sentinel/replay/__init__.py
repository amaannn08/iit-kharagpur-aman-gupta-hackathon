"""Deterministic replay and deduplication engine for S&P Sentinel."""

from sentinel.replay.clock import (
    LogicalClock,
    ReplaySpeed,
    record_sort_key,
    sort_records_deterministically,
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
    "ReplaySpeed",
    "compute_normalized_hash",
    "normalize_text_for_dedup",
    "record_sort_key",
    "sort_records_deterministically",
]
