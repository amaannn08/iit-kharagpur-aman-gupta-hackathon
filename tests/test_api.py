"""Unit tests for FastAPI endpoints: health, datasets, and scenarios."""

import subprocess
import sys

from fastapi.testclient import TestClient

from sentinel.api.app import app
from sentinel.config import settings
from sentinel.storage.db import init_db

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


def test_runtime_database_isolation_and_no_root_db():
    """Verify default database is stored in .runtime and root sentinel.db is not created."""
    init_db()

    root_db = settings.base_dir / "sentinel.db"
    assert not root_db.exists(), f"Forbidden database file detected at repository root: {root_db}"

    runtime_db = settings.base_dir / ".runtime" / "sentinel.db"
    assert runtime_db.exists(), f"Expected runtime database file at {runtime_db}"

    # Also verify lifespan context manager initialization
    with TestClient(app):
        assert not root_db.exists(), f"Forbidden root DB created during app lifespan: {root_db}"


def test_hygiene_verification_passes_with_runtime_db_and_rejects_external_db():
    """Verify verify_hygiene passes with .runtime DB but rejects forbidden external DBs."""
    script_path = settings.base_dir / "scripts" / "verify_hygiene.py"

    # 1. Standard run must pass cleanly
    res = subprocess.run([sys.executable, str(script_path)], capture_output=True, text=True)
    assert res.returncode == 0, f"Hygiene check failed: {res.stdout}\n{res.stderr}"

    # 2. Placing a forbidden db in repo root must trigger failure
    probe_db = settings.base_dir / "forbidden_test.db"
    try:
        probe_db.write_text("probe")
        fail_res = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=True,
            text=True,
        )
        assert fail_res.returncode != 0
        assert "Forbidden extension detected: forbidden_test.db" in fail_res.stderr
    finally:
        if probe_db.exists():
            probe_db.unlink()
