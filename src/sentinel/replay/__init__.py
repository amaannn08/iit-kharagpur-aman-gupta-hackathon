"""Deterministic replay and deduplication engine for S&P Sentinel."""

from sentinel.replay.clock import (
    LogicalClock,
    ReplaySpeed,
    record_sort_key,
    sort_records_deterministically,
)

__all__ = [
    "LogicalClock",
    "ReplaySpeed",
    "record_sort_key",
    "sort_records_deterministically",
]
