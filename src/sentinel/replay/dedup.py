"""Exact normalized-text hash deduplication for financial streaming text (PRD Section 8.1)."""

import hashlib
import re
from dataclasses import dataclass
from typing import Dict, Tuple


def normalize_text_for_dedup(text: str) -> str:
    """Normalize text by stripping URLs, lowercasing, and collapsing whitespace.

    Keeps alphanumeric characters and essential punctuation for financial tickers/symbols ($),
    while neutralizing incidental whitespace and case differences.
    """
    # Remove URLs
    cleaned = re.sub(r"https?://\S+|www\.\S+", "", text)
    # Lowercase
    cleaned = cleaned.lower()
    # Replace non-alphanumeric (except $ for cashtags) with single space
    cleaned = re.sub(r"[^\w\$]+", " ", cleaned)
    # Collapse multiple whitespace characters
    cleaned = " ".join(cleaned.split())
    return cleaned.strip()


def compute_normalized_hash(text: str) -> str:
    """Return 64-char SHA-256 hash of normalized text."""
    norm = normalize_text_for_dedup(text)
    return hashlib.sha256(norm.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class DedupDecision:
    """Result of checking a record against the deduplication registry."""

    is_duplicate: bool
    text_hash: str
    duplicate_group_id: str
    canonical_record_id: str
    occurrence_index: int


class ExactTextDeduplicator:
    """In-memory exact-hash deduplicator tracking duplicates across a replay run."""

    def __init__(self) -> None:
        # text_hash -> (canonical_record_id, total_seen_count)
        self._registry: Dict[str, Tuple[str, int]] = {}

    def process(self, record_id: str, text: str) -> DedupDecision:
        """Check if text is duplicate.

        First observation becomes canonical. Subsequent identical texts are flagged
        as duplicates with duplicate_group_id pointing to the canonical entry.
        """
        thash = compute_normalized_hash(text)
        group_id = f"dup-{thash[:16]}"

        if thash in self._registry:
            canonical_id, count = self._registry[thash]
            new_count = count + 1
            self._registry[thash] = (canonical_id, new_count)
            return DedupDecision(
                is_duplicate=True,
                text_hash=thash,
                duplicate_group_id=group_id,
                canonical_record_id=canonical_id,
                occurrence_index=new_count,
            )

        # First time seen -> canonical record
        self._registry[thash] = (record_id, 1)
        return DedupDecision(
            is_duplicate=False,
            text_hash=thash,
            duplicate_group_id=group_id,
            canonical_record_id=record_id,
            occurrence_index=1,
        )

    def is_known(self, text: str) -> bool:
        thash = compute_normalized_hash(text)
        return thash in self._registry

    @property
    def total_unique(self) -> int:
        return len(self._registry)

    @property
    def total_seen(self) -> int:
        return sum(count for _, count in self._registry.values())

    @property
    def total_duplicates(self) -> int:
        return self.total_seen - self.total_unique

    def reset(self) -> None:
        """Clear deduplication state for a new run."""
        self._registry.clear()
