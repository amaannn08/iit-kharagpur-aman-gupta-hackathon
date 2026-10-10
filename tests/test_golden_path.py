"""Golden-path integration tests (Item 12).

Validates end-to-end integration:
1. Headline ingestion -> entity linking -> event classification -> impact scoring
   -> action eligibility -> automatic stress test trigger -> full reconciliation.
2. Low impact / irrelevant stories are NOT stressed.
3. Duplicate stories act once (deduplication suppression).
4. Non-held issuer reports NO_EXPOSURE status.
"""

import json
from dataclasses import dataclass

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from sentinel.api.app import create_app
from sentinel.config import settings

HEADLINE = "{name} misses bond payment, files for Chapter 11 bankruptcy protection"


@dataclass
class IssuerInfo:
    ticker: str
    name: str


@pytest.fixture
def client():
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def reset_state():
    from sentinel.api.routes.analyze import deduplicator
    from sentinel.api.routes.stress import stress_engine

    deduplicator.reset()
    stress_engine.reset_triggers()


@pytest.fixture
def held_issuer() -> IssuerInfo:
    """Select a real wholesale book corporate borrower dynamically."""
    book_path = settings.data_dir / "portfolio" / "wholesale_real.json"
    with open(book_path, encoding="utf-8") as f:
        data = json.load(f)
    for pos in data["positions"]:
        t = pos["entity_id"]
        if t not in ("MACRO", "TREASURY") and pos["counterparty_name"]:
            return IssuerInfo(ticker=t, name=pos["counterparty_name"])
    return IssuerInfo(ticker="T", name="AT&T")


@pytest.fixture
def non_held_issuer() -> IssuerInfo:
    """Select a real S&P 500 company not held in the portfolio."""
    book_path = settings.data_dir / "portfolio" / "wholesale_real.json"
    with open(book_path, encoding="utf-8") as f:
        w_data = json.load(f)
    eq_path = settings.data_dir / "portfolio" / "equity_sleeve.json"
    eq_held = set()
    if eq_path.exists():
        with open(eq_path, encoding="utf-8") as f:
            eq_data = json.load(f)
            eq_held = {p["entity_id"] for p in eq_data["positions"]}

    held_set = {p["entity_id"] for p in w_data["positions"]} | eq_held

    ent_df = pd.read_csv(settings.data_dir / "universe" / "entities.csv")
    for _, row in ent_df.iterrows():
        t = row["ticker"]
        if (
            t not in held_set
            and not row.get("is_synthetic", False)
            and not row.get("is_historical", False)
        ):
            return IssuerInfo(ticker=t, name=row["canonical_name"])
    return IssuerInfo(ticker="A", name="Agilent Technologies")


def test_headline_to_reconciled_stress(client: TestClient, held_issuer: IssuerInfo):
    r = client.post(
        "/api/analyze",
        json={"text": HEADLINE.format(name=held_issuer.name), "source_type": "news"},
    )
    assert r.status_code == 200
    body = r.json()
    sig = body["signals"][0]
    assert sig["entity"]["ticker"] == held_issuer.ticker
    assert sig["event"]["label"] == "CREDIT"
    assert sig["impact"]["score"] > 7
    assert sig["eligible_for_action"] is True

    assert len(body["stress_runs"]) >= 1
    run = body["stress_runs"][0]

    full = client.get(f"/api/stress/{run['stress_id']}").json()
    assert full["reconciliation_passed"] is True
    assert full["status"] != "NO_EXPOSURE"
    assert full["total_pnl_usd"] < 0
    assert (
        abs(sum(p["pnl_usd"] for p in full["position_deltas"]) - full["total_pnl_usd"])
        < 0.05
    )
    attr = full["attribution"]
    assert abs(sum(attr["by_component"].values()) - full["total_pnl_usd"]) < 0.05


def test_low_impact_is_not_stressed(client: TestClient):
    r = client.post(
        "/api/analyze",
        json={"text": "Apple opens a new store in Mumbai", "source_type": "news"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["stress_runs"] == []
    sig = body["signals"][0]
    assert (
        "IMPACT_BELOW_ACTION_THRESHOLD" in sig["action_block_reasons"]
        or sig["event"]["label"] == "OTHER"
    )


def test_duplicate_story_acts_once(client: TestClient, held_issuer: IssuerInfo):
    text = HEADLINE.format(name=held_issuer.name)

    r1 = client.post("/api/analyze", json={"text": text, "source_type": "news"})
    assert r1.status_code == 200
    assert r1.json()["is_duplicate"] is False
    assert len(r1.json()["stress_runs"]) == 1

    r2 = client.post("/api/analyze", json={"text": text, "source_type": "news"})
    assert r2.status_code == 200
    assert r2.json()["is_duplicate"] is True
    assert len(r2.json()["stress_runs"]) == 0


def test_non_held_issuer_reports_no_exposure(
    client: TestClient, non_held_issuer: IssuerInfo
):
    r = client.post(
        "/api/analyze",
        json={"text": HEADLINE.format(name=non_held_issuer.name), "source_type": "news"},
    )
    assert r.status_code == 200
    body = r.json()
    assert len(body["stress_runs"]) >= 1
    run = body["stress_runs"][0]
    full = client.get(f"/api/stress/{run['stress_id']}").json()
    assert full["status"] == "NO_EXPOSURE"
    assert full["total_pnl_usd"] == 0.0
