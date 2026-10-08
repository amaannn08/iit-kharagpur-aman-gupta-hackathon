"""Unit tests for wholesale banking stress valuation engine (PRD 9.4 & 13.3)."""

import pytest

from sentinel.contracts.stress import (
    AssetClass,
    BondPosition,
    LoanPosition,
)
from sentinel.stress.portfolio import WholesalePortfolio
from sentinel.stress.shocks import ScaledShock, build_scaled_shock
from sentinel.stress.valuation import ValuationEngine


@pytest.fixture
def portfolio() -> WholesalePortfolio:
    return WholesalePortfolio.load_from_json("data/wholesale_positions.json")


@pytest.fixture
def engine(portfolio: WholesalePortfolio) -> ValuationEngine:
    return ValuationEngine(portfolio)


def test_portfolio_funded_and_derivative_segregation(portfolio: WholesalePortfolio):
    """PRD 9.1: Verify funded exposure is $500M and derivative notional is segregated."""
    assert portfolio.total_funded_exposure == 500_000_000.0
    # Swap gross notional is $150M ($75M + $75M)
    assert portfolio.total_derivative_notional == 150_000_000.0
    # Derivative notional must not be added to balance sheet funded exposure
    funded = portfolio.total_funded_exposure
    assert funded != funded + portfolio.total_derivative_notional


def test_bond_duration_valuation_and_bps_conversion(engine: ValuationEngine):
    """PRD 9.4 & 13.3: Verify delta = -duration * value * shift with exact bps conversion."""
    bond = BondPosition(

        position_id="TEST-BOND-1",
        asset_class=AssetClass.BOND,
        entity_id="APEX",
        counterparty_name="Apex Industrial",
        sector="Industrials",
        market_value=10_000_000.0,
        notional=10_000_000.0,
        coupon=0.05,
        yield_val=0.05,
        spread_bps=100.0,
        modified_duration=4.0,
        rating="BBB",
        maturity_date="2030-01-01",
    )

    # 150 bps spread shift = 0.015 decimal
    shock = ScaledShock(
        bond_spread_shift_bps=150.0,
        loan_pd_increment=0.0,
        lgd_increment=0.0,
        benchmark_yield_shift_bps=0.0,
        scale_multiplier=1.0,
        target_entity="APEX",
        target_scope="entity",
    )

    delta = engine.value_bond(bond, shock)
    # Expected: -4.0 * 10,000,000 * 0.015 = -600,000
    assert delta.pnl_usd == -600_000.0
    assert delta.stressed_value_usd == 9_400_000.0
    assert delta.pct_change == -0.06
    assert delta.applied_shock_summary != "Unimpacted"


def test_loan_ecl_valuation_and_clamping(engine: ValuationEngine):
    """PRD 9.4 & 13.3: Incremental ECL = EAD * delta_PD * LGD and PD/LGD clamped."""
    loan = LoanPosition(

        position_id="TEST-LOAN-1",
        asset_class=AssetClass.LOAN,
        entity_id="APEX",
        counterparty_name="Apex Industrial",
        sector="Industrials",
        market_value=20_000_000.0,
        ead=20_000_000.0,
        baseline_pd=0.02,
        lgd=0.40,
        rating="BB",
        maturity_date="2028-01-01",
    )

    # PD + 2.5 pp = 0.025 decimal, LGD + 5.0 pp = 0.05 decimal
    shock = ScaledShock(
        bond_spread_shift_bps=0.0,
        loan_pd_increment=0.025,
        lgd_increment=0.05,
        benchmark_yield_shift_bps=0.0,
        scale_multiplier=1.0,
        target_entity="APEX",
        target_scope="entity",
    )

    delta = engine.value_loan(loan, shock)
    # Baseline ECL: 20M * 0.02 * 0.40 = 160,000
    # Stressed PD: 0.045, Stressed LGD: 0.45
    # Stressed ECL: 20M * 0.045 * 0.45 = 405,000
    # Incremental ECL: 405,000 - 160,000 = 245,000
    assert delta.ecl_baseline_usd == 160_000.0
    assert delta.ecl_stressed_usd == 405_000.0
    assert delta.incremental_ecl_usd == 245_000.0
    assert delta.pnl_usd == -245_000.0
    assert delta.stressed_value_usd == 19_755_000.0


