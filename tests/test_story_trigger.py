"""Unit tests for story-level clustering and intensity triggering."""

from datetime import datetime, timedelta, timezone
from typing import Optional

from sentinel.contracts.signals import (
    EntityReference,
    EventOutput,
    ImpactComponents,
    ImpactOutput,
    RiskSignal,
    SentimentOutput,
    SentimentProbabilities,
)
from sentinel.stress.story_trigger import (
    STORY_TRIGGER_INTENSITY_THRESHOLD,
    StoryCluster,
    StoryTracker,
)


def make_signal(
    record_id: str,
    ticker: str,
    event_label: str = "CREDIT",
    impact_score: int = 4,
    sentiment_score: float = -0.5,
    source_type: str = "news",
    published_at: Optional[datetime] = None,
    confidence: float = 0.85,
) -> RiskSignal:
    probs = SentimentProbabilities(
        positive=0.1 if sentiment_score < 0 else 0.8,
        negative=0.8 if sentiment_score < 0 else 0.1,
        neutral=0.1,
    )
    sent_out = SentimentOutput(
        score=sentiment_score,
        label="negative" if sentiment_score < 0 else "positive",
        probabilities=probs,
    )
    event_out = EventOutput(label=event_label, confidence=confidence)
    impact_out = ImpactOutput(
        score=impact_score,
        components=ImpactComponents(event_base=5, scope=1, explicit_severity=1),
    )
    entity_ref = EntityReference(name=ticker, ticker=ticker, resolved=True)
    ts = published_at or datetime.now(timezone.utc)
    return RiskSignal(
        signal_id=f"sig-{record_id}",
        run_id="test-run",
        record_id=record_id,
        source_id="test_src",
        source_type=source_type,
        published_at=ts,
        text_excerpt="Test excerpt",
        entity=entity_ref,
        sentiment=sent_out,
        event=event_out,
        impact=impact_out,
        eligible_for_action=True,
    )


def test_story_cluster_intensity_calculation():
    t0 = datetime(2026, 10, 12, 10, 0, tzinfo=timezone.utc)
    cluster = StoryCluster(
        story_id="story-1",
        entity_ticker="AAPL",
        event_class="CREDIT",
        first_seen=t0,
        last_seen=t0,
    )
    s1 = make_signal("r1", "AAPL", impact_score=4, sentiment_score=-0.3, published_at=t0)
    cluster.signals.append(s1)

    # 1 article, impact 4: ~5.3
    intensity_1 = cluster.compute_intensity()
    assert 4.5 <= intensity_1 <= 6.0

    # Add second article 30 mins later from a filing
    t1 = t0 + timedelta(minutes=30)
    cluster.last_seen = t1
    s2 = make_signal("r2", "AAPL", impact_score=6, sentiment_score=-0.7, source_type="sec_8k", published_at=t1)
    cluster.signals.append(s2)

    intensity_2 = cluster.compute_intensity()
    # High impact, high velocity (4 articles/hr rate), multi-source, adverse sentiment
    assert intensity_2 > intensity_1
    assert intensity_2 >= STORY_TRIGGER_INTENSITY_THRESHOLD


def test_story_tracker_escalation_trigger():
    tracker = StoryTracker(trigger_threshold=STORY_TRIGGER_INTENSITY_THRESHOLD)
    t0 = datetime(2026, 10, 12, 9, 0, tzinfo=timezone.utc)

    # First moderate article: should not trigger
    s1 = make_signal("r1", "JPM", impact_score=5, sentiment_score=-0.4, published_at=t0)
    c1, tr1, r1 = tracker.process_signal(s1, timestamp=t0)
    assert not tr1
    assert not c1.triggered

    # Second article 45 mins later with higher impact from SEC filing: should trigger
    t1 = t0 + timedelta(minutes=45)
    s2 = make_signal("r2", "JPM", impact_score=6, sentiment_score=-0.6, source_type="sec_8k", published_at=t1)
    c2, tr2, r2 = tracker.process_signal(s2, timestamp=t1)
    assert tr2
    assert c2.triggered
    assert "Story escalation" in (r2 or "")

    # Third article in same cluster within cooldown should not re-trigger
    t2 = t1 + timedelta(minutes=30)
    s3 = make_signal("r3", "JPM", impact_score=6, sentiment_score=-0.5, published_at=t2)
    c3, tr3, r3 = tracker.process_signal(s3, timestamp=t2)
    assert not tr3


def test_story_tracker_single_catastrophic_event():
    tracker = StoryTracker()
    t0 = datetime(2026, 10, 12, 12, 0, tzinfo=timezone.utc)

    # Single catastrophic signal (impact 8, high confidence): triggers immediately
    s = make_signal("r-cat", "BAC", impact_score=8, sentiment_score=-0.8, confidence=0.92, published_at=t0)
    cluster, should_trig, reason = tracker.process_signal(s, timestamp=t0)
    assert should_trig
    assert "Catastrophic event" in (reason or "")


def test_story_tracker_routine_articles_do_not_trigger():
    tracker = StoryTracker()
    t0 = datetime(2026, 10, 12, 8, 0, tzinfo=timezone.utc)

    # 10 routine articles across different companies with low impact
    for i in range(10):
        ts = t0 + timedelta(hours=i)
        s = make_signal(f"r-{i}", f"TICKER_{i}", impact_score=2, sentiment_score=0.1, published_at=ts)
        cluster, should_trig, _ = tracker.process_signal(s, timestamp=ts)
        assert not should_trig
