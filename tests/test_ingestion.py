"""Unit tests for local multi-source text adapters and portfolio loaders."""

import json
from pathlib import Path

import pytest

from sentinel.contracts.records import SourceType
from sentinel.contracts.stress import (
    BondPosition,
    CashPosition,
    LoanPosition,
    PortfolioSummary,
    SwapPosition,
)
from sentinel.ingestion.adapters import NewsAdapter, SocialAdapter

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def test_news_adapter_loads_curated_records():
    """Verify NewsAdapter parses all records from data/news_demo.csv."""
    news_file = DATA_DIR / "news_demo.csv"
    assert news_file.exists(), f"Missing required news demo file: {news_file}"

    records = NewsAdapter.load_from_csv(news_file)
    assert len(records) == 25

    for rec in records:
        assert rec.source_type == SourceType.NEWS
        assert rec.is_synthetic is True
        assert len(rec.text) >= 5
        assert rec.sequence_number is not None
        assert rec.timestamp_quality.value in ["synthetic", "original", "date_only"]

    apex_records = [r for r in records if r.primary_entity_id == "APEX"]
    assert len(apex_records) >= 1
    assert "Apex Industrial" in apex_records[0].text


def test_social_adapter_loads_curated_records():
    """Verify SocialAdapter parses all records from data/social_demo.csv."""
    social_file = DATA_DIR / "social_demo.csv"
    assert social_file.exists(), f"Missing required social demo file: {social_file}"

    records = SocialAdapter.load_from_csv(social_file)
    assert len(records) == 25

    for rec in records:
        assert rec.source_type == SourceType.SOCIAL
        assert rec.is_synthetic is True
        assert len(rec.text) >= 5
        assert rec.sequence_number is not None

    cashtag_records = [r for r in records if "$APEX" in r.text]
    assert len(cashtag_records) >= 1


def test_adapter_file_not_found():
    """Verify adapter raises FileNotFoundError on missing files."""
    with pytest.raises(FileNotFoundError):
        NewsAdapter.load_from_csv(DATA_DIR / "non_existent_file.csv")

    with pytest.raises(FileNotFoundError):
        SocialAdapter.load_from_csv(DATA_DIR / "non_existent_file.csv")


def test_wholesale_positions_json_validity():
    """Verify wholesale portfolio JSON adheres to Pydantic stress contracts."""
    portfolio_file = DATA_DIR / "wholesale_positions.json"
    assert portfolio_file.exists()

    with open(portfolio_file, mode="r", encoding="utf-8") as f:
        data = json.load(f)

    positions_data = data.get("positions", [])
    assert len(positions_data) == 13

    loans = []
    bonds = []
    swaps = []
    cash = []

    for pos in positions_data:
        asset_class = pos.get("asset_class")
        if asset_class == "loan":
            loans.append(LoanPosition(**pos))
        elif asset_class == "bond":
            bonds.append(BondPosition(**pos))
        elif asset_class == "swap":
            swaps.append(SwapPosition(**pos))
        elif asset_class == "cash":
            cash.append(CashPosition(**pos))
        else:
            pytest.fail(f"Unknown asset class: {asset_class}")

    assert len(loans) == 5
    assert len(bonds) == 5
    assert len(swaps) == 2
    assert len(cash) == 1

    summary = PortfolioSummary(**data["summary"])
    assert summary.total_book_value_usd == 500000000.0
    assert summary.corporate_loans_value_usd == 220000000.0
    assert summary.corporate_bonds_value_usd == 200000000.0
    assert summary.cash_reserves_usd == 80000000.0
    assert summary.interest_rate_swaps_gross_notional_usd == 150000000.0
