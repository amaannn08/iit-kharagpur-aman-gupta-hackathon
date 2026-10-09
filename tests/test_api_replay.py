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


def test_replay_sources_are_registered_with_honest_badges(client):
    sources = {s["source"]: s for s in client.get("/api/replay/sources").json()}
    assert sources["news_demo"]["badge"] == "SYNTHETIC SCENARIO"
    assert sources["polygon_2023"]["badge"] == "HISTORICAL REPLAY"
    assert sources["polygon_2023"]["available"] is True
    assert sources["gdelt_live"]["badge"] == "LIVE CAPTURE"


def test_load_real_gdelt_snapshot_and_reject_unknown_source(client):
    client.post("/api/replay/reset")
    status = client.post(
        "/api/replay/load", json={"scenario_id": "gdelt", "sources": ["gdelt_snapshot"]}
    ).json()
    assert status["total_records"] >= 2000
    assert status["source_badges"] == ["HISTORICAL REPLAY"]
    bad = client.post("/api/replay/load", json={"scenario_id": "x", "sources": ["nope"]})
    assert bad.status_code == 400


def test_append_queues_only_new_live_records(client, tmp_path, monkeypatch):
    from sentinel.config import settings

    live = tmp_path / "live.csv"
    header = "record_id,source_id,source_type,headline,body,published_at,timestamp_quality,simulated_at,is_synthetic,primary_entity_id\n"
    row = "{rid},gdelt_gkg_v2,news,{h},,2026-10-09T08:{m}:00Z,original,,false,\n"
    live.write_text(
        header + row.format(rid="gd-1", h="Fed raises rates by 75 basis points", m="00")
    )
    monkeypatch.setitem(settings.replay_sources, "test_live", (str(live), "news", "LIVE CAPTURE"))

    client.post("/api/replay/reset")
    first = client.post(
        "/api/replay/load", json={"scenario_id": "live", "sources": ["test_live"]}
    ).json()
    assert first["total_records"] == 1 and first["source_badges"] == ["LIVE CAPTURE"]
    with open(live, "a") as f:  # the recorder appends a new record
        f.write(row.format(rid="gd-2", h="ECB cuts its deposit rate unexpectedly", m="15"))
    after = client.post("/api/replay/append", json={"source": "test_live"}).json()
    assert after["total_records"] == 2 and after["pending_records"] == 2
    again = client.post("/api/replay/append", json={"source": "test_live"}).json()
    assert again["total_records"] == 2  # nothing new
