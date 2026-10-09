import pytest
from fastapi.testclient import TestClient

from sentinel.api.app import create_app
from sentinel.storage.db import engine, init_db
from sentinel.storage.models import Base


@pytest.fixture(autouse=True)
def fresh_db():
    Base.metadata.drop_all(bind=engine)
    init_db()
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client


def test_api_get_portfolio(client: TestClient):
    """Verify /api/stress/portfolio returns wholesale portfolio with funded segregation."""
    resp = client.get("/api/stress/portfolio")

    assert resp.status_code == 200
    data = resp.json()
    assert data["portfolio_name"] == "Synthetic Wholesale Institutional Credit & Rates Portfolio"
    assert "summary" in data
    # Funded book = $500M synthetic wholesale + $50M retail/SME sleeve from real transactions
    assert data["funded_value_by_sleeve_usd"]["wholesale"] == 500_000_000.0
    assert abs(data["funded_value_by_sleeve_usd"]["retail_sme"] - 50_000_000.0) < 0.01
    assert abs(data["summary"]["total_book_value_usd"] - 550_000_000.0) < 0.01
    wholesale_loans = [p for p in data["loans"] if p["sleeve"] == "wholesale"]
    assert len(wholesale_loans) == 5
    assert len(data["loans"]) > 5  # retail tranches
    assert len(data["bonds"]) == 5
    assert len(data["swaps"]) == 2
    assert len(data["cash"]) == 1
    # derivative notional is metadata, never part of funded book value (PRD 9.1)
    assert data["summary"]["interest_rate_swaps_gross_notional_usd"] == 150_000_000.0


def test_api_simulate_manual_stress(client: TestClient):
    """Verify /api/stress/simulate triggers manual sandbox stress simulation and saves results."""
    payload = {
        "event_class": "CREDIT",
        "impact_score": 8,
        "target_entity": "APEX",
        "target_scope": "entity",
        "is_easing": False,
        "run_id": "test-manual-run",
    }
    resp = client.post("/api/stress/simulate", json=payload)
    assert resp.status_code == 200
    result = resp.json()

    assert result["trigger_type"] == "USER_TRIGGERED"
    assert result["event_class"] == "CREDIT"
    assert result["impact_score"] == 8
    assert result["target_entity"] == "APEX"
    assert result["total_pnl_usd"] < 0.0
    assert result["reconciliation_passed"] is True
    deltas = result["position_deltas"]
    assert len([d for d in deltas if d["sleeve"] == "wholesale"]) == 13
    portfolio = client.get("/api/stress/portfolio").json()
    n_positions = sum(len(portfolio[k]) for k in ("loans", "bonds", "swaps", "cash"))
    assert len(deltas) == n_positions  # every position is revalued
    assert {s["sleeve"] for s in result["sleeve_breakdown"]} == {"wholesale", "retail_sme"}

    # Now verify it appears in /api/stress/runs
    list_resp = client.get("/api/stress/runs")
    assert list_resp.status_code == 200
    runs = list_resp.json()
    assert len(runs) >= 1
    assert runs[0]["stress_id"] == result["stress_id"]

    # Now verify detail fetch from /api/stress/{stress_id}
    detail_resp = client.get(f"/api/stress/{result['stress_id']}")
    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    assert detail["stress_id"] == result["stress_id"]
    assert detail["total_pnl_usd"] == result["total_pnl_usd"]
