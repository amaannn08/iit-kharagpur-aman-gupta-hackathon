"""Module A: sentiment-driven mock index rebalancer (PS Section 3, PRD Section 10)."""

from datetime import datetime, timedelta

from fastapi.testclient import TestClient

from sentinel.api.app import create_app
from sentinel.rebalance import IndexRebalancer

T0 = datetime(2026, 3, 2, 9, 0)


def test_positive_sentiment_increases_and_negative_decreases_weight():
    idx = IndexRebalancer()
    base = idx.base["AAPL"]
    idx.update("AAPL", 0.9, T0)
    up = idx.weights["AAPL"]
    idx.update("BA", -0.9, T0)
    assert up > base and idx.weights["BA"] < base
    assert abs(sum(idx.weights.values()) - 1.0) < 1e-5
    assert idx.history[-1].reasons["BA"].startswith("decrease")


def test_caps_long_only_and_sum_to_one_under_extreme_sentiment():
    idx = IndexRebalancer(k=50.0)
    for t in ("AAPL", "MSFT", "ADBE", "CSCO", "INTC"):  # all Information Technology
        idx.update(t, 1.0, T0)
    idx.update("CVX", -1.0, T0)
    w = idx.weights
    assert all(v >= 0 for v in w.values())
    assert max(w.values()) <= idx.name_cap + 1e-6
    it = sum(v for t, v in w.items() if idx.universe[t] == "Information Technology")
    assert it <= idx.sector_cap + 1e-6
    assert abs(sum(w.values()) - 1.0) < 1e-5
    assert w["CVX"] == 0.0


def test_sentiment_decays_toward_neutral_and_turnover_is_recorded():
    idx = IndexRebalancer(halflife_days=5)
    idx.update("META", 1.0, T0)
    ema0 = idx.ema["META"]
    idx.update("META", 0.0, T0 + timedelta(days=5))
    assert idx.ema["META"] < ema0 * 0.5 + 1e-9  # halved by decay, then blended with 0
    assert all(r.turnover >= 0 for r in idx.history)
    assert idx.history[1].turnover > 0


def test_signals_feed_index_through_api_and_reset():
    with TestClient(create_app()) as client:
        client.post("/api/index/reset")
        base = client.get("/api/index/current").json()["base_weights"]["AAPL"]
        client.post(
            "/api/analyze",
            json={"text": "Apple shares surge after record quarterly profit beats estimates"},
        )
        current = client.get("/api/index/current").json()
        assert current["weights"]["AAPL"] > base
        assert "mock index" in current["label"].lower()
        history = client.get("/api/index/history").json()
        assert len(history) >= 2 and history[-1]["trigger_ticker"] == "AAPL"
        assert client.post("/api/index/reset").json()["rebalances"] == 0
