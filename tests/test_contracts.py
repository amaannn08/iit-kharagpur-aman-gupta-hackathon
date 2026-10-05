"""Unit tests for Pydantic v2 data contracts conforming to PRD Section 6 & 10."""

from datetime import date, datetime, timezone

import pytest
from pydantic import ValidationError

from sentinel.contracts.records import InputRecord, SourceType, TimestampQuality
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
from sentinel.contracts.stress import (
    AssetClass,
    BondPosition,
    CashPosition,
    LoanPosition,
    PortfolioSummary,
    SwapPosition,
)


def test_input_record_valid_creation():
    """Verify standard valid news record creation."""
    record = InputRecord(
        record_id="rec-001",
        source_id="news_demo",
        source_type=SourceType.NEWS,
        text="Apex Industrial Holdings missed coupon payment to syndicated lenders.",
        headline="Apex Industrial misses coupon",
        published_at=datetime.now(timezone.utc),
        timestamp_quality=TimestampQuality.SYNTHETIC,
        is_synthetic=True,
        primary_entity_id="APEX",
    )
    assert record.record_id == "rec-001"
    assert record.source_type == SourceType.NEWS
    assert record.is_synthetic is True
    assert record.primary_entity_id == "APEX"


def test_input_record_empty_text_rejected():
    """Verify input text under 5 characters or empty whitespace is rejected."""
    with pytest.raises(ValidationError):
        InputRecord(
            record_id="rec-fail",
            source_id="news_demo",
            source_type=SourceType.NEWS,
            text="   ",
        )


def test_sentiment_probabilities_sum_validation():
    """Verify probability distribution must sum to approximately 1.0."""
    valid_probs = SentimentProbabilities(positive=0.02, negative=0.92, neutral=0.06)
    assert valid_probs.negative == 0.92

    # Invalid sum (> 1.05 or < 0.95) must fail
    with pytest.raises(ValidationError):
        SentimentProbabilities(positive=0.8, negative=0.8, neutral=0.1)


def test_risk_signal_contract_integrity():
    """Verify end-to-end RiskSignal structure matches PRD Section 6.2."""
    signal = RiskSignal(
        signal_id="sig-001",
        run_id="run-local-001",
        record_id="rec-001",
        source_id="news_demo",
        source_type="news",
        is_synthetic=True,
        entity=EntityReference(name="Apex Industrial Holdings", ticker="APEX"),
        sentiment=SentimentOutput(
            score=-0.90,
            label="negative",
            probabilities=SentimentProbabilities(positive=0.02, negative=0.92, neutral=0.06),
        ),
        event=EventOutput(label="CREDIT", confidence=0.95, abstained=False),
        impact=ImpactOutput(
            score=8,
            rubric_version="1.0",
            components=ImpactComponents(event_base=5, scope=1, explicit_severity=2),
        ),
        evidence=[EvidenceSpan(start=0, end=42, text="Apex Industrial Holdings missed coupon")],
        eligible_for_action=True,
    )
    assert signal.signal_id == "sig-001"
    assert signal.impact.score == 8
    assert signal.entity.ticker == "APEX"
    assert signal.sentiment.label == "negative"


def test_wholesale_positions_contract():
    """Verify portfolio position validation across loans, bonds, swaps, and cash."""
    loan = LoanPosition(
        position_id="LOAN-001",
        asset_class=AssetClass.LOAN,
        entity_id="APEX",
        counterparty_name="Apex Industrial Holdings",
        sector="Industrials",
        market_value=45000000.0,
        ead=45000000.0,
        baseline_pd=0.02,
        lgd=0.45,
        rating="BB-",
        maturity_date=date(2028, 6, 30),
    )
    assert loan.asset_class == AssetClass.LOAN
    assert loan.market_value == 45000000.0

    bond = BondPosition(
        position_id="BOND-001",
        asset_class=AssetClass.BOND,
        entity_id="APEX",
        counterparty_name="Apex Industrial Holdings",
        sector="Industrials",
        market_value=30000000.0,
        notional=30000000.0,
        coupon=0.065,
        yield_val=0.075,
        spread_bps=280.0,
        modified_duration=4.8,
        rating="BB-",
        maturity_date=date(2030, 9, 15),
    )
    assert bond.modified_duration == 4.8

    swap = SwapPosition(
        position_id="SWAP-001",
        asset_class=AssetClass.SWAP,
        entity_id="GCH",
        counterparty_name="Global Clearing House",
        sector="Financials",
        market_value=0.0,
        notional=100000000.0,
        pay_receive="receive_fixed",
        fixed_rate=0.041,
        signed_dv01=-42000.0,
        maturity_years=5.0,
        maturity_date=date(2031, 3, 1),
    )
    assert swap.signed_dv01 == -42000.0

    cash = CashPosition(
        position_id="CASH-001",
        entity_id="FED",
        counterparty_name="Federal Reserve Bank",
        market_value=80000000.0,
        notional=80000000.0,
        yield_val=0.0525,
        maturity_date=date(2026, 12, 31),
    )
    assert cash.market_value == 80000000.0

    summary = PortfolioSummary(
        total_book_value_usd=500000000.0,
        corporate_loans_value_usd=220000000.0,
        corporate_bonds_value_usd=200000000.0,
        cash_reserves_usd=80000000.0,
        interest_rate_swaps_gross_notional_usd=150000000.0,
    )
    assert summary.total_book_value_usd == 500000000.0