def test_swap_sign_convention_pay_fixed_loses_on_rate_increase(engine: ValuationEngine):
    """PRD 13.3 Invariant: Pay-fixed loses value under rate increase, and gains under rate cut."""
    # SWAP-002 is pay-fixed with signed_dv01 = -34,500
    pay_fixed_swap = next(s for s in engine.portfolio.swaps if s.pay_receive == "pay_fixed")

    # Rate hike: +100 bps
    hike_shock = ScaledShock(
        bond_spread_shift_bps=0.0,
        loan_pd_increment=0.0,
        lgd_increment=0.0,
        benchmark_yield_shift_bps=100.0,
        scale_multiplier=1.0,
        target_entity=None,
        target_scope="systemic",
    )

    delta_hike = engine.value_swap(pay_fixed_swap, hike_shock)
    # delta_value = signed_dv01 * yield_shift_bps = -34,500 * 100 = -3,450,000
    assert delta_hike.pnl_usd == -3_450_000.0
    assert delta_hike.pnl_usd < 0  # Invariant: pay-fixed loses value under rate increase

    # Rate cut: -100 bps
    cut_shock = ScaledShock(
        bond_spread_shift_bps=0.0,
        loan_pd_increment=0.0,
        lgd_increment=0.0,
        benchmark_yield_shift_bps=-100.0,
        scale_multiplier=1.0,
        target_entity=None,
        target_scope="systemic",
    )

    delta_cut = engine.value_swap(pay_fixed_swap, cut_shock)
    assert delta_cut.pnl_usd == 3_450_000.0
    assert delta_cut.pnl_usd > 0  # Invariant: pay-fixed gains under rate cut


def test_cash_zero_delta(engine: ValuationEngine):
    """PRD 9.4: Cash has zero market or credit delta under stress."""
    cash = engine.portfolio.cash[0]
    shock = ScaledShock(
        bond_spread_shift_bps=200.0,
        loan_pd_increment=0.05,
        lgd_increment=0.10,
        benchmark_yield_shift_bps=150.0,
        scale_multiplier=1.0,
        target_entity=None,
        target_scope="systemic",
    )
    delta = engine.value_cash(cash, shock)
    assert delta.pnl_usd == 0.0
    assert delta.stressed_value_usd == delta.baseline_value_usd
    assert delta.applied_shock_summary == "Unimpacted (Risk-free cash)"


def test_zero_shock_zero_change(engine: ValuationEngine):
    """PRD 13.3 Invariant: Zero shock produces exactly zero P&L."""
    zero_shock = ScaledShock(
        bond_spread_shift_bps=0.0,
        loan_pd_increment=0.0,
        lgd_increment=0.0,
        benchmark_yield_shift_bps=0.0,
        scale_multiplier=0.0,
        target_entity="APEX",
        target_scope="entity",
    )
    result = engine.run_stress_test(zero_shock)
    assert result.total_pnl_usd == 0.0
    assert result.baseline_total_book_value_usd == result.stressed_total_book_value_usd
    assert result.credit_ecl_change_usd == 0.0
    assert result.market_mtm_change_usd == 0.0
    assert result.reconciliation_passed is True


def test_unrelated_entity_exposure_unchanged(engine: ValuationEngine):
    """PRD 13.3 Invariant: Unrelated exposure remains unchanged under entity-scoped shock."""
    apex_shock = build_scaled_shock(
        "CREDIT", impact_score=8, target_entity="APEX", target_scope="entity"
    )
    result = engine.run_stress_test(apex_shock)

    for delta in result.position_deltas:
        if delta.entity_id != "APEX":
            assert delta.pnl_usd == 0.0
            assert "Unimpacted" in delta.applied_shock_summary
            assert delta.stressed_value_usd == delta.baseline_value_usd

        else:
            assert delta.pnl_usd < 0.0
            assert delta.applied_shock_summary != "Unimpacted"


def test_full_portfolio_reconciliation_invariants(engine: ValuationEngine):
    """PRD 13.3 Invariant: Sum of position P&L equals total P&L, before + P&L = after."""
    systemic_shock = build_scaled_shock("CREDIT", impact_score=9, target_scope="systemic")
    result = engine.run_stress_test(systemic_shock)

    # 1. Sum of position P&L equals total P&L
    sum_deltas = sum(p.pnl_usd for p in result.position_deltas)
    assert pytest.approx(sum_deltas, abs=0.05) == result.total_pnl_usd

    # 2. Before + P&L = After for each position
    for p in result.position_deltas:
        assert pytest.approx(p.baseline_value_usd + p.pnl_usd, abs=0.02) == p.stressed_value_usd

    # 3. Baseline + Total P&L = Stressed Book Value
    expected_stressed = result.baseline_total_book_value_usd + result.total_pnl_usd
    assert pytest.approx(expected_stressed, abs=0.05) == result.stressed_total_book_value_usd


    # 4. Built-in reconciliation flag must be True
    assert result.reconciliation_passed is True

    # 5. Asset class breakdowns reconcile
    sum_asset_class_pnl = sum(ac.total_pnl_usd for ac in result.asset_class_breakdown)
    assert pytest.approx(sum_asset_class_pnl, abs=0.05) == result.total_pnl_usd

    # 6. Sector breakdowns reconcile
    sum_sector_pnl = sum(s.total_pnl_usd for s in result.sector_breakdown)
    assert pytest.approx(sum_sector_pnl, abs=0.05) == result.total_pnl_usd
