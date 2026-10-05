"""Data contracts and Pydantic schemas for S&P Sentinel."""

from sentinel.contracts.records import InputRecord, SourceType, TimestampQuality
from sentinel.contracts.signals import (
    EntityReference,
    EventOutput,
    EvidenceSpan,
    ImpactOutput,
    RiskSignal,
    SentimentOutput,
)
from sentinel.contracts.stress import (
    BondPosition,
    CashPosition,
    LoanPosition,
    PortfolioSummary,
    SwapPosition,
)

__all__ = [
    "BondPosition",
    "CashPosition",
    "EntityReference",
    "EventOutput",
    "EvidenceSpan",
    "ImpactOutput",
    "InputRecord",
    "LoanPosition",
    "PortfolioSummary",
    "RiskSignal",
    "SentimentOutput",
    "SourceType",
    "SwapPosition",
    "TimestampQuality",
]
