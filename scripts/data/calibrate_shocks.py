#!/usr/bin/env python3
"""Calibrate Module B shock sizes from real historical stress windows.

For each named window, from real yfinance closes (data/raw/real/market/close.parquet):
  equity_shock_pct          SPY total move over the window
  benchmark_yield_shift_bps change in the 10-year Treasury yield (^TNX)
  bond_spread_shift_bps     implied high-yield spread change: -(HYG return - IEF return) / D_HY
                            with HYG effective duration D_HY = 3.7 (approximation)
  loan_pd_increment         credit triangle: spread ~ PD x LGD  =>  dPD = d_spread / LGD (0.6)

Outputs: data/market/stress_windows.json (derived statistics) and one runnable scenario per window
in data/scenarios/historical_*.json. The shock catalog in sentinel.stress.shocks is anchored on
these windows; tests check it stays consistent with stress_windows.json.

Usage: uv run --group data python scripts/data/calibrate_shocks.py
"""

import importlib.util
import json
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
CLOSE = REPO_ROOT / "data" / "raw" / "real" / "market" / "close.parquet"
OUT = REPO_ROOT / "data" / "market" / "stress_windows.json"
SCENARIOS = REPO_ROOT / "data" / "scenarios"
HY_DURATION = 3.7
LGD_FOR_TRIANGLE = 0.6

WINDOWS = {
    "covid_2020": ("COVID-19 liquidity shock", "MACRO", "2020-02-19", "2020-03-23"),
    "russia_2022": ("Russia-Ukraine invasion", "GEOPOLITICAL", "2022-02-23", "2022-03-08"),
    "fed_jun_2022": ("Fed 75 bp surprise hike", "MACRO", "2022-06-09", "2022-06-16"),
    "svb_2023": ("Silicon Valley Bank failure", "CREDIT", "2023-03-08", "2023-03-17"),
    "fed_pivot_2023": ("Fed pivot rally (easing)", "MACRO", "2023-11-01", "2023-12-14"),
}


def main() -> None:
    px = pd.read_parquet(CLOSE).sort_index()
    windows = {}
    for key, (name, event_class, start, end) in WINDOWS.items():
        w = px.loc[start:end]
        first, last = w.iloc[0], w.iloc[-1]
        hy_rel = (last["HYG"] / first["HYG"] - 1) - (last["IEF"] / first["IEF"] - 1)
        spread_bps = -hy_rel / HY_DURATION * 1e4
        windows[key] = {
            "name": name,
            "event_class": event_class,
            "start": start,
            "end": end,
            "trading_days": int(len(w)),
            "equity_shock_pct": round(float(last["SPY"] / first["SPY"] - 1), 4),
            "benchmark_yield_shift_bps": round(float((last["^TNX"] - first["^TNX"]) * 100), 1),
            "hy_minus_treasury_return": round(float(hy_rel), 4),
            "bond_spread_shift_bps": round(float(spread_bps), 1),
            "loan_pd_increment": round(max(0.0, float(spread_bps) / 1e4 / LGD_FOR_TRIANGLE), 4),
            "vix_change": round(float(last["^VIX"] - first["^VIX"]), 1),
            "vix_peak": round(float(w["^VIX"].max()), 1),
        }
    meta = {
        "source": "yfinance closes (SPY, ^TNX, HYG, IEF, ^VIX)",
        "hy_duration_assumption": HY_DURATION,
        "credit_triangle_lgd": LGD_FOR_TRIANGLE,
        "windows": windows,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(meta, indent=1) + "\n")

    for key, wd in windows.items():
        scenario = {
            "scenario_id": f"HIST-{key.upper()}",
            "name": f"Historical: {wd['name']} ({wd['start']} to {wd['end']})",
            "description": (
                f"Replays the measured market move of {wd['name']}: S&P 500 "
                f"{wd['equity_shock_pct']:+.1%}, 10y yield {wd['benchmark_yield_shift_bps']:+.0f} bp, "
                f"implied HY spread {wd['bond_spread_shift_bps']:+.0f} bp."
            ),
            "event_class": wd["event_class"],
            "trigger_impact_score": 8,
            "target_entity": None,
            "target_scope": "systemic",
            "direct_shocks": {
                "bond_spread_shift_bps": wd["bond_spread_shift_bps"],
                "loan_pd_increment": wd["loan_pd_increment"],
                "lgd_increment": 0.0,
            },
            "macro_shocks": {"benchmark_yield_shift_bps": wd["benchmark_yield_shift_bps"]},
            "equity_shocks": {"equity_shock_pct": wd["equity_shock_pct"]},
            "contagion": {"enabled": False, "hop_decay": 0.0, "max_hops": 0},
            "provenance": "data/market/stress_windows.json (real yfinance closes)",
            "is_synthetic": False,
        }
        (SCENARIOS / f"historical_{key}.json").write_text(json.dumps(scenario, indent=2) + "\n")

    spec = importlib.util.spec_from_file_location(
        "bm", Path(__file__).with_name("build_manifest.py")
    )
    bm = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bm)
    bm.register_dataset(
        "data/market/stress_windows.json",
        "Measured market moves over five historical stress windows (shock calibration anchors)",
        "Derived statistics from Yahoo Finance closes (yfinance); no raw prices redistributed",
        is_synthetic=False,
        source="https://finance.yahoo.com via yfinance",
    )
    for key in WINDOWS:
        bm.register_dataset(
            f"data/scenarios/historical_{key}.json",
            f"Runnable historical stress scenario: {WINDOWS[key][0]}",
            "Derived statistics from Yahoo Finance closes (yfinance)",
            is_synthetic=False,
            source="data/market/stress_windows.json",
        )
    print(pd.DataFrame(windows).T[["equity_shock_pct", "benchmark_yield_shift_bps",
                                    "bond_spread_shift_bps", "loan_pd_increment", "vix_peak"]])  # fmt: skip


if __name__ == "__main__":
    main()
