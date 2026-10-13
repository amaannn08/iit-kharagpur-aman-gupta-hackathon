"""Tests for ISDA and SEC Item 1.05 domain credit/cyber rules and triggering behavior.

Verifies:
1. Domain credit distress headlines map to CREDIT with impact >= 7.
2. SVB Securities investment banking conference headlines stay non-CREDIT and non-triggering.
3. Routine 8-K filings stay non-triggering.
4. Material cyber outage headlines map to CYBER with impact >= 7.
"""

from datetime import datetime, timezone

from sentinel.contracts.records import InputRecord, SourceType
from sentinel.nlp.engine import NLPEngine
from sentinel.stress.engine import StressEngine


def test_svb_crisis_headlines_classified_as_credit_with_high_impact():
    engine = NLPEngine()

    headlines = [
        "Silicon Valley Bank fails, shut down by FDIC after run on deposits",
        "SVB shares fall sharply after $1.8B in surprise bond losses",
        "Silicon Valley Bank seized by FDIC as depositors pull cash",
    ]

    for text in headlines:
        rec = InputRecord(
            record_id=f"test-{hash(text)}",
            source_id="news",
            source_type=SourceType.NEWS,
            text=text,
            published_at=datetime.now(timezone.utc),
        )
        signals = engine.process_record_multi(rec, "eval-test")
        assert len(signals) >= 1, f"Expected resolved signal for: {text}"
        sig = signals[0]

        assert sig.event.label == "CREDIT", f"Expected CREDIT for '{text}', got {sig.event.label}"
        assert sig.event.confidence >= 0.50, f"Expected confidence >= 0.50 for '{text}', got {sig.event.confidence}"
        assert sig.impact.score >= 7, f"Expected impact >= 7 for '{text}', got {sig.impact.score}"
        assert len(sig.evidence) >= 1, f"Expected evidence span for '{text}'"


def test_svb_securities_conference_stays_non_credit_and_non_triggering():
    engine = NLPEngine()
    stress_engine = StressEngine()

    text = "SVB Securities to host biopharma conference"
    rec = InputRecord(
        record_id="test-conf",
        source_id="news",
        source_type=SourceType.NEWS,
        text=text,
        published_at=datetime.now(timezone.utc),
    )
    signals = engine.process_record_multi(rec, "eval-test")
    assert len(signals) >= 1
    sig = signals[0]

    assert sig.event.label != "CREDIT", f"Expected non-CREDIT for conference PR, got {sig.event.label}"
    assert sig.impact.score < 7, f"Expected impact < 7 for conference PR, got {sig.impact.score}"
    assert stress_engine.should_trigger(sig) is False, "Conference PR must not trigger stress test"


def test_routine_8k_filing_stays_non_triggering():
    engine = NLPEngine()
    stress_engine = StressEngine()

    filings = [
        "Apple Inc. files Form 8-K Item 5.02: Departure of Director or Principal Officers",
        "Microsoft Corp. announces quarterly dividend declaration of $0.75 per share",
        "Johnson & Johnson submits Form 8-K Item 8.01 Other Events regarding upcoming investor presentation",
    ]

    for text in filings:
        rec = InputRecord(
            record_id=f"test-8k-{hash(text)}",
            source_id="sec_8k",
            source_type=SourceType.NEWS,
            text=text,
            published_at=datetime.now(timezone.utc),
        )
        signals = engine.process_record_multi(rec, "eval-test")
        assert len(signals) >= 1
        sig = signals[0]

        assert sig.event.label != "CREDIT", f"Routine filing must not be CREDIT: {text}"
        assert sig.impact.score < 7, f"Routine filing impact must be < 7: {text}"
        assert stress_engine.should_trigger(sig) is False, f"Routine filing must not trigger: {text}"


def test_cyber_global_outage_classified_as_cyber_with_high_impact():
    engine = NLPEngine()
    text = "CrowdStrike update crashes Windows machines worldwide, causing global IT outage"
    rec = InputRecord(
        record_id="test-cyber",
        source_id="news",
        source_type=SourceType.NEWS,
        text=text,
        published_at=datetime.now(timezone.utc),
    )
    signals = engine.process_record_multi(rec, "eval-test")
    assert len(signals) >= 1
    sig = signals[0]

    assert sig.event.label == "CYBER", f"Expected CYBER, got {sig.event.label}"
    assert sig.impact.score >= 7, f"Expected impact >= 7, got {sig.impact.score}"
