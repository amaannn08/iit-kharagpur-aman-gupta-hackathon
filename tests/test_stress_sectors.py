"""Tests for GICS sector normalization and real sector scope (Item 9 & Finding B)."""

import json
from pathlib import Path

import pytest

from sentinel.nlp.engine import NLPEngine
from sentinel.nlp.entities import EntityLinker
from sentinel.stress.engine import StressEngine
from sentinel.stress.portfolio import WholesalePortfolio
from sentinel.stress.sectors import GICS_SECTORS, NON_CORPORATE, normalize_sector


def test_normalize_sector():
    assert normalize_sector("Information Technology") == "Information Technology"
    assert normalize_sector("tech") == "Information Technology"
    assert normalize_sector("technology") == "Information Technology"
    assert normalize_sector("healthcare") == "Health Care"
    assert normalize_sector("Health Care") == "Health Care"
    assert normalize_sector("banks") == "Financials"
    assert normalize_sector("financial services") == "Financials"
    assert normalize_sector("Financials") == "Financials"
    assert normalize_sector("Rates") == "Rates"
    assert normalize_sector("Government / Cash") == "Government / Cash"
    assert normalize_sector(None) is None

    with pytest.raises(ValueError, match="Unknown sector"):
        normalize_sector("invalid_sector_xyz")


def test_all_positions_in_portfolio_files_have_valid_sector():
    from sentinel.config import settings

    portfolio_files = sorted({settings.data_dir / f for files in settings.portfolio_profiles.values()
                              for f in files})  # fmt: skip
    valid_sectors = set(GICS_SECTORS) | set(NON_CORPORATE)
    for path in portfolio_files:
        data = json.loads(path.read_text(encoding="utf-8"))
        for pos in data.get("positions", []):
            sec = pos.get("sector")
            assert sec in valid_sectors, f"Position {pos.get('position_id')} in {path.name} has invalid sector '{sec}'"


def test_sector_shock_hits_only_target_sector():
    repo_root = Path(__file__).resolve().parent.parent
    portfolio = WholesalePortfolio.load_many([
        repo_root / "data" / "wholesale_positions.json",
        repo_root / "data" / "portfolio" / "credit_sleeve.json",
        repo_root / "data" / "portfolio" / "equity_sleeve.json",
    ])
    engine = StressEngine()
    engine.valuation_engine.portfolio = portfolio

    result = engine.run_manual_stress(
        event_class="CREDIT",
        impact_score=8,
        target_entity=None,
        target_scope="sector",
        target_sector="Financials",
    )

    impacted = [p for p in result.position_deltas if abs(p.pnl_usd) > 1e-4]
    assert len(impacted) > 0, "At least one Financials position should be impacted"
    for p in impacted:
        assert p.sector == "Financials", f"Expected only Financials to be impacted, got {p.position_id} ({p.sector})"

    # Verify positions in other sectors were not impacted
    unimpacted = [p for p in result.position_deltas if p.sector != "Financials"]
    for p in unimpacted:
        assert abs(p.pnl_usd) < 1e-4, f"Position {p.position_id} in {p.sector} should have 0 PnL"


def test_regional_banks_headline_triggers_sector_scope_credit_shock():
    linker = EntityLinker()
    text = "Regional banks slump as deposit flight spreads"
    ref, spans = linker.resolve(text)

    assert ref.scope == "sector"
    assert ref.sector == "Financials"
    assert ref.name == "Financials"
    assert len(spans) > 0

    from sentinel.contracts.records import InputRecord, SourceType

    nlp = NLPEngine()
    signal = nlp.process_record(
        InputRecord(
            record_id="rec-1",
            source_id="src-1",
            source_type=SourceType.NEWS,
            text=text,
        ),
        run_id="test-run",
    )
    # The signal entity scope should be sector
    assert signal.entity.scope == "sector"
    assert signal.entity.sector == "Financials"

    engine = StressEngine()
    # Force event to CREDIT with impact 8 for stress triggering
    signal.event.label = "CREDIT"
    signal.event.confidence = 0.95
    signal.impact.score = 8
    signal.event.abstained = False
    signal.eligible_for_action = True

    result = engine.trigger_from_signal(signal)
    assert result is not None
    assert result.shock_parameters["target_scope"] == "sector"
    assert result.shock_parameters["target_sector"] == "Financials"

    impacted = [p for p in result.position_deltas if abs(p.pnl_usd) > 1e-4]
    assert len(impacted) > 0
    for p in impacted:
        assert p.sector == "Financials"
