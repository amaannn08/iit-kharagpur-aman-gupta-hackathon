"""Story-level risk event clustering and intensity triggering engine.

Real financial risk desks do not react to single isolated articles; they react to
developing *stories*—clusters of corroborated news and filings over rolling windows
with accelerating arrival velocity, multi-source diversity, and negative sentiment drift.

This module implements story clustering and intensity scoring:
  1. Signals are clustered by (entity_ticker, event_class) over a rolling 24-hour window.
  2. Story Intensity is computed via an explainable formula combining:
     - Peak single-article impact score
     - Article volume (log scale)
     - Source diversity (news, SEC filings, social)
     - Arrival velocity (articles/hour vs historical entity baseline)
     - Negative sentiment severity and drift
  3. Automatic stress triggers fire when Story Intensity crosses a frozen threshold
     calibrated on the dev split (false-trigger rate <= 5% per source).
"""

import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

from sentinel.contracts.signals import RiskSignal

# Frozen calibrated parameters (fixed on Polygon 2023 Q1-Q3 dev split, crisis windows excluded)
STORY_TRIGGER_INTENSITY_THRESHOLD = 7.5
STORY_MIN_ARTICLES_FOR_CLUSTER_TRIGGER = 2
STORY_MAX_SENTIMENT_FOR_TRIGGER = 0.15  # only adverse or non-positive stories trigger downside stress
SINGLE_EVENT_CATASTROPHIC_THRESHOLD = 8
STORY_ROLLING_WINDOW_HOURS = 24.0
STORY_COOLDOWN_HOURS = 12.0
ENTITY_BASELINE_VELOCITY_HOURLY = 0.15


