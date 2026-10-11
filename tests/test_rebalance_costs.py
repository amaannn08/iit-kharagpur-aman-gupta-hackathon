"""Tests for Module A: costs, net returns, no-trade band, and block bootstrap CI."""

import json
from pathlib import Path

from sentinel.rebalance.engine import IndexRebalancer

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_no_trade_band_reduces_turnover():
    # Test that setting no_trade_band reduces or keeps equal turnover for small score updates
    idx_noband = IndexRebalancer(k=1.0, no_trade_band=0.0)
    idx_band = IndexRebalancer(k=1.0, no_trade_band=0.01)  # 1% band

    # Small update to AAPL
    rec1 = idx_noband.update("AAPL", 0.05)
    rec2 = idx_band.update("AAPL", 0.05)

    assert rec1 is not None and rec2 is not None
    assert rec2.turnover <= rec1.turnover


def test_no_trade_band_keeps_weight_put_on_small_deltas():
    idx = IndexRebalancer(k=1.0, no_trade_band=0.05)  # 5% band
    init_w = dict(idx.weights)
    rec = idx.update("AAPL", 0.01)
    assert rec is not None
    # For a small delta under the band, weights stay identical to base weights
    assert rec.turnover == 0.0
    assert idx.weights["AAPL"] == init_w["AAPL"]


def test_module_a_backtest_costs_and_ci():
    path = REPO_ROOT / "docs" / "module_a_backtest.json"
    assert path.exists(), "docs/module_a_backtest.json must exist"
    data = json.loads(path.read_text())

    for run in data["runs"]:
        # 1. With cost_bps=0, net active return equals gross active return
        costs = run["net_costs"]
        assert "cost_0bps" in costs
        assert "cost_5bps" in costs
        assert "cost_10bps" in costs
        assert costs["cost_0bps"]["net_active_annual_return"] == run["active_annual_return"]

        # 2. Net return with 10 bps is less than net return with 0 bps (if turnover > 0)
        if run["annual_turnover"] > 0:
            assert (
                costs["cost_10bps"]["net_active_annual_return"]
                <= costs["cost_0bps"]["net_active_annual_return"]
            )

        # 3. Bootstrap CI contains the point estimate
        ci = run["active_annual_return_ci95"]
        assert len(ci) == 2
        assert ci[0] <= run["active_annual_return"] <= ci[1]

        # 4. Break-even cost is positive
        assert run["break_even_cost_bps"] >= 0.0
