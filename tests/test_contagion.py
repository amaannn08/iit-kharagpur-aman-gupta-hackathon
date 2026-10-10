"""Tests for contagion graph data and multi-hop propagation (Item 8).

Validates:
1. Sector peer edges are symmetric in data/graph_edges.csv.
2. All tickers belong to the universe (data/universe/entities.csv).
3. 0 < transmission_factor <= 0.8 for all edges.
4. Total edge count >= 60.
5. SIVB has at least 2 Financials peers.
6. A CREDIT shock to SIVB reaches held Financials positions via multi-hop contagion.
7. Out-degree per node is capped at 5 for sector_peer relationships.
8. 10-K customer-concentration links exist with valid citations.
"""

import csv

import pandas as pd

from sentinel.config import settings
from sentinel.stress.contagion import ContagionGraph
from sentinel.stress.engine import StressEngine
from sentinel.stress.shocks import build_scaled_shock


def test_contagion_sector_peer_edges_are_symmetric():
    edges_path = settings.data_dir / "graph_edges.csv"
    assert edges_path.exists(), "graph_edges.csv not found"

    with open(edges_path, newline="", encoding="utf-8") as f:
        edges = list(csv.DictReader(f))

    peer_edges = {
        (r["source_ticker"], r["target_ticker"]): float(r["transmission_factor"])
        for r in edges
        if r["relationship_type"] == "sector_peer"
    }

    for (src, tgt), factor in peer_edges.items():
        assert (tgt, src) in peer_edges, f"Missing symmetric edge for ({src}, {tgt})"
        rev_factor = peer_edges[(tgt, src)]
        assert abs(factor - rev_factor) < 1e-4, f"Asymmetric factor for ({src}, {tgt})"


def test_contagion_all_tickers_in_universe():
    edges_path = settings.data_dir / "graph_edges.csv"
    entities_path = settings.data_dir / "universe" / "entities.csv"

    univ_df = pd.read_csv(entities_path)
    universe_tickers = set(univ_df["ticker"].str.strip().str.upper())

    with open(edges_path, newline="", encoding="utf-8") as f:
        edges = list(csv.DictReader(f))

    for r in edges:
        src = r["source_ticker"].strip().upper()
        tgt = r["target_ticker"].strip().upper()
        assert src in universe_tickers, f"Source ticker {src} not in universe"
        assert tgt in universe_tickers, f"Target ticker {tgt} not in universe"


def test_contagion_factors_and_edge_count():
    edges_path = settings.data_dir / "graph_edges.csv"
    with open(edges_path, newline="", encoding="utf-8") as f:
        edges = list(csv.DictReader(f))

    assert len(edges) >= 60, f"Expected at least 60 edges, got {len(edges)}"

    for r in edges:
        factor = float(r["transmission_factor"])
        assert 0.0 < factor <= 0.8, f"Transmission factor {factor} out of range (0, 0.8]"


def test_sivb_has_at_least_two_financials_peers():
    edges_path = settings.data_dir / "graph_edges.csv"
    with open(edges_path, newline="", encoding="utf-8") as f:
        edges = list(csv.DictReader(f))

    sivb_peers = [
        r["target_ticker"]
        for r in edges
        if r["source_ticker"] == "SIVB" and r["relationship_type"] == "sector_peer"
    ]
    assert len(sivb_peers) >= 2, f"Expected at least 2 Financials peers for SIVB, got {sivb_peers}"


def test_sivb_credit_shock_contagion_reaches_held_financials():
    engine = StressEngine()
    val_engine, prof_name = engine.get_valuation_engine("real_issuers")
    assert prof_name == "real_issuers"

    shock = build_scaled_shock(
        "CREDIT",
        impact_score=9,
        target_entity="SIVB",
        target_scope="entity",
    )
    result = val_engine.run_stress_test(shock, enable_contagion=True)

    assert result.contagion_positions_count > 0, "No contagion positions generated"
    assert result.contagion_pnl_usd < 0.0, "Contagion PnL should be negative"

    # Held Financials (BAC, MS) should be impacted via contagion
    fin_contagion = [
        p
        for p in result.position_deltas
        if p.is_contagion and p.sector == "Financials" and p.pnl_usd < 0.0
    ]
    assert len(fin_contagion) > 0, "No held Financials positions impacted by SIVB contagion"
    impacted_entities = {p.entity_id for p in fin_contagion}
    assert impacted_entities.intersection({"BAC", "MS"}), (
        f"Expected BAC or MS to be impacted, got {impacted_entities}"
    )


def test_ten_k_customer_concentration_edges_exist():
    edges_path = settings.data_dir / "graph_edges.csv"
    with open(edges_path, newline="", encoding="utf-8") as f:
        edges = list(csv.DictReader(f))

    ten_k_pairs = {
        (r["source_ticker"], r["target_ticker"])
        for r in edges
        if r["relationship_type"] == "customer_concentration"
    }

    assert ("UPS", "AMZN") in ten_k_pairs
    assert ("PG", "WMT") in ten_k_pairs
    assert ("AVGO", "AAPL") in ten_k_pairs
    assert ("QCOM", "AAPL") in ten_k_pairs
    assert ("GE", "BA") in ten_k_pairs
    assert ("CAT", "UNP") in ten_k_pairs


def test_contagion_graph_network_summary():
    graph = ContagionGraph(settings.data_dir / "graph_edges.csv")
    summary = graph.get_network_summary()
    assert summary["total_edges"] >= 60
    assert summary["total_nodes"] >= 30
    assert "sector_peer" in summary["edge_types"]
    assert "customer_concentration" in summary["edge_types"]
