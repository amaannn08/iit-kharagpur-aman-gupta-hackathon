"""Tests for exact-text hash deduplication (PRD Section 8.1)."""

from sentinel.replay.dedup import (
    ExactTextDeduplicator,
    compute_normalized_hash,
    normalize_text_for_dedup,
)


def test_normalize_text_invariance():
    t1 = "Federal Reserve signals rate hike of 50 bps! https://t.co/xyz123"
    t2 = "federal reserve signals rate hike of 50 bps   "
    assert normalize_text_for_dedup(t1) == normalize_text_for_dedup(t2)
    assert compute_normalized_hash(t1) == compute_normalized_hash(t2)


def test_normalize_text_preserves_cashtag():
    t = "Downgrade imminent for $FRB following depositor run"
    norm = normalize_text_for_dedup(t)
    assert "$frb" in norm


def test_deduplicator_canonical_and_duplicates():
    dedup = ExactTextDeduplicator()

    d1 = dedup.process("rec-1", "Moody's cuts rating on SVB Financial Group to Baa1.")
    assert not d1.is_duplicate
    assert d1.canonical_record_id == "rec-1"
    assert d1.occurrence_index == 1

    # Exact duplicate text with extra spaces and different casing
    d2 = dedup.process("rec-2", "  moody's cuts rating on svb financial group to baa1.  ")
    assert d2.is_duplicate
    assert d2.canonical_record_id == "rec-1"
    assert d2.occurrence_index == 2
    assert d2.duplicate_group_id == d1.duplicate_group_id

    # Distinct text
    d3 = dedup.process("rec-3", "Signature Bank seized by regulators in NY.")
    assert not d3.is_duplicate
    assert d3.canonical_record_id == "rec-3"
    assert d3.occurrence_index == 1
    assert d3.duplicate_group_id != d1.duplicate_group_id

    assert dedup.total_seen == 3
    assert dedup.total_unique == 2
    assert dedup.total_duplicates == 1


def test_deduplicator_reset():
    dedup = ExactTextDeduplicator()
    dedup.process("rec-1", "Some breaking financial headline")
    assert dedup.total_seen == 1

    dedup.reset()
    assert dedup.total_seen == 0
    assert dedup.total_unique == 0

    d = dedup.process("rec-2", "Some breaking financial headline")
    assert not d.is_duplicate
    assert d.canonical_record_id == "rec-2"
