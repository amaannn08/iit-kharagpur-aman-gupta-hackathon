"""Unit tests for StressEngine trigger policy and sandbox execution (PRD 9.3)."""

from datetime import datetime

import pytest

from sentinel.contracts.signals import (
    EntityReference,
    EventOutput,
    EvidenceSpan,
    ImpactComponents,
    ImpactOutput,
    RiskSignal,
    SentimentOutput,
    SentimentProbabilities,
)
from sentinel.stress.engine import StressEngine


@pytest.fixture
def stress_engine() -> StressEngine:
    engine = StressEngine()
    engine.reset_triggers()
    return engine


def make_signal(
    signal_id: str = "sig-001",
    event_label: str = "CREDIT",
    impact_score: int = 8,
    eligible_for_action: bool = True,
    confidence: float = 0.85,
    ticker: str = "APEX",
) -> RiskSignal:
    return RiskSignal(
        signal_id=signal_id,
        record_id="rec-001",
        run_id="run-001",
        source_id="news_demo",
        source_type="news",
        processed_at=datetime.utcnow(),
        entity=EntityReference(
            name="Apex Industrial Holdings",
            ticker=ticker,
            scope="company",
            resolved=True,
        ),
        sentiment=SentimentOutput(

            score=-0.75,
            label="negative",
            probabilities=SentimentProbabilities(positive=0.05, neutral=0.20, negative=0.75),
        ),
        event=EventOutput(label=event_label, confidence=confidence, abstained=False),
        impact=ImpactOutput(
            score=impact_score,
            components=ImpactComponents(event_base=4, scope=2, explicit_severity=2),
        ),
        evidence=[EvidenceSpan(start=0, end=40, text="Apex Industrial facing credit downgrade")],
        eligible_for_action=eligible_for_action,
        action_block_reasons=[],
    )



def test_stress_engine_trigger_criteria(stress_engine: StressEngine):
    """PRD 9.3: Only eligible signals with supported event class and impact > 7 trigger stress."""
    # Eligible signal, impact 8 -> Should trigger
    sig_eligible = make_signal(signal_id="sig-1", impact_score=8)
    assert stress_engine.should_trigger(sig_eligible) is True

    # Impact <= 7 -> Should NOT trigger
    sig_low_impact = make_signal(signal_id="sig-2", impact_score=7)
    assert stress_engine.should_trigger(sig_low_impact) is False

    # Blocked/ineligible signal -> Should NOT trigger
    sig_blocked = make_signal(signal_id="sig-3", impact_score=9, eligible_for_action=False)
    assert stress_engine.should_trigger(sig_blocked) is False

    # Unsupported event class -> Should NOT trigger
    sig_other = make_signal(signal_id="sig-4", event_label="OTHER", impact_score=9)
    assert stress_engine.should_trigger(sig_other) is False

    # Low event confidence -> Should NOT trigger
    sig_low_conf = make_signal(signal_id="sig-5", confidence=0.40, impact_score=9)
    assert stress_engine.should_trigger(sig_low_conf) is False


def test_duplicate_signal_does_not_retrigger(stress_engine: StressEngine):
    """PRD 9.3 & 13.3: Duplicate events do not create additional stress runs."""
    sig = make_signal(signal_id="sig-uniq-100", impact_score=8)
    assert stress_engine.should_trigger(sig) is True

    result = stress_engine.trigger_from_signal(sig)
    assert result is not None
    assert result.trigger_signal_id == "sig-uniq-100"

    # Attempting to trigger again with the exact same signal_id must be blocked
    assert stress_engine.should_trigger(sig) is False
    assert stress_engine.trigger_from_signal(sig) is None


def test_manual_sandbox_stress_simulation(stress_engine: StressEngine):
    """PRD 9.3: Manual user-triggered sandbox stress is labeled User-Triggered."""
    result = stress_engine.run_manual_stress(
        event_class="MACRO",
        impact_score=8,
        target_entity=None,
        target_scope="systemic",
        is_easing=False,
        run_id="sandbox-test-run",
    )

    assert result.trigger_type == "USER_TRIGGERED"
    assert result.event_class == "MACRO"
    assert result.impact_score == 8
    assert result.total_pnl_usd != 0.0
    assert result.reconciliation_passed is True
