#!/usr/bin/env python3
"""Calibrate Module B shock sizes from real historical stress windows.

For each named window, from real yfinance closes (data/raw/real/market/close.parquet):
  equity_shock_pct          SPY total move over the window
  benchmark_yield_shift_bps change in the 10-year Treasury yield (^TNX)
  bond_spread_shift_bps     implied high-yield spread change: -(r_credit - (D_c/D_t) r_tsy) / D_c
                            with HYG effective duration 3.7 and IEF 7.3
  ig_spread_shift_bps       implied investment-grade spread change using LQD (D_IG = 8.4)

Outputs: data/market/stress_windows.json (derived statistics) and one runnable scenario per window
in data/scenarios/historical_*.json. The shock catalog in sentinel.stress.shocks is anchored on
these windows; tests check it stays consistent with stress_windows.json.

Usage: uv run --group data python scripts/data/calibrate_shocks.py
"""

import importlib.util
import json
import sys
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))
from sentinel.stress.calibration import (  # noqa: E402
    HY_DURATION,
    IG_DURATION,
    TSY_DURATION,
    implied_spread_change_bps,
)

CLOSE = REPO_ROOT / "data" / "raw" / "real" / "market" / "close.parquet"
OUT = REPO_ROOT / "data" / "market" / "stress_windows.json"
SCENARIOS = REPO_ROOT / "data" / "scenarios"

WINDOWS = {
    "covid_2020": ("COVID-19 liquidity shock", "MACRO", "2020-02-19", "2020-03-23"),
    "russia_2022": ("Russia-Ukraine invasion", "GEOPOLITICAL", "2022-02-23", "2022-03-08"),
    "fed_jun_2022": ("Fed 75 bp surprise hike", "MACRO", "2022-06-09", "2022-06-16"),
    "svb_2023": ("Silicon Valley Bank failure", "CREDIT", "2023-03-08", "2023-03-17"),
    "fed_pivot_2023": ("Fed pivot rally (easing)", "MACRO", "2023-11-01", "2023-12-14"),
}


def load_fred(series_id: str) -> pd.Series | None:
    p = REPO_ROOT / "data" / "raw" / "real" / "fred" / f"{series_id}.csv"
    if not p.exists():
        return None
    df = pd.read_csv(p)
    df.columns = ["date", "val"]
    df["val"] = pd.to_numeric(df["val"], errors="coerce")
    df = df.dropna(subset=["val"]).copy()
    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index("date")
    return df["val"]


def fred_validation(windows):
    out = {}
    for key, wd in windows.items():
        for series, field in (
            ("BAMLH0A0HYM2", "bond_spread_shift_bps"),
            ("BAMLC0A0CM", "ig_spread_shift_bps"),
        ):
            s = load_fred(series)
            if s is None or pd.Timestamp(wd["start"]) < s.index.min():
                continue
            actual = (s.asof(wd["end"]) - s.asof(wd["start"])) * 100
            out.setdefault(key, {})[series] = {
                "implied_bps": wd[field],
                "actual_oas_bps": round(float(actual), 1),
                "error_bps": round(float(wd[field] - actual), 1),
            }
    return out


def main() -> None:
    px = pd.read_parquet(CLOSE).sort_index()
    windows = {}
    for key, (name, event_class, start, end) in WINDOWS.items():
        w = px.loc[start:end]
        first, last = w.iloc[0], w.iloc[-1]
        r = lambda c: float(last[c] / first[c] - 1)  # noqa: E731
        spread_bps = implied_spread_change_bps(r("HYG"), r("IEF"), HY_DURATION, TSY_DURATION)
        ig_spread_bps = implied_spread_change_bps(r("LQD"), r("IEF"), IG_DURATION, TSY_DURATION)
        windows[key] = {
            "name": name,
            "event_class": event_class,
            "start": start,
            "end": end,
            "trading_days": int(len(w)),
            "equity_shock_pct": round(float(last["SPY"] / first["SPY"] - 1), 4),
            "benchmark_yield_shift_bps": round(float((last["^TNX"] - first["^TNX"]) * 100), 1),
            "hy_minus_treasury_return": round(float(r("HYG") - r("IEF")), 4),
            "bond_spread_shift_bps": round(float(spread_bps), 1),
            "ig_spread_shift_bps": round(float(ig_spread_bps), 1),
            "ig_to_hy_ratio": (
                round(float(ig_spread_bps / spread_bps), 3) if abs(spread_bps) > 30 else None
            ),
            "spread_sensitivity_bps": {
                "low": round(
                    min(
                        implied_spread_change_bps(r("HYG"), r("IEF"), d, t)
                        for d in (3.2, 4.2)
                        for t in (6.8, 7.8)
                    ),
                    1,
                ),
                "high": round(
                    max(
                        implied_spread_change_bps(r("HYG"), r("IEF"), d, t)
                        for d in (3.2, 4.2)
                        for t in (6.8, 7.8)
                    ),
                    1,
                ),
            },
            "vix_change": round(float(last["^VIX"] - first["^VIX"]), 1),
            "vix_peak": round(float(w["^VIX"].max()), 1),
        }
    meta = {
        "source": "yfinance closes (SPY, ^TNX, HYG, LQD, IEF, ^VIX)",
        "durations": {"HYG": HY_DURATION, "LQD": IG_DURATION, "IEF": TSY_DURATION},
        "spread_formula": "-(r_credit - (D_c/D_t) r_IEF) / D_c",
        "windows": windows,
        "validation_vs_fred_oas": fred_validation(windows),
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
                "pd_from_spread": True,
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
    print(
        pd.DataFrame(windows).T[
            [
                "equity_shock_pct",
                "benchmark_yield_shift_bps",
                "bond_spread_shift_bps",
                "ig_spread_shift_bps",
                "ig_to_hy_ratio",
                "vix_peak",
            ]
        ]
    )


if __name__ == "__main__":
    main()
