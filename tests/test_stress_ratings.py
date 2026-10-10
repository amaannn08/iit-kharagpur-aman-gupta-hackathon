"""Tests for rating-tiered spreads and per-loan credit-triangle PD derivation."""

import json
import statistics

from sentinel.config import settings
from sentinel.contracts.stress import LoanPosition, PortfolioSummary
from sentinel.stress.portfolio import WholesalePortfolio
from sentinel.stress.ratings import (
    HY_INDEX_MIX,
    IG_INDEX_MIX,
    RATING_SPREAD_MULTIPLIER,
    index_multiplier,
    rating_bucket,
)
from sentinel.stress.shocks import ScaledShock
from sentinel.stress.valuation import ValuationEngine

STRESS_WINDOWS = settings.data_dir / "market" / "stress_windows.json"


def test_bucket_parsing():
    assert rating_bucket("BB-") == "BB" and rating_bucket("A+") == "A"
    assert rating_bucket("D") == "CCC" and rating_bucket(None) == "BB"


def test_multipliers_monotone():
    order = ["AAA", "AA", "A", "BBB", "BB", "B", "CCC"]
    vals = [RATING_SPREAD_MULTIPLIER[b] for b in order]
    assert vals == sorted(vals)


def test_index_anchors_match_measured_ratio():
    w = json.loads(STRESS_WINDOWS.read_text())["windows"]
    ratios = [x["ig_to_hy_ratio"] for x in w.values() if x.get("ig_to_hy_ratio")]
    measured = statistics.median(ratios)
    assert abs(index_multiplier(IG_INDEX_MIX) / index_multiplier(HY_INDEX_MIX) - measured) < 0.10
    assert abs(index_multiplier(HY_INDEX_MIX) - 1.0) < 0.10


def make_loan(pos_id: str, rating: str, ead: float, lgd: float, pd: float) -> LoanPosition:
    return LoanPosition(
        position_id=pos_id,
        entity_id="BORROWER",
        counterparty_name="Borrower Corp",
        sector="Industrials",
        market_value=ead,
        ead=ead,
        drawn_amount=ead,
        committed_amount=ead,
        baseline_pd=pd,
        lgd=lgd,
        rating=rating,
        maturity_date="2028-12-31",
        interest_rate=0.05,
        sleeve="wholesale",
    )


def portfolio_of(*loans: LoanPosition) -> WholesalePortfolio:
    total_val = sum(ln.market_value for ln in loans)
    summary = PortfolioSummary(
        total_book_value_usd=total_val,
        corporate_loans_value_usd=total_val,
        corporate_bonds_value_usd=0.0,
        cash_reserves_usd=0.0,
        interest_rate_swaps_gross_notional_usd=0.0,
    )
    return WholesalePortfolio(
        portfolio_name="Test Book",
        base_currency="USD",
        valuation_date="2026-03-01",
        summary=summary,
        loans=list(loans),
        bonds=[],
        swaps=[],
        cash=[],
    )


def systemic_shock(spread: float, pd_from_spread: bool = True) -> ScaledShock:
    return ScaledShock(
        bond_spread_shift_bps=spread,
        loan_pd_increment=0.0,
        lgd_increment=0.0,
        benchmark_yield_shift_bps=0.0,
        scale_multiplier=1.0,
        target_entity=None,
        target_scope="systemic",
        pd_from_spread=pd_from_spread,
        rating_tiered=True,
    )


def test_bb_loan_loses_more_than_a_loan_same_exposure():
    a = make_loan("L-A", rating="A", ead=10e6, lgd=0.45, pd=0.0005)
    bb = make_loan("L-BB", rating="BB", ead=10e6, lgd=0.45, pd=0.006)
    eng = ValuationEngine(portfolio_of(a, bb))
    res = eng.run_stress_test(shock=systemic_shock(spread=100, pd_from_spread=True))
    d = {p.position_id: p.pnl_usd for p in res.position_deltas}
    assert d["L-BB"] < d["L-A"] < 0


def test_triangle_ecl_is_lgd_invariant():
    lo = make_loan("L1", rating="BB", ead=10e6, lgd=0.3, pd=0.01)
    hi = make_loan("L2", rating="BB", ead=10e6, lgd=0.8, pd=0.01)
    res = ValuationEngine(portfolio_of(lo, hi)).run_stress_test(
        shock=systemic_shock(spread=100, pd_from_spread=True)
    )
    ecl = [p.incremental_ecl_usd for p in res.position_deltas]
    assert abs(ecl[0] - ecl[1]) < 1.0  # both = EAD * 0.75 * 1% = 75,000
