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


WIRE_NOISE_TOKENS = {
    "breaking",
    "update",
    "via",
    "reuters",
    "bloomberg",
    "ap",
    "dow",
    "jones",
    "alert",
    "urgent",
    "flash",
    "news",
    "exclusive",
    "report",
}


def extract_content_tokens(text: str) -> set:
    """Extract informative lowercased tokens excluding common wire lead-in words."""
    norm = normalize_text_for_dedup(text)
    raw_tokens = set(re.findall(r"\b[a-z0-9$]{2,}\b", norm))
    filtered = raw_tokens - WIRE_NOISE_TOKENS
    return filtered if len(filtered) >= 3 else raw_tokens


@dataclass(frozen=True)
class DedupDecision:
    """Result of checking a record against the deduplication registry."""

    is_duplicate: bool
    text_hash: str
    duplicate_group_id: str
    canonical_record_id: str
    occurrence_index: int
    match_type: str = "exact"  # "exact", "near_duplicate", "unique"


class ExactTextDeduplicator:
    """Hybrid exact-hash and token Jaccard deduplicator tracking duplicates across a replay run."""

    def __init__(self, jaccard_threshold: float = 0.75) -> None:
        # text_hash -> (canonical_record_id, total_seen_count)
        self._registry: Dict[str, Tuple[str, int]] = {}
        # List of (canonical_record_id, content_tokens, duplicate_group_id)
        self._canonical_tokens: list = []
        self.jaccard_threshold = jaccard_threshold

    def process(self, record_id: str, text: str) -> DedupDecision:
        """Check if text is exact duplicate or syndicated near-duplicate.

        First observation becomes canonical. Subsequent identical or syndicated variant texts
        are flagged as duplicates with duplicate_group_id pointing to the canonical entry.
        """
        thash = compute_normalized_hash(text)
        group_id = f"dup-{thash[:16]}"

        # 1. Exact hash check
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
                match_type="exact",
            )

        # 2. Near-duplicate check via token Jaccard and containment similarity
        # (handles wire syndication and quotes)
        content_tokens = extract_content_tokens(text)
        if len(content_tokens) >= 4:
            for can_id, can_tokens, can_group in self._canonical_tokens:
                intersection = len(content_tokens & can_tokens)
                union = len(content_tokens | can_tokens)
                min_len = min(len(content_tokens), len(can_tokens))
                jaccard = intersection / union if union > 0 else 0.0
                containment = intersection / min_len if min_len > 0 else 0.0

                if (jaccard >= self.jaccard_threshold) or (
                    containment >= 0.85 and intersection >= 4
                ):
                    # Register this hash as an alias to canonical
                    self._registry[thash] = (can_id, 2)
                    return DedupDecision(
                        is_duplicate=True,
                        text_hash=thash,
                        duplicate_group_id=can_group,
                        canonical_record_id=can_id,
                        occurrence_index=2,
                        match_type="near_duplicate",
                    )

        # First time seen -> canonical record
        self._registry[thash] = (record_id, 1)
        self._canonical_tokens.append((record_id, content_tokens, group_id))
        return DedupDecision(
            is_duplicate=False,
            text_hash=thash,
            duplicate_group_id=group_id,
            canonical_record_id=record_id,
            occurrence_index=1,
            match_type="unique",
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
        self._canonical_tokens.clear()
