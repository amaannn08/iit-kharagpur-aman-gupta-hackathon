#!/usr/bin/env python3
"""Build the Module B equity sleeve: 15 S&P 100 names with betas estimated from real prices.

The PS's example stress ("a 10% drop in all equity prices") needs equity exposure. Position
sizes are a stated assumption ($4M each, $60M total); betas and volatilities are estimated
from real yfinance closes (data/raw/real/market) over the 252 trading days to 2024-02-29.

Output: data/portfolio/equity_sleeve.json
Usage:  uv run --group data python scripts/data/build_equity_sleeve.py
"""

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
RAW_MARKET = REPO_ROOT / "data" / "raw" / "real" / "market"
UNIVERSE = REPO_ROOT / "data" / "universe" / "entities.csv"
OUT = REPO_ROOT / "data" / "portfolio" / "equity_sleeve.json"
POSITION_USD = 4_000_000.0
WINDOW = 252
# Two or three names per GICS sector across the S&P 100
TICKERS = ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "JPM", "BAC", "XOM", "CVX",
           "JNJ", "PFE", "WMT", "KO", "CAT", "BA"]  # fmt: skip


def main() -> None:
    if not (RAW_MARKET / "close.parquet").exists():
        sys.exit("data/raw/real/market missing: run scripts/data/fetch_real.py --only market")
    px = pd.read_parquet(RAW_MARKET / "close.parquet").sort_index()
    ret = np.log(px[TICKERS + ["SPY"]]).diff().iloc[-WINDOW:]
    universe = pd.read_csv(UNIVERSE).set_index("ticker")
    positions = []
    for i, t in enumerate(TICKERS, start=1):
        r = ret[[t, "SPY"]].dropna()
        beta = float(r[t].cov(r["SPY"]) / r["SPY"].var())
        vol = float(r[t].std() * np.sqrt(252))
        positions.append(
            {
                "position_id": f"EQ-{i:03d}",
                "asset_class": "equity",
                "entity_id": t,
                "counterparty_name": universe.loc[t, "canonical_name"],
                "sector": universe.loc[t, "sector"],
                "currency": "USD",
                "market_value": POSITION_USD,
                "beta": round(beta, 4),
                "volatility_annual": round(vol, 4),
                "sleeve": "equity",
            }
        )
    sleeve = {
        "portfolio_name": "Equity sleeve (S&P 100 names, real betas)",
        "base_currency": "USD",
        "valuation_date": "2026-03-01",
        "is_synthetic": True,
        "assumptions": {
            "position_size_usd": POSITION_USD,
            "beta": f"OLS vs SPY on daily log returns, {WINDOW} trading days to {ret.index[-1].date()}",
            "sizes_are_synthetic": True,
            "betas_are_estimated_from_real_prices": True,
        },
        "positions": positions,
    }
    OUT.write_text(json.dumps(sleeve, indent=1) + "\n")
    spec = importlib.util.spec_from_file_location(
        "bm", Path(__file__).with_name("build_manifest.py")
    )
    bm = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bm)
    bm.register_dataset(
        "data/portfolio/equity_sleeve.json",
        "Module B equity sleeve: 15 S&P 100 names, synthetic $4M sizes, betas estimated from real prices",
        "MIT License (project-authored sizes); betas derived from Yahoo Finance closes via yfinance",
        is_synthetic=True,
        source="https://finance.yahoo.com via yfinance",
    )
    for p in positions:
        print(
            f"{p['entity_id']:6} beta={p['beta']:.2f} vol={p['volatility_annual']:.2f} {p['sector']}"
        )


if __name__ == "__main__":
    main()
