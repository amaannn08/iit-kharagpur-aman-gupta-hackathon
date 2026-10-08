import pytest
from fastapi.testclient import TestClient

from sentinel.api.app import create_app


@pytest.fixture
def client():
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client


def test_replay_status_endpoint(client):
    response = client.get("/api/replay/status")
    assert response.status_code == 200
    data = response.json()
    assert "run_id" in data
    assert "state" in data
    assert "speed" in data
    assert "total_records" in data


def test_replay_lifecycle_flow(client):
    # 1. Reset first
    reset_resp = client.post("/api/replay/reset")
    assert reset_resp.status_code == 200
    run_id = reset_resp.json()["run_id"]

    # 2. Load Scenario
    load_resp = client.post(
        "/api/replay/load",
        json={"scenario_id": "SCENARIO-CREDIT-01", "sources": ["news_demo", "social_demo"]},
    )
    assert load_resp.status_code == 200
    load_data = load_resp.json()
    run_id = load_data["run_id"]
    assert load_data["scenario_id"] == "SCENARIO-CREDIT-01"
    assert load_data["total_records"] > 0
    assert load_data["pending_records"] == load_data["total_records"]

    # 3. Configure Speed
    speed_resp = client.post("/api/replay/speed", json={"speed": 5.0})
    assert speed_resp.status_code == 200
    assert speed_resp.json()["speed"] == 5.0

    # 4. Step one record
    step_resp = client.post("/api/replay/step")
    assert step_resp.status_code == 200
    step_data = step_resp.json()
    assert step_data is not None
    assert step_data["success"] is True
    assert "record" in step_data
    assert "dedup" in step_data
    assert "is_duplicate" in step_data["dedup"]

    # 5. Check status reflects processed count
    status_resp = client.get("/api/replay/status")
    assert status_resp.status_code == 200
    assert status_resp.json()["processed_count"] == 1

    # 6. Check persisted runs
    runs_resp = client.get("/api/replay/runs")
    assert runs_resp.status_code == 200
    runs = runs_resp.json()
    assert any(r["run_id"] == run_id for r in runs)

    # 7. Check persisted records for run
    records_resp = client.get(f"/api/replay/runs/{run_id}/records")
    assert records_resp.status_code == 200
    records = records_resp.json()
    assert len(records) >= 1
    assert "is_duplicate" in records[0]
