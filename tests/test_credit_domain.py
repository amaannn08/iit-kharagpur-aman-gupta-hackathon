"""Unit tests for Early-Warning Watchlist, IFRS 9 Loan Staging, CET1 Capital Impact, and Reverse Stress."""

import pytest

from sentinel.stress.engine import StressEngine
from sentinel.stress.staging import StagingAndCapitalEngine


@pytest.fixture
def stress_engine():
    return StressEngine(portfolio_path="data/portfolio/demo_book.json")


def test_ews_watchlist_generation(stress_engine: StressEngine):
    """Verify Early-Warning Watchlist generates scores and obligor statuses."""
    items = stress_engine.get_ews_watchlist()
    assert len(items) > 0
    statuses = {item["status"] for item in items}
    assert statuses.issubset({"GREEN", "AMBER", "RED"})

    # Check obligor fields
    first = items[0]
    assert "entity_id" in first
    assert "counterparty_name" in first
    assert "ews_score" in first
    assert 0 <= first["ews_score"] <= 100
    assert "recommended_action" in first
    assert len(first["triggers"]) > 0


def test_ifrs9_staging_and_staging_cliff(stress_engine: StressEngine):
    """Verify IFRS 9 staging classifies loans, separates EAD from ECL, and detects staging cliff jumps."""
    # Baseline staging (no shock): all loans performing in Stage 1
    staging_base = stress_engine.get_ifrs9_staging()
    s1_ead = staging_base["stage_1"]["exposure_usd"]
    s1_ecl = staging_base["stage_1"]["ecl_usd"]
    assert s1_ead > 0
    assert s1_ecl > 0
    # Invariant: ECL is strictly less than EAD
    assert s1_ecl < s1_ead
    assert staging_base["total_baseline_ecl_usd"] < s1_ead
    assert staging_base["stage_2"]["count"] == 0

    # Under severe COVID-2020 shock: loans migrate to Stage 2 with staging cliff jump
    staging_covid = stress_engine.get_ifrs9_staging(scenario_id="HIST-COVID_2020")
    s2_ead = staging_covid["stage_2"]["exposure_usd"]
    s2_ecl = staging_covid["stage_2"]["ecl_usd"]
    assert s2_ead > 0
    assert s2_ecl > 0
    assert s2_ecl < s2_ead
    assert staging_covid["staging_cliff_total_jump_usd"] > 0
    assert staging_covid["total_stressed_ecl_usd"] > staging_covid["total_baseline_ecl_usd"]

    total_ead = (
        staging_covid["stage_1"]["exposure_usd"]
        + staging_covid["stage_2"]["exposure_usd"]
        + staging_covid["stage_3"]["exposure_usd"]
    )
    total_ecl = staging_covid["total_stressed_ecl_usd"]
    assert total_ecl < total_ead

    # When stressed PD spikes, staging cliff jump is positive
    engine = StagingAndCapitalEngine(stress_engine.portfolio)
    loan0 = stress_engine.portfolio.loans[0]
    stressed_pds = {loan0.position_id: loan0.baseline_pd * 4.0}
    report = engine.evaluate_staging(stressed_pds)
    assert report.stage_2_count >= 1
    assert report.staging_cliff_total_jump_usd > 0
    assert any(m.position_id == loan0.position_id for m in report.migrations)


def test_cet1_capital_impact(stress_engine: StressEngine):
    """Verify CET1 ratio and basis point impact calculation."""
    # Zero loss: baseline CET1 preserved, 0 bps delta
    cap_zero = stress_engine.get_capital_impact(total_pnl_usd=0.0)
    assert cap_zero["cet1_delta_bps"] == 0
    assert cap_zero["baseline_cet1_ratio"] > 0.08

    # $20M loss: CET1 decreases, negative bps delta
    cap_loss = stress_engine.get_capital_impact(total_pnl_usd=-20_000_000.0)
    assert cap_loss["stressed_cet1_ratio"] < cap_zero["baseline_cet1_ratio"]
    assert cap_loss["cet1_delta_bps"] < 0
    assert cap_loss["capital_surplus_usd"] < cap_zero["capital_surplus_usd"]


def test_reverse_stress_testing_bisection(stress_engine: StressEngine):
    """Verify reverse stress test finds shock multiplier breaching CET1 floor and sub-multiplier does not."""
    target_floor = 0.08
    res = stress_engine.run_reverse_stress(
        scenario_id="HIST-COVID_2020",
        target_cet1_floor=target_floor,
    )
    assert res["scenario_id"] == "HIST-COVID_2020"
    assert res["breach_found"] is True
    mult = res["breach_multiplier"]
    assert mult > 0.1
    assert res["iterations"] > 1
    assert res["breach_loss_usd"] > 0

    # Test that the found multiplier actually breaches the target floor (or within 1 bp tolerance)
    res_at_mult = stress_engine.run_scenario("HIST-COVID_2020", scale_factor=mult)
    cap_at_mult = stress_engine.get_capital_impact(res_at_mult.total_pnl_usd)
    assert cap_at_mult["stressed_cet1_ratio"] <= target_floor + 1e-4

    # Test that a multiplier below tolerance does NOT breach the target floor
    mult_below = max(0.1, mult - 0.05)
    res_below = stress_engine.run_scenario("HIST-COVID_2020", scale_factor=mult_below)
    cap_below = stress_engine.get_capital_impact(res_below.total_pnl_usd)
    assert cap_below["stressed_cet1_ratio"] > target_floor
