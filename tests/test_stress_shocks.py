"""Shock catalog v2: calibrated on measured historical windows, directional, equity-aware."""

import json

from sentinel.config import settings
from sentinel.contracts.stress import AssetClass, EquityPosition
from sentinel.stress import shocks
from sentinel.stress.engine import StressEngine
from sentinel.stress.shocks import ScaledShock, build_scaled_shock
from sentinel.stress.valuation import ValuationEngine


def test_systemic_catalog_matches_measured_windows():
    windows = json.loads((settings.data_dir / "market" / "stress_windows.json").read_text())[
        "windows"
    ]
    for params in (
        shocks.MACRO_TIGHTENING,
        shocks.MACRO_EASING,
        shocks.CREDIT_SYSTEMIC,
        shocks.GEOPOLITICAL_SYSTEMIC,
    ):
        w = windows[params.anchor]
        assert abs(params.equity_shock_pct - w["equity_shock_pct"]) < 1e-3
        assert abs(params.benchmark_yield_shift_bps - w["benchmark_yield_shift_bps"]) < 0.2
        assert abs(params.bond_spread_shift_bps - w["bond_spread_shift_bps"]) < 0.2
        assert abs(params.loan_pd_increment - w["loan_pd_increment"]) < 1e-3


def test_flight_to_quality_signs():
    assert (
        build_scaled_shock("GEOPOLITICAL", 8, target_scope="systemic").benchmark_yield_shift_bps < 0
    )
    assert build_scaled_shock("CREDIT", 8, target_scope="systemic").benchmark_yield_shift_bps < 0
    assert build_scaled_shock("MACRO", 8, target_scope="systemic").benchmark_yield_shift_bps > 0
    easing = build_scaled_shock("MACRO", 8, target_scope="systemic", is_easing=True)
    assert easing.benchmark_yield_shift_bps < 0 and easing.equity_shock_pct > 0


def test_equity_beta_one_loses_exactly_the_market_shock():
    engine = ValuationEngine(StressEngine().portfolio)
    pos = EquityPosition(position_id="E", entity_id="X", counterparty_name="X", sector="Industrials",
                         market_value=1_000_000.0, beta=1.0)  # fmt: skip
    shock = ScaledShock(0, 0, 0, 0, 1.0, None, "systemic", equity_shock_pct=-0.10)
    d = engine.value_equity(pos, shock)
    assert d.asset_class == AssetClass.EQUITY and d.pnl_usd == -100_000.0
    idio = ScaledShock(0, 0, 0, 0, 1.0, "X", "entity", equity_shock_pct=-0.15)
    assert engine.value_equity(pos, idio).pnl_usd == -150_000.0


def test_cyber_without_exposure_is_flagged_not_a_zero_loss_run():
    engine = StressEngine()
    shock = build_scaled_shock("CYBER", 8, target_entity="NOBODY", target_scope="entity")
    result = engine._mark_exposure(
        engine.valuation_engine.run_stress_test(shock, event_class="CYBER")
    )
    assert result.status == "NO_EXPOSURE"


def test_cyber_operational_loss_uses_observed_sector_fraud_rate():
    engine = StressEngine()
    rate = engine.portfolio.sector_fraud_rates["Financials"]
    shock = build_scaled_shock("CYBER", 8, target_entity="FSBK", target_scope="entity",
                               target_sector="Financials")  # fmt: skip
    result = engine.valuation_engine.run_stress_test(shock, event_class="CYBER")
    hit = [p for p in result.position_deltas if p.operational_loss_usd > 0]
    assert hit and all(p.sector == "Financials" and p.sleeve == "retail_sme" for p in hit)
    for p in hit:
        assert abs(p.operational_loss_usd - p.baseline_value_usd * rate * 10.0) < 0.05
    assert result.reconciliation_passed
