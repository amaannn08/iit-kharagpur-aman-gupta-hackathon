"""Syndication-aware deduplication for financial streaming text (PRD Section 8.1).

1. Exact match on the SHA-256 of normalized text.
2. Near-duplicates (wire syndication, quote re-posts): MinHash-LSH retrieves a small candidate
   set, then exact token Jaccard (>= 0.75) or containment (>= 0.85, >= 4 shared tokens) decides.
   Each record is indexed twice, by its full text and by its lead (first sentence), so a tweet
   re-posting an article headline (Jaccard 0.24 but containment 0.91) is still retrieved.
   This replaces a linear scan over every earlier record (100k records took over an hour).
3. A sliding time window (default 24 h of record time) evicts old entries, so the index stays
   bounded on long replays and a story repeated days later is treated as new.
"""

import hashlib
import re
from collections import Counter, deque
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Deque, Dict, Optional, Set, Tuple

from datasketch import MinHash, MinHashLSH


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


def lead_sentence(text: str) -> str:
    """Headline-sized lead of a record: text up to the first sentence break."""
    return re.split(r"(?<=[.!?])\s+|\n", text.strip(), maxsplit=1)[0]


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
    """Exact-hash + MinHash-LSH near-duplicate detector over a sliding time window."""

    LSH_CANDIDATE_THRESHOLD = 0.5  # recall-oriented retrieval; verification below decides
    NUM_PERM = 64

    def __init__(self, jaccard_threshold: float = 0.75, window_hours: float = 24.0) -> None:
        self.jaccard_threshold = jaccard_threshold
        self.containment_threshold = 0.85
        self.window = timedelta(hours=window_hours)
        # Generating permutations dominated runtime (53%) when done per record: build once.
        template = MinHash(num_perm=self.NUM_PERM, seed=1)
        self._permutations, self._scheme = template.permutations, template.scheme
        self.reset()

    def reset(self) -> None:
        """Clear deduplication state for a new run."""
        self._lsh = MinHashLSH(threshold=self.LSH_CANDIDATE_THRESHOLD, num_perm=self.NUM_PERM)
        self._lsh_keys: Set[str] = set()
        self._exact: Dict[str, str] = {}  # text hash -> canonical record id
        # canonical record id -> (content tokens, duplicate group id, text hash)
        self._canonical: Dict[str, Tuple[Set[str], str, str]] = {}
        self._queue: Deque[Tuple[Optional[datetime], str]] = deque()
        self._group_counts: Counter = Counter()
        self._seen = 0
        self._duplicates = 0

    def _evict(self, now: Optional[datetime]) -> None:
        if now is None:
            return
        while (
            self._queue and self._queue[0][0] is not None and now - self._queue[0][0] > self.window
        ):
            _, rec_id = self._queue.popleft()
            _, _, thash = self._canonical.pop(rec_id)
            for key in (f"{rec_id}|full", f"{rec_id}|lead"):
                if key in self._lsh_keys:  # short texts (< 4 tokens) are exact-match only
                    self._lsh_keys.discard(key)
                    self._lsh.remove(key)
            self._exact.pop(thash, None)

    def _minhash(self, tokens: Set[str]) -> MinHash:
        m = MinHash(
            num_perm=self.NUM_PERM, seed=1, permutations=self._permutations, scheme=self._scheme
        )
        m.update_batch([tok.encode("utf-8") for tok in tokens])
        return m

    def _duplicate(self, thash: str, canonical_id: str, match_type: str) -> DedupDecision:
        _, group_id, _ = self._canonical[canonical_id]
        self._group_counts[group_id] += 1
        self._duplicates += 1
        return DedupDecision(
            is_duplicate=True,
            text_hash=thash,
            duplicate_group_id=group_id,
            canonical_record_id=canonical_id,
            occurrence_index=self._group_counts[group_id],
            match_type=match_type,
        )

    def process(
        self, record_id: str, text: str, timestamp: Optional[datetime] = None
    ) -> DedupDecision:
        """First observation becomes canonical; later identical or syndicated copies within the
        window are flagged with duplicate_group_id pointing to the canonical entry."""
        self._seen += 1
        self._evict(timestamp)
        thash = compute_normalized_hash(text)

        if thash in self._exact:
            return self._duplicate(thash, self._exact[thash], "exact")

        tokens = extract_content_tokens(text)
        lead = extract_content_tokens(lead_sentence(text))
        if len(tokens) >= 4:
            keys = set(self._lsh.query(self._minhash(tokens)))
            if len(lead) >= 4:
                keys |= set(self._lsh.query(self._minhash(lead)))
            for cand in sorted({k.rsplit("|", 1)[0] for k in keys}):
                cand_tokens = self._canonical[cand][0]
                inter = len(tokens & cand_tokens)
                jaccard = inter / len(tokens | cand_tokens)
                containment = inter / min(len(tokens), len(cand_tokens))
                if jaccard >= self.jaccard_threshold or (
                    containment >= self.containment_threshold and inter >= 4
                ):
                    return self._duplicate(thash, cand, "near_duplicate")

        group_id = f"dup-{thash[:16]}"
        self._exact[thash] = record_id
        self._canonical[record_id] = (tokens, group_id, thash)
        for kind, toks in (("full", tokens), ("lead", lead)):
            if len(toks) >= 4 and (kind == "full" or toks != tokens):
                key = f"{record_id}|{kind}"
                self._lsh.insert(key, self._minhash(toks))
                self._lsh_keys.add(key)
        self._queue.append((timestamp, record_id))
        self._group_counts[group_id] = 1
        return DedupDecision(
            is_duplicate=False,
            text_hash=thash,
            duplicate_group_id=group_id,
            canonical_record_id=record_id,
            occurrence_index=1,
            match_type="unique",
        )

    def is_known(self, text: str) -> bool:
        return compute_normalized_hash(text) in self._exact

    @property
    def total_seen(self) -> int:
        return self._seen

    @property
    def total_duplicates(self) -> int:
        return self._duplicates

    @property
    def total_unique(self) -> int:
        return self._seen - self._duplicates
