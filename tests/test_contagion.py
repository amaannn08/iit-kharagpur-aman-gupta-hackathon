"""Tests for contagion graph data and multi-hop propagation (Item 8).

Validates:
1. Sector peer edges are symmetric in data/graph_edges.csv.
2. All tickers belong to the universe (data/universe/entities.csv).
3. 0 < transmission_factor <= 0.8 for all edges.
4. Total edge count >= 60.
5. Every edge is computed from price data (no hand-typed correlations or citations).
6. Names without price history (SIVB) have no edges and a shock to them books no contagion.
7. Degree per node is capped at 5; a CREDIT shock to a held issuer reaches a held peer.
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


def _edges():
    with open(settings.data_dir / "graph_edges.csv", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def test_every_edge_is_computed_from_prices():
    for r in _edges():
        assert r["relationship_type"] == "sector_peer"
        assert r["rationale"].startswith("residual return correlation ")
        rho = float(r["rationale"].split()[3])
        assert abs(float(r["transmission_factor"]) - round(min(0.8, 0.9 * rho), 2)) < 0.011
        assert r["evidence"].startswith("data/raw/real/market/")


def test_degree_cap():
    from collections import Counter

    assert max(Counter(r["source_ticker"] for r in _edges()).values()) <= 5


def test_name_without_price_history_has_no_contagion():
    assert not [r for r in _edges() if "SIVB" in (r["source_ticker"], r["target_ticker"])]
    val_engine, _ = StressEngine().get_valuation_engine("real_issuers")
    shock = build_scaled_shock("CREDIT", impact_score=9, target_entity="SIVB", target_scope="entity")
    result = val_engine.run_stress_test(shock, enable_contagion=True)
    assert result.contagion_positions_count == 0


def test_credit_shock_on_held_issuer_reaches_held_peer():
    val_engine, _ = StressEngine().get_valuation_engine("real_issuers")
    held = {p.entity_id for p in val_engine.portfolio.loans + val_engine.portfolio.bonds}
    pair = next((r["source_ticker"], r["target_ticker"]) for r in _edges()
                if r["source_ticker"] in held and r["target_ticker"] in held)  # fmt: skip
    shock = build_scaled_shock("CREDIT", impact_score=9, target_entity=pair[0], target_scope="entity")
    result = val_engine.run_stress_test(shock, enable_contagion=True)
    hit = {p.entity_id for p in result.position_deltas if p.is_contagion and p.pnl_usd < 0}
    assert pair[1] in hit


def test_contagion_graph_network_summary():
    graph = ContagionGraph(settings.data_dir / "graph_edges.csv")
    summary = graph.get_network_summary()
    assert summary["total_edges"] >= 60
    assert summary["total_nodes"] >= 30
    assert set(summary["edge_types"]) == {"sector_peer"}
