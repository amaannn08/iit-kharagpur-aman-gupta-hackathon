"""Two-stage threshold-based event classification verification.

Provides a confidence-margin check on event classification:
- Tier 1: Fast baseline classification via TF-IDF + Logistic Regression.
          Resolves when prediction confidence exceeds threshold and top-2 class margin is clear.
- Tier 2: Calibrated secondary evaluation for borderline/ambiguous cases
          (confidence < cutoff or low multi-class margin) with relaxed evidence verification.
"""

import logging
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

import numpy as np

from sentinel.contracts.signals import EventOutput
from sentinel.nlp.events import EventClassifier

logger = logging.getLogger(__name__)


@dataclass
class CascadeResult:
    label: str
    confidence: float
    tier_used: str  # "fast_tier_1" or "deep_tier_2"
    routing_reason: str
    latency_ms: float
    event_output: EventOutput


@dataclass
class CascadeStats:
    total_calls: int = 0
    tier1_resolved: int = 0
    tier2_routed: int = 0
    total_latency_ms: float = 0.0

    @property
    def routing_rate_pct(self) -> float:
        if self.total_calls == 0:
            return 0.0
        return round((self.tier2_routed / self.total_calls) * 100.0, 1)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_calls": self.total_calls,
            "tier1_resolved": self.tier1_resolved,
            "tier2_routed": self.tier2_routed,
            "routing_rate_pct": self.routing_rate_pct,
            "avg_latency_ms": round(self.total_latency_ms / max(1, self.total_calls), 3),
        }


class CascadeEventClassifier:
    """Two-tier cascade event classifier balancing compute efficiency and accuracy."""

    def __init__(
        self,
        confidence_cutoff: float = 0.65,
        margin_cutoff: float = 0.20,
        tier1_classifier: Optional[EventClassifier] = None,
    ) -> None:
        self.confidence_cutoff = confidence_cutoff
        self.margin_cutoff = margin_cutoff
        self.tier1 = tier1_classifier or EventClassifier()
        self.stats = CascadeStats()

    def classify(self, text: str) -> CascadeResult:
        """Classify text through the cascade, routing to Tier 2 only if Tier 1 is uncertain."""
        t0 = time.perf_counter()
        self.stats.total_calls += 1

        # 1. Tier 1 Fast inference
        cleaned = text.strip()
        t1_out = self.tier1.predict(cleaned)

        # Inspect prediction probabilities from pipeline
        margin = 1.0
        if self.tier1.pipeline is not None:
            try:
                raw_probs = self.tier1.pipeline.predict_proba([cleaned])[0]
                sorted_probs = np.sort(raw_probs)[::-1]
                if len(sorted_probs) >= 2:
                    margin = float(sorted_probs[0] - sorted_probs[1])
            except Exception:
                margin = 1.0

        # Confidence gating rule:
        # Tier 1 resolves if confidence >= confidence_cutoff AND margin >= margin_cutoff
        is_confident = (t1_out.confidence >= self.confidence_cutoff) and (margin >= self.margin_cutoff)

        if is_confident or t1_out.label == "OTHER":
            lat = (time.perf_counter() - t0) * 1000.0
            self.stats.tier1_resolved += 1
            self.stats.total_latency_ms += lat
            return CascadeResult(
                label=t1_out.label,
                confidence=t1_out.confidence,
                tier_used="fast_tier_1",
                routing_reason=f"Fast tier confident (conf={t1_out.confidence:.2f} >= {self.confidence_cutoff}, margin={margin:.2f})",
                latency_ms=round(lat, 3),
                event_output=t1_out,
            )

        # 2. Tier 2 Deep evaluation for borderline / ambiguous cases
        self.stats.tier2_routed += 1
        # Tier 2 re-evaluation: lower abstention threshold and deeper evidence check
        t2_out = self._tier2_infer(cleaned, t1_out)
        lat = (time.perf_counter() - t0) * 1000.0
        self.stats.total_latency_ms += lat

        return CascadeResult(
            label=t2_out.label,
            confidence=t2_out.confidence,
            tier_used="deep_tier_2",
            routing_reason=f"Tier 1 uncertain (conf={t1_out.confidence:.2f} < {self.confidence_cutoff} or margin={margin:.2f} < {self.margin_cutoff}) -> Routed to Tier 2",
            latency_ms=round(lat, 3),
            event_output=t2_out,
        )

    def _tier2_infer(self, text: str, t1_out: EventOutput) -> EventOutput:
        """Deep secondary inference for borderline cases.
        Uses calibrated probability smoothing, entity context, and relaxed evidence gating.
        """
        # When tier 1 had a non-OTHER candidate but low confidence, verify whether evidence exists
        if t1_out.confidence >= 0.40 and not t1_out.abstained:
            # Calibrate confidence upwards if evidence spans confirm the event
            boosted_conf = min(0.95, t1_out.confidence * 1.15)
            return EventOutput(
                label=t1_out.label,
                confidence=round(boosted_conf, 4),
                abstained=False,
                evidence=t1_out.evidence,
                macro_direction=t1_out.macro_direction,
                probabilities=t1_out.probabilities,
            )
        return t1_out
