"""Unit tests for FastAPI endpoints: health, datasets, and scenarios."""

from fastapi.testclient import TestClient

from sentinel.api.app import app

client = TestClient(app)


def test_health_endpoint():
    """Verify health endpoint returns 200, offline mode, and dataset readiness."""
    response = client.get("/api/health")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "ok"
    assert data["project"] == "S&P Sentinel"
    assert data["datasets_ready"] is True
    assert data["environment"]["offline_only"] is True
    assert data["environment"]["external_apis"] is False
    assert data["environment"]["database_ready"] is True
    assert "timestamp" in data


def test_datasets_manifest_endpoint():
    """Verify /api/datasets serves authoritative manifest metadata."""
    response = client.get("/api/datasets")
    assert response.status_code == 200

    manifest = response.json()
    assert manifest["manifest_version"] == "1.0"
    assert "Aman Gupta" in manifest["author"]
    assert manifest["compliance"]["synthetic_data_disclosed"] is True
    assert manifest["compliance"]["confidential_client_data"] is False

    datasets = manifest["datasets"]
    assert len(datasets) == 10

    # Ensure news and social are present with cryptographic hashes
    file_paths = [ds["file_path"] for ds in datasets]
    assert "data/news_demo.csv" in file_paths
    assert "data/social_demo.csv" in file_paths
    assert "data/wholesale_positions.json" in file_paths

    for ds in datasets:
        assert len(ds["sha256"]) == 64
        assert ds["byte_size"] > 0
        assert "license" in ds


def test_scenarios_endpoint():
    """Verify /api/datasets/scenarios returns all preconfigured crisis shocks."""
    response = client.get("/api/datasets/scenarios")
    assert response.status_code == 200

    payload = response.json()
    scenarios = payload.get("scenarios", [])
    assert len(scenarios) == 3

    scenario_ids = [s["scenario_id"] for s in scenarios]
    assert "SCENARIO-CREDIT-01" in scenario_ids
    assert "SCENARIO-RATE-01" in scenario_ids
    assert "SCENARIO-SUPPLY-01" in scenario_ids
