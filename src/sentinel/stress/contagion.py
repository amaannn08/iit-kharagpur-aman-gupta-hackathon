"""Counterparty & Supply Chain Contagion Graph Engine (PRD Section 9.3 & Bug B6 fix).

Loads data/graph_edges.csv and computes second-order multi-hop shock propagation
across customer-supplier and credit linkages using transmission factors and hop decay.
"""

import csv
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class ContagionEdge:
    source_ticker: str
    target_ticker: str
    relationship_type: str
    transmission_factor: float
    sign: int
    rationale: str


class ContagionGraph:
    """Directed contagion network for second-order risk propagation."""

    def __init__(self, edges_csv_path: Optional[Path] = None) -> None:
        self.edges_csv_path = (
            edges_csv_path
            if edges_csv_path
            else Path(__file__).resolve().parent.parent.parent.parent
            / "data"
            / "graph_edges.csv"
        )
        self.edges: List[ContagionEdge] = []
        self.adjacency: Dict[str, List[ContagionEdge]] = {}
        self._load_edges()

    def _load_edges(self) -> None:
        if not self.edges_csv_path.exists():
            logger.warning("Contagion graph edges not found at %s", self.edges_csv_path)
            return

        with open(self.edges_csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    edge = ContagionEdge(
                        source_ticker=row["source_ticker"].strip().upper(),
                        target_ticker=row["target_ticker"].strip().upper(),
                        relationship_type=row.get("relationship_type", "counterparty"),
                        transmission_factor=float(row.get("transmission_factor", 0.5)),
                        sign=int(row.get("sign", 1)),
                        rationale=row.get("rationale", ""),
                    )
                    self.edges.append(edge)
                    self.adjacency.setdefault(edge.source_ticker, []).append(edge)
                except Exception as exc:
                    logger.warning("Error parsing graph edge row %s: %s", row, exc)

        logger.info(
            "Loaded %d contagion edges across %d source nodes from %s",
            len(self.edges),
            len(self.adjacency),
            self.edges_csv_path,
        )

    def get_contagion_targets(
        self,
        source_ticker: str,
        max_hops: int = 2,
        hop_decay: float = 0.60,
    ) -> Dict[str, Tuple[float, int]]:
        """Compute downstream contagion targets and effective transmission factors.

        Returns a mapping:
            {target_ticker: (effective_transmission_factor, hop_distance)}
        """
        source = source_ticker.strip().upper()
        if source not in self.adjacency or max_hops < 1:
            return {}

        results: Dict[str, Tuple[float, int]] = {}
        visited = {source}

        # Level 1 (Hop 1)
        level_1_nodes: List[Tuple[str, float]] = []
        for edge in self.adjacency.get(source, []):
            target = edge.target_ticker
            if target not in visited:
                factor = edge.transmission_factor
                results[target] = (factor, 1)
                level_1_nodes.append((target, factor))
                visited.add(target)

        # Level 2 (Hop 2)
        if max_hops >= 2:
            for l1_node, l1_factor in level_1_nodes:
                for edge in self.adjacency.get(l1_node, []):
                    target = edge.target_ticker
                    if target not in visited:
                        factor_hop2 = l1_factor * edge.transmission_factor * hop_decay
                        results[target] = (round(factor_hop2, 4), 2)
                        visited.add(target)

        return results

    def get_network_summary(self) -> dict:
        """Return structural metrics of the loaded graph."""
        nodes = set()
        for edge in self.edges:
            nodes.add(edge.source_ticker)
            nodes.add(edge.target_ticker)

        return {
            "total_nodes": len(nodes),
            "total_edges": len(self.edges),
            "node_list": sorted(list(nodes)),
            "edge_types": sorted(list({e.relationship_type for e in self.edges})),
        }
