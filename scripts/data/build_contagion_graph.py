#!/usr/bin/env python3
"""Build data/graph_edges.csv: a contagion graph computed from real market data only.

Method (every edge is reproducible from data/raw/real/market/close_sp500.parquet):
- daily log returns over the last WINDOW trading days of the file;
- each stock's residual after removing its SPY beta (OLS);
- for every focus name (wholesale-book issuers and equity-sleeve names), candidate peers are
  S&P 500 names in the same GICS sector; edge weight = residual correlation rho;
- pairs with rho >= MIN_RHO are added strongest first while both endpoints have fewer than
  MAX_DEGREE edges; transmission_factor = min(0.8, 0.9 * rho); edges are symmetric.

Names without price history in the file (e.g. the 2023 failures SIVB, FRC, SBNY) get no
edges: a shock to them reports NO_EXPOSURE unless the book holds them. No edge is typed by hand.

Usage: uv run --group data python scripts/data/build_contagion_graph.py
"""

import csv
import importlib.util
import json
from pathlib import Path
from typing import Dict, List, Set, Tuple

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = REPO_ROOT / "data"
PRICES = DATA_DIR / "raw" / "real" / "market" / "close_sp500.parquet"
OUTPUT_CSV = DATA_DIR / "graph_edges.csv"
WINDOW = 252
MIN_RHO = 0.35
MAX_DEGREE = 5
FIELDS = ["source_ticker", "target_ticker", "relationship_type", "transmission_factor", "sign",
          "is_synthetic", "rationale", "evidence"]  # fmt: skip


def focus_tickers() -> Set[str]:
    focus: Set[str] = set()
    for name in ("wholesale_real.json", "equity_sleeve.json"):
        book = json.loads((DATA_DIR / "portfolio" / name).read_text())
        focus |= {p["entity_id"] for p in book["positions"]
                  if p["asset_class"] in ("loan", "bond", "equity")}  # fmt: skip
    return focus


def residuals(px: pd.DataFrame) -> pd.DataFrame:
    rets = np.log(px).diff().iloc[1:]
    mkt = rets.pop("SPY")
    m = mkt - mkt.mean()
    beta = rets.sub(rets.mean()).mul(m, axis=0).sum() / (m**2).sum()
    return rets - np.outer(mkt, beta)


def main() -> None:
    uni = pd.read_csv(DATA_DIR / "universe" / "entities.csv")
    sectors = dict(uni[["ticker", "sector"]].values)
    # share classes of one company (GOOG/GOOGL, FOX/FOXA, ...) are the same issuer, not peers
    company = {t: n.split(" (")[0] for t, n in uni[["ticker", "canonical_name"]].values}
    px = pd.read_parquet(PRICES).sort_index().tail(WINDOW + 1)
    px = px.loc[:, px.notna().all()]  # full history in the window only
    window = f"{px.index[1].date()} to {px.index[-1].date()}"
    res = residuals(px)

    focus = sorted(t for t in focus_tickers() if t in res.columns)
    missing = sorted(t for t in focus_tickers() if t not in res.columns)
    pairs: List[Tuple[float, str, str]] = []
    seen: Set[Tuple[str, str]] = set()
    for a in focus:
        peers = [b for b in res.columns
                 if b != a and sectors.get(b) == sectors.get(a) and company.get(b) != company.get(a)]
        if not peers:
            continue
        rho = res[peers].corrwith(res[a])
        for b, r in rho.items():
            key = tuple(sorted((a, b)))
            if r >= MIN_RHO and key not in seen:
                seen.add(key)
                pairs.append((round(float(r), 4), *key))

    degree: Dict[str, int] = {}
    rows = []
    for r, a, b in sorted(pairs, key=lambda x: (-x[0], x[1], x[2])):
        if degree.get(a, 0) >= MAX_DEGREE or degree.get(b, 0) >= MAX_DEGREE:
            continue
        degree[a], degree[b] = degree.get(a, 0) + 1, degree.get(b, 0) + 1
        for src, dst in ((a, b), (b, a)):
            rows.append({
                "source_ticker": src,
                "target_ticker": dst,
                "relationship_type": "sector_peer",
                "transmission_factor": round(min(0.8, 0.9 * r), 2),
                "sign": 1,
                "is_synthetic": "false",
                "rationale": f"residual return correlation {r:.2f} ({WINDOW}d ex-SPY, {window})",
                "evidence": "data/raw/real/market/close_sp500.parquet (yfinance)",
            })

    with OUTPUT_CSV.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    print(f"Wrote {len(rows)} directed edges ({len(rows) // 2} pairs) for {len(focus)} focus names; "
          f"no price history for: {', '.join(missing) or 'none'}")  # fmt: skip

    spec = importlib.util.spec_from_file_location("bm", Path(__file__).with_name("build_manifest.py"))
    bm = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bm)
    bm.register_dataset(
        "data/graph_edges.csv",
        f"Contagion graph: same-sector residual return correlations ex-SPY ({WINDOW}d, {window})",
        "Derived statistics from Yahoo Finance closes (yfinance); no raw prices redistributed",
        is_synthetic=False,
        source="scripts/data/build_contagion_graph.py",
        derived_from=["data/portfolio/wholesale_real.json", "data/portfolio/equity_sleeve.json",
                      "data/universe/entities.csv"],  # fmt: skip
        columns=FIELDS,
    )


if __name__ == "__main__":
    main()