@dataclass
class StoryCluster:
    """A cluster of related risk signals representing a single emerging financial story."""

    story_id: str
    entity_ticker: Optional[str]
    event_class: str
    first_seen: datetime
    last_seen: datetime
    signals: List[RiskSignal] = field(default_factory=list)
    triggered: bool = False
    trigger_time: Optional[datetime] = None
    trigger_reason: Optional[str] = None
    last_trigger_intensity: float = 0.0

    @property
    def article_count(self) -> int:
        return len(self.signals)

    @property
    def source_types(self) -> Set[str]:
        return {s.source_type for s in self.signals if s.source_type}

    @property
    def source_diversity(self) -> int:
        return len(self.source_types)

    @property
    def max_impact(self) -> int:
        if not self.signals:
            return 1
        return max(s.impact.score for s in self.signals)

    @property
    def avg_sentiment(self) -> float:
        if not self.signals:
            return 0.0
        return sum(s.sentiment.score for s in self.signals) / len(self.signals)

    @property
    def sentiment_drift(self) -> float:
        if len(self.signals) < 2:
            return 0.0
        recent = self.signals[-1].sentiment.score
        initial = self.signals[0].sentiment.score
        return recent - initial

    @property
    def velocity_hourly(self) -> float:
        """Articles per hour in the active observation window."""
        if len(self.signals) < 2:
            return 0.0
        dt = (self.last_seen - self.first_seen).total_seconds() / 3600.0
        effective_hours = max(0.5, dt)
        return len(self.signals) / effective_hours

    def compute_intensity(self) -> float:
        """Calculate explainable story intensity score (1.0 to 15.0 scale).

        Formula:
          intensity = max_impact
                    + 1.25 * ln(1 + count)
                    + 0.75 * (source_diversity - 1)
                    + 1.20 * min(2.5, max(0, velocity - baseline))
                    + sentiment_penalty
        """
        base_impact = float(self.max_impact)
        count_boost = 1.25 * math.log(1 + self.article_count)
        diversity_boost = 0.75 * max(0, self.source_diversity - 1)

        vel_excess = max(0.0, self.velocity_hourly - ENTITY_BASELINE_VELOCITY_HOURLY)
        velocity_boost = min(2.5, vel_excess * 1.20)

        # Adverse sentiment penalty / boost to risk intensity
        if self.avg_sentiment < -0.4:
            sent_boost = 1.0
        elif self.avg_sentiment < -0.2:
            sent_boost = 0.5
        elif self.avg_sentiment > 0.4:
            sent_boost = -0.75  # strong positive reduces downside risk intensity
        else:
            sent_boost = 0.0

        raw_score = base_impact + count_boost + diversity_boost + velocity_boost + sent_boost
        return round(min(15.0, max(1.0, raw_score)), 3)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize story cluster for API inspection and UI cards."""
        intensity = self.compute_intensity()
        return {
            "story_id": self.story_id,
            "entity_ticker": self.entity_ticker,
            "event_class": self.event_class,
            "article_count": self.article_count,
            "source_diversity": self.source_diversity,
            "source_types": list(self.source_types),
            "max_impact": self.max_impact,
            "avg_sentiment": round(self.avg_sentiment, 3),
            "sentiment_drift": round(self.sentiment_drift, 3),
            "velocity_hourly": round(self.velocity_hourly, 2),
            "intensity": intensity,
            "first_seen": self.first_seen.isoformat(),
            "last_seen": self.last_seen.isoformat(),
            "triggered": self.triggered,
            "trigger_time": self.trigger_time.isoformat() if self.trigger_time else None,
            "trigger_reason": self.trigger_reason,
            "headlines": [s.text_excerpt[:100] for s in self.signals[-5:] if s.text_excerpt],
        }


class StoryTracker:
    """Maintains rolling state of story clusters across replayed or live signals."""

    def __init__(
        self,
        window_hours: float = STORY_ROLLING_WINDOW_HOURS,
        trigger_threshold: float = STORY_TRIGGER_INTENSITY_THRESHOLD,
        cooldown_hours: float = STORY_COOLDOWN_HOURS,
    ) -> None:
        self.window_hours = window_hours
        self.trigger_threshold = trigger_threshold
        self.cooldown_hours = cooldown_hours
        self.active_clusters: Dict[Tuple[str, str], StoryCluster] = {}
        self.historical_clusters: List[StoryCluster] = []

    def _cluster_key(self, signal: RiskSignal) -> Tuple[str, str]:
        ticker = signal.entity.ticker or signal.entity.scope or "SYSTEMIC"
        event = signal.event.label.upper()
        return (ticker, event)

    def _prune_expired(self, current_time: datetime) -> None:
        expired_keys = []
        for key, cluster in self.active_clusters.items():
            age_hours = (current_time - cluster.last_seen).total_seconds() / 3600.0
            if age_hours > self.window_hours:
                expired_keys.append(key)
        for key in expired_keys:
            expired = self.active_clusters.pop(key)
            self.historical_clusters.append(expired)

    def process_signal(
        self,
        signal: RiskSignal,
        timestamp: Optional[datetime] = None,
    ) -> Tuple[StoryCluster, bool, Optional[str]]:
        """Add signal to its story cluster and evaluate whether it triggers a stress test.

        Returns:
            (cluster, should_trigger, trigger_reason)
        """
        ts = timestamp or signal.published_at or datetime.now(timezone.utc)
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)

        self._prune_expired(ts)

        key = self._cluster_key(signal)
        cluster = self.active_clusters.get(key)
        if cluster is None:
            story_id = f"story-{key[0]}-{key[1]}-{int(ts.timestamp())}"
            cluster = StoryCluster(
                story_id=story_id,
                entity_ticker=signal.entity.ticker,
                event_class=key[1],
                first_seen=ts,
                last_seen=ts,
                signals=[],
            )
            self.active_clusters[key] = cluster

        cluster.signals.append(signal)
        cluster.last_seen = ts
        intensity = cluster.compute_intensity()

        # Check triggering logic
        should_trigger = False
        reason = None

        # Rule 1: Catastrophic single event (unambiguous high impact >= 8)
        if (
            signal.impact.score >= SINGLE_EVENT_CATASTROPHIC_THRESHOLD
            and signal.event.confidence >= 0.70
            and not cluster.triggered
        ):
            should_trigger = True
            reason = (
                f"Catastrophic event: single article impact {signal.impact.score} "
                f"(confidence {signal.event.confidence:.2f}) on {cluster.event_class}"
            )

        # Rule 2: Story escalation (corroborated cluster crossing intensity threshold)
        elif (
            cluster.article_count >= STORY_MIN_ARTICLES_FOR_CLUSTER_TRIGGER
            and intensity >= self.trigger_threshold
            and cluster.avg_sentiment <= STORY_MAX_SENTIMENT_FOR_TRIGGER
        ):
            # Check cooldown or significant re-escalation
            if not cluster.triggered:
                should_trigger = True
                reason = (
                    f"Story escalation: {cluster.article_count} articles across "
                    f"{cluster.source_diversity} source(s) (velocity {cluster.velocity_hourly:.2f}/h, "
                    f"intensity {intensity:.2f} >= {self.trigger_threshold})"
                )
            elif (
                cluster.trigger_time is not None
                and (ts - cluster.trigger_time).total_seconds() / 3600.0 >= self.cooldown_hours
                and intensity >= cluster.last_trigger_intensity + 1.5
            ):
                should_trigger = True
                reason = (
                    f"Story re-escalation after cooldown: intensity surged to {intensity:.2f} "
                    f"(+{intensity - cluster.last_trigger_intensity:.2f})"
                )

        if should_trigger:
            cluster.triggered = True
            cluster.trigger_time = ts
            cluster.trigger_reason = reason
            cluster.last_trigger_intensity = intensity

        return cluster, should_trigger, reason

    def get_active_stories(self) -> List[Dict[str, Any]]:
        """Return serialized list of currently active story clusters sorted by intensity desc."""
        stories = [c.to_dict() for c in self.active_clusters.values()]
        stories.sort(key=lambda s: s["intensity"], reverse=True)
        return stories

    def get_story_by_id(self, story_id: str) -> Optional[Dict[str, Any]]:
        for c in self.active_clusters.values():
            if c.story_id == story_id:
                return c.to_dict()
        for c in self.historical_clusters:
            if c.story_id == story_id:
                return c.to_dict()
        return None

    def reset(self) -> None:
        """Clear all clusters (used across replay resets)."""
        self.active_clusters.clear()
        self.historical_clusters.clear()
