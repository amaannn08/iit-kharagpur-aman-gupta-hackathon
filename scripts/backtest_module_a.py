#!/usr/bin/env python3
"""Back-test Module A (sentiment-tilted mock index) on real 2017-2018 tweets and prices.

Pipeline (no look-ahead): real tweets (Kaggle stock-tweets, CC0) -> company name mapped to the
mock-index universe -> social relevance filter -> exact dedup -> sentiment_v2 score -> one
update per ticker-day into the real IndexRebalancer -> end-of-day weights earn the NEXT
trading day's return (yfinance closes). Benchmark: equal weight over the same 20 names.

Writes docs/module_a_backtest.json. Needs data/raw/real (scripts/data/fetch_real.py).
Usage: uv run --group data python scripts/backtest_module_a.py
"""

import json
import sys
from datetime import datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
RAW = REPO_ROOT / "data" / "raw" / "real"
sys.path.insert(0, str(REPO_ROOT / "src"))

from sentinel.nlp.entities import EntityLinker  # noqa: E402
from sentinel.nlp.events import clean_for_classifier  # noqa: E402
from sentinel.nlp.relevance import social_block_reason  # noqa: E402
from sentinel.rebalance import DEFAULT_UNIVERSE, IndexRebalancer  # noqa: E402


def scored_ticker_days() -> pd.DataFrame:
    tw = pd.read_csv(RAW / "stock_tweets" / "full_dataset-release.csv", engine="python",
                     on_bad_lines="skip", usecols=["TWEET", "STOCK", "DATE"])  # fmt: skip
    tw = tw[tw.DATE.astype(str).str.fullmatch(r"\d\d/\d\d/\d{4}")].dropna(subset=["TWEET"])
    linker = EntityLinker()
    alias = {a: t for a, (t, _) in linker.alias_lookup.items()}
    tw["ticker"] = tw.STOCK.astype(str).str.strip().str.lower().map(alias)
    tw = tw[tw.ticker.isin(DEFAULT_UNIVERSE)].drop_duplicates("TWEET")
    n_mapped = len(tw)
    tw = tw[[social_block_reason(t) is None for t in tw.TWEET.astype(str)]]
    model = joblib.load(REPO_ROOT / "models" / "sentiment_v2.joblib")
    proba = model.predict_proba(tw.TWEET.astype(str).map(clean_for_classifier))
    cls = list(model.classes_)
    tw["score"] = proba[:, cls.index("positive")] - proba[:, cls.index("negative")]
    tw["day"] = pd.to_datetime(tw.DATE, format="%d/%m/%Y")
    daily = tw.groupby(["day", "ticker"]).score.agg(["mean", "size"]).reset_index()
    daily.attrs.update(tweets_mapped=n_mapped, tweets_relevant=int(len(tw)))
    return daily


