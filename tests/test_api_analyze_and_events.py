"""API tests for manual analysis, SSE events stream, and exports (PRD Section 11 & 12)."""

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


def test_api_manual_analyze_routine_text(client: TestClient):
    """Verify POST /api/analyze processes routine text and blocks actions."""
    payload = {
        "text": "Apex Industrial announced the date for its routine annual shareholder meeting.",
        "source_type": "news",
    }
    resp = client.post("/api/analyze", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    assert "record" in data
    assert "signal" in data
    assert data["record"]["text"] == payload["text"]
    assert data["signal"]["impact"]["score"] < 7
    # Routine announcements do not trigger stress runs
    assert data["stress_run"] is None
    assert data["is_duplicate"] is False


def test_api_manual_analyze_severe_credit_triggers_stress(client: TestClient):
    """Verify POST /api/analyze processes severe distress and triggers automated stress test."""
    payload = {
        "text": (
            "Apex Industrial $APEX files emergency Chapter 11 bankruptcy petition following severe "
            "debt default, triggering systemic contagion across nationwide supply chain network."
        ),
        "source_type": "news",
    }
    resp = client.post("/api/analyze", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    assert data["signal"]["entity"]["name"] is not None
    assert data["signal"]["impact"]["score"] >= 8
    assert data["signal"]["event"]["label"] == "CREDIT"
    assert data["signal"]["eligible_for_action"] is True

    # Automatic Module B stress test must be triggered
    assert data["stress_run"] is not None
    assert data["stress_run"]["trigger_type"] == "EVENT_TRIGGERED"
    assert data["stress_run"]["target_entity"] == "APEX"
    assert data["stress_run"]["total_pnl_usd"] < 0.0
    assert data["stress_run"]["reconciliation_passed"] is True


def test_api_manual_analyze_exact_duplicate_suppression(client: TestClient):
    """Verify repeated manual submissions are flagged as duplicate."""
    payload = {
        "text": "Quantum Semiconductor $QSEM reports Q3 revenue growth beating analyst estimates.",
        "source_type": "social",
    }
    resp1 = client.post("/api/analyze", json=payload)
    assert resp1.status_code == 200
    assert resp1.json()["is_duplicate"] is False

    resp2 = client.post("/api/analyze", json=payload)
    assert resp2.status_code == 200
    assert resp2.json()["is_duplicate"] is True
    assert resp2.json()["duplicate_group_id"] is not None


def test_api_exports_json_and_csv(client: TestClient):
    """Verify GET /api/exports/{run_id} returns valid JSON and CSV audit packages."""
    # 1. First run a step to produce a record
    client.post("/api/replay/load", json={"scenario_id": "test", "sources": ["news_demo"]})
    step_resp = client.post("/api/replay/step")
    run_id = step_resp.json()["signal"]["run_id"]

    # 2. Export as JSON
    json_resp = client.get(f"/api/exports/{run_id}?format=json")
    assert json_resp.status_code == 200
    json_data = json_resp.json()
    assert "export_metadata" in json_data
    assert "records" in json_data
    assert "signals" in json_data
    assert len(json_data["records"]) >= 1

    # 3. Export as CSV
    csv_resp = client.get(f"/api/exports/{run_id}?format=csv")
    assert csv_resp.status_code == 200
    assert csv_resp.headers["content-type"].startswith("text/csv")
    csv_text = csv_resp.text
    assert "record_id,source_id,source_type,text" in csv_text


def test_api_direct_prd_aliases(client: TestClient):
    """Verify exact PRD Section 12 endpoints: /api/portfolio and /api/stress."""
    # GET /api/portfolio
    port_resp = client.get("/api/portfolio")
    assert port_resp.status_code == 200
    expected_name = "Synthetic Wholesale Institutional Credit & Rates Portfolio"
    assert port_resp.json()["portfolio_name"] == expected_name

    # POST /api/stress
    stress_resp = client.post(
        "/api/stress",
        json={
            "event_class": "MACRO",
            "impact_score": 8,
            "target_scope": "systemic",
        },
    )
    assert stress_resp.status_code == 200
    stress_data = stress_resp.json()
    assert stress_data["event_class"] == "MACRO"
    assert stress_data["reconciliation_passed"] is True

    # GET /api/stress/{id}
    stress_id = stress_data["stress_id"]
    detail_resp = client.get(f"/api/stress/{stress_id}")
    assert detail_resp.status_code == 200
    assert detail_resp.json()["stress_id"] == stress_id
