"""Integration tests for RiskSignal streaming and query API (PRD Section 6.2 & 16 M3)."""

import pytest
from fastapi.testclient import TestClient

from sentinel.api.app import create_app


@pytest.fixture
def client():
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client


def test_signals_streaming_and_query_endpoints(client):
    # 1. Reset and load scenario
    client.post("/api/replay/reset")
    load_resp = client.post(
        "/api/replay/load",
        json={"scenario_id": "SCENARIO-CREDIT-01", "sources": ["news_demo"]},
    )
    assert load_resp.status_code == 200
    run_id = load_resp.json()["run_id"]

    # 2. Step one record to emit signal
    step_resp = client.post("/api/replay/step")
    assert step_resp.status_code == 200
    step_data = step_resp.json()
    assert step_data is not None
    assert "signal" in step_data
    sig = step_data["signal"]
    assert sig is not None
    signal_id = sig["signal_id"]
    assert sig["run_id"] == run_id
    assert "sentiment" in sig
    assert "event" in sig
    assert "impact" in sig

    # 3. List latest signals
    list_resp = client.get("/api/signals?limit=10")
    assert list_resp.status_code == 200
    signals = list_resp.json()
    assert len(signals) >= 1
    assert any(s["signal_id"] == signal_id for s in signals)

    # 4. Get signal by ID
    get_resp = client.get(f"/api/signals/{signal_id}")
    assert get_resp.status_code == 200
    full_sig = get_resp.json()
    assert full_sig["signal_id"] == signal_id
    assert full_sig["schema_version"] == "1.0"
    assert "probabilities" in full_sig["sentiment"]

    # 5. Get signals by run ID
    run_sigs_resp = client.get(f"/api/signals/run/{run_id}")
    assert run_sigs_resp.status_code == 200
    run_sigs = run_sigs_resp.json()
    assert len(run_sigs) >= 1
    assert run_sigs[0]["signal_id"] == signal_id

    # 6. Verify since filtering query parameter
    since_resp = client.get(f"/api/signals?since={sig['processed_at']}")
    assert since_resp.status_code == 200
    since_sigs = since_resp.json()
    assert any(s["signal_id"] == signal_id for s in since_sigs)

    # 7. Verify PS R3 literal file sink (data/signals.jsonl)
    from pathlib import Path
    sink_file = Path("data/signals.jsonl")
    assert sink_file.exists()
    assert sink_file.stat().st_size > 0