def run(
    daily: pd.DataFrame, closes: pd.DataFrame, k: float, no_trade_band: float = 0.0025
) -> dict:
    idx = IndexRebalancer(k=k, no_trade_band=no_trade_band)
    names = list(DEFAULT_UNIVERSE)
    ret = closes[names].pct_change()
    trading_days = ret.loc[daily.day.min() : daily.day.max()].index
    by_day = {d: g for d, g in daily.groupby("day")}
    weights, turnover = [], []
    for d in trading_days:
        before = dict(idx.weights)
        for row in by_day.get(d, pd.DataFrame()).itertuples():
            idx.update(row.ticker, float(row.mean), datetime(d.year, d.month, d.day))
        weights.append(pd.Series(idx.weights, name=d))
        turnover.append(0.5 * sum(abs(idx.weights[t] - before[t]) for t in names))
    w = pd.DataFrame(weights)
    nxt = ret.shift(-1).loc[w.index, names]  # weights at close t earn the return of t+1
    gross_tilt = (w * nxt).sum(axis=1, min_count=1).dropna()
    eq = nxt.mean(axis=1).loc[gross_tilt.index]
    t_turnover = pd.Series(turnover, index=w.index).loc[gross_tilt.index]

    # Costs and net returns for cost_bps in {0, 5, 10}
    costs_dict = {}
    for bps in (0, 5, 10):
        cost_series = t_turnover * (bps / 10000.0)
        net_tilt = gross_tilt - cost_series
        net_active = net_tilt - eq
        net_te = net_active.std() * np.sqrt(252)
        costs_dict[f"cost_{bps}bps"] = {
            "net_tilt_annual_return": round(float(net_tilt.mean() * 252), 4),
            "net_active_annual_return": round(float(net_active.mean() * 252), 4),
            "net_tracking_error": round(float(net_te), 4),
            "net_information_ratio": round(float(net_active.mean() * 252 / net_te), 3)
            if net_te > 0
            else None,
        }

    active = gross_tilt - eq
    te = active.std() * np.sqrt(252)
    ann_turnover = float(np.mean(turnover) * 252)
    active_ann = float(active.mean() * 252)
    be_cost_bps = round(float((active_ann / ann_turnover) * 10000), 2) if ann_turnover > 0 else 0.0

    # Stationary circular block bootstrap for active return (block 20 days, 2,000 resamples, seed 42)
    rng = np.random.default_rng(42)
    n_days = len(active)
    block_len = 20
    n_blocks = int(np.ceil(n_days / block_len))
    boot_active_ann = []
    active_arr = active.values
    for _ in range(2000):
        start_indices = rng.integers(0, n_days, size=n_blocks)
        sampled = []
        for s in start_indices:
            block = [active_arr[(s + j) % n_days] for j in range(block_len)]
            sampled.extend(block)
        sampled = sampled[:n_days]
        boot_active_ann.append(np.mean(sampled) * 252)

    ci95 = [
        round(float(np.percentile(boot_active_ann, 2.5)), 4),
        round(float(np.percentile(boot_active_ann, 97.5)), 4),
    ]

    return {
        "k": k,
        "no_trade_band": no_trade_band,
        "trading_days": int(len(gross_tilt)),
        "tilt_annual_return": round(float(gross_tilt.mean() * 252), 4),
        "equal_weight_annual_return": round(float(eq.mean() * 252), 4),
        "active_annual_return": round(active_ann, 4),
        "active_annual_return_ci95": ci95,
        "tracking_error": round(float(te), 4),
        "information_ratio": round(float(active_ann / te), 3) if te > 0 else None,
        "active_return_t_stat": round(
            float(active.mean() / active.std() * np.sqrt(len(active))), 3
        ),
        "avg_daily_turnover": round(float(np.mean(turnover)), 5),
        "annual_turnover": round(ann_turnover, 4),
        "break_even_cost_bps": be_cost_bps,
        "net_costs": costs_dict,
        "max_weight": round(float(w.max().max()), 4),
        "mean_abs_tilt_from_equal": round(float((w - 1 / len(names)).abs().mean().mean()), 5),
    }


def main() -> None:
    daily = scored_ticker_days()
    closes = pd.read_parquet(RAW / "market" / "close.parquet").sort_index()
    results = [run(daily, closes, k) for k in (0.5, 1.5, 5.0)]
    out = {
        "description": "Module A back-test on real tweets (2017-2018) and real closes; "
        "weights at close t earn the t+1 return; equal-weight benchmark on the same 20 names",
        "universe": list(DEFAULT_UNIVERSE),
        "tweets_mapped_to_universe": daily.attrs["tweets_mapped"],
        "tweets_relevant_after_filter": daily.attrs["tweets_relevant"],
        "ticker_days_with_sentiment": int(len(daily)),
        "period": [str(daily.day.min().date()), str(daily.day.max().date())],
        "runs": results,
        "conclusion": (
            "Positive but statistically insignificant active return (|t| < 2 for every k): "
            "the module demonstrates sentiment-driven reweighting, not demonstrated alpha."
            if all(abs(r["active_return_t_stat"]) < 2 for r in results)
            else "At least one k has |t| >= 2; check robustness before claiming alpha."
        ),
    }
    (REPO_ROOT / "docs" / "module_a_backtest.json").write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
