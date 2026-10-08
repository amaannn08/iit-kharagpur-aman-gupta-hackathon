"""Tests for orchestrated NLPEngine and RiskSignal emission (PRD Section 6.2 & 7)."""

from datetime import datetime, timezone

from sentinel.contracts.records import InputRecord, SourceType
from sentinel.nlp.engine import NLPEngine
from sentinel.replay.dedup import DedupDecision


def test_nlp_engine_severe_credit_signal_eligible():
    engine = NLPEngine(action_impact_threshold=7, action_confidence_threshold=0.30)
    text = (
        "Apex Industrial missed scheduled coupon payment and declared bankruptcy, "
        "sparking nationwide systemic contagion across banking sector."
    )
    record = InputRecord(
        record_id="rec-apex-01",
        source_id="news_demo",
        source_type=SourceType.NEWS,
        text=text,
        simulated_at=datetime(2023, 3, 10, 9, 0, tzinfo=timezone.utc),
    )

    signal = engine.process_record(record, run_id="run-test-01")

    assert signal.record_id == "rec-apex-01"
    assert signal.run_id == "run-test-01"
    assert signal.entity.ticker == "APEX"
    assert signal.sentiment.label == "negative"
    assert signal.sentiment.score < 0
    assert signal.event.label == "CREDIT"
    assert signal.impact.score >= 8
    assert signal.eligible_for_action is True
    assert signal.action_block_reasons == []
    assert len(signal.evidence) >= 1


def test_nlp_engine_duplicate_action_suppression():
    engine = NLPEngine()
    record = InputRecord(
        record_id="rec-apex-02",
        source_id="social_demo",
        source_type=SourceType.SOCIAL,
        text="Apex Industrial missed scheduled coupon payment and declared bankruptcy.",
    )
    dedup = DedupDecision(
        is_duplicate=True,
        text_hash="hash-dup",
        duplicate_group_id="dup-group-01",
        canonical_record_id="rec-apex-01",
        occurrence_index=2,
    )

    signal = engine.process_record(record, run_id="run-test-01", dedup_decision=dedup)

    assert signal.eligible_for_action is False
    assert "DUPLICATE_TEXT_SUPPRESSED" in signal.action_block_reasons
    assert signal.duplicate_group_id == "dup-group-01"


def test_nlp_engine_routine_text_blocks_action():
    engine = NLPEngine()
    record = InputRecord(
        record_id="rec-appl-01",
        source_id="news_demo",
        source_type=SourceType.NEWS,
        text="Apple uploaded routine corporate governance presentation to website.",
    )

    signal = engine.process_record(record, run_id="run-test-01")

    assert signal.eligible_for_action is False
    assert (
        "EVENT_CLASSIFICATION_OTHER" in signal.action_block_reasons
        or "IMPACT_BELOW_ACTION_THRESHOLD" in signal.action_block_reasons
    )
