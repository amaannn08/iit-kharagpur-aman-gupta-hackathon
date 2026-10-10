#!/usr/bin/env python3
"""Train and validate the market-calibrated impact model (models/impact_v2.*).

Label: for every real 2023 Polygon article and every S&P 500 company it names, the absolute
standardized abnormal return on the reaction day:
    z = (r_t - beta_120d * r_SPY,t) / sigma_30d     (beta and sigma use data before t only)
Reaction day = publication day if published before 16:00 New York on a trading day, else the
next trading day.

Leakage controls:
  - reaction headlines written *because* the price moved ("Why X stock is soaring today") are
    dropped, otherwise the label leaks into the text features;
  - no same-day attention counts; features come only from the article text;
  - cross-validation folds are grouped by calendar month.

Labels are derived once from the raw yfinance cache (data/raw/real/market) and committed as
data/market/reaction_labels.csv (derived statistics only), so retraining needs no raw data.

Usage:
  uv run python scripts/models/train_impact.py                 # uses committed labels
  uv run python scripts/models/train_impact.py --rebuild-labels # needs data/raw/real/market
"""

import argparse
import hashlib
import importlib.util
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.model_selection import GroupKFold

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DATA = REPO_ROOT / "data"
MODELS = REPO_ROOT / "models"
RAW_MARKET = DATA / "raw" / "real" / "market"
LABELS = DATA / "market" / "reaction_labels.csv"
sys.path.insert(0, str(REPO_ROOT / "src"))

from sentinel.contracts.signals import EntityReference  # noqa: E402
from sentinel.nlp.entities import EntityLinker  # noqa: E402
from sentinel.nlp.events import EventClassifier  # noqa: E402
from sentinel.nlp.impact_model import impact_features  # noqa: E402
from sentinel.nlp.sentiment import FinBERTSentimentAnalyzer  # noqa: E402
from sentinel.nlp.severity import SeverityRubricEngine  # noqa: E402

REACTION_HEADLINE = re.compile(
    r"\b(why|here's why)\b.*\b(stock|shares)\b|"
    r"\b(soar|soaring|plung|tumbl|jump|surg|sink|slid|rall|crash|skyrocket|down|up)\w*\b.*\btoday\b|"
    r"\bstock (is|are) (up|down)\b",
    re.I,
)
SEED = 42


def load_closes() -> pd.DataFrame:
    wide = pd.read_parquet(RAW_MARKET / "close_sp500.parquet")
    sp100 = pd.read_parquet(RAW_MARKET / "close.parquet")
    for col in sp100.columns:  # fill tickers the wide pull missed (e.g. AMD)
        if col not in wide.columns or wide[col].notna().sum() < 100:
            wide[col] = sp100[col].reindex(wide.index)
    return wide.sort_index()


def abnormal_z(closes: pd.DataFrame) -> pd.DataFrame:
    ret = np.log(closes).diff()
    vol = ret.rolling(30).std().shift(1)
    beta = ret.rolling(120).cov(ret["SPY"]).div(ret["SPY"].rolling(120).var(), axis=0).shift(1)
    return (ret - beta.mul(ret["SPY"], axis=0)) / vol


def rebuild_labels() -> pd.DataFrame:
    news = pd.read_csv(DATA / "real" / "polygon_news" / "polygon_news.csv")
    z = abnormal_z(load_closes())
    days = z.index
    linker = EntityLinker()
    rows = []
    for r in news.itertuples():
        if REACTION_HEADLINE.search(r.headline or ""):
            continue
        text = f"{r.headline}. {r.body if isinstance(r.body, str) else ''}"
        tickers = [t for t in linker.find_companies(text) if not linker.entities[t].is_synthetic]
        if not tickers:
            continue
        ts = pd.Timestamp(r.published_at).tz_convert("America/New_York")
        day = ts.normalize().tz_localize(None)
        pos = days.searchsorted(day)
        if pos < len(days) and days[pos] == day and ts.hour >= 16:
            pos += 1
        if pos >= len(days):
            continue
        for t in tickers:
            if t not in z.columns or np.isnan(z[t].iloc[pos]):
                continue
            rows.append(
                {
                    "record_id": r.record_id,
                    "ticker": t,
                    "reaction_date": days[pos].date().isoformat(),
                    "abnormal_z": round(float(z[t].iloc[pos]), 5),
                }
            )
    df = pd.DataFrame(rows)
    LABELS.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(LABELS, index=False)
    spec = importlib.util.spec_from_file_location(
        "build_manifest", REPO_ROOT / "scripts" / "data" / "build_manifest.py"
    )
    bm = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bm)
    bm.register_dataset(
        "data/market/reaction_labels.csv",
        "Standardized next-day abnormal return per (Polygon article, S&P 500 company): impact labels",
        "Derived statistics from Yahoo Finance closes (yfinance); no raw prices redistributed",
        is_synthetic=False,
        source="https://finance.yahoo.com via yfinance; data/real/polygon_news",
        derived_from=["data/real/polygon_news/polygon_news.csv"],
        columns=list(df.columns),
    )
    return df


def build_features(labels: pd.DataFrame) -> pd.DataFrame:
    news = pd.read_csv(DATA / "real" / "polygon_news" / "polygon_news.csv").set_index("record_id")
    events, sentiment, linker = EventClassifier(), FinBERTSentimentAnalyzer(), EntityLinker()
    rubric = SeverityRubricEngine()
    cache = {}
    rows = []
    for r in labels.itertuples():
        if r.record_id not in cache:
            art = news.loc[r.record_id]
            text = f"{art.headline}. {art.body if isinstance(art.body, str) else ''}"
            ev = events.predict(text)
            s = sentiment.analyze(text)
            n = len([t for t in linker.find_companies(text) if not linker.entities[t].is_synthetic])
            ref = EntityReference(name="x", ticker="X", scope="company")
            cache[r.record_id] = (
                impact_features(ev, s.score, n, text, is_social=False),
                rubric.evaluate(ev.label, text, ref)[0].score,
            )
        feats, rubric_score = cache[r.record_id]
        rows.append({**feats, "rubric_score": rubric_score, "abs_z": abs(r.abnormal_z),
                     "month": r.reaction_date[:7], "record_id": r.record_id})  # fmt: skip
    return pd.DataFrame(rows)


def bootstrap_ci(x, y, n=1000):
    rng = np.random.default_rng(SEED)
    stats = []
    for _ in range(n):
        idx = rng.integers(0, len(x), len(x))
        stats.append(spearmanr(x[idx], y[idx]).statistic)
    return [round(float(np.percentile(stats, 2.5)), 4), round(float(np.percentile(stats, 97.5)), 4)]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rebuild-labels", action="store_true")
    args = ap.parse_args()
    labels = rebuild_labels() if args.rebuild_labels or not LABELS.exists() else pd.read_csv(LABELS)
    df = build_features(labels)
    feature_cols = [
        c for c in df.columns if c not in ("rubric_score", "abs_z", "month", "record_id")
    ]

    y = df.abs_z.to_numpy()
    oof = np.zeros(len(df))
    for trn, tst in GroupKFold(n_splits=5).split(df, groups=df.month):
        m = HistGradientBoostingRegressor(
            max_depth=3, learning_rate=0.05, max_iter=300, min_samples_leaf=30, random_state=SEED
        )
        m.fit(df.iloc[trn][feature_cols], y[trn])
        oof[tst] = m.predict(df.iloc[tst][feature_cols])

    edges = np.quantile(oof, np.linspace(0, 1, 11)[1:-1])
    deciles = np.searchsorted(edges, oof, side="right") + 1
    by_decile = pd.DataFrame({"decile": deciles, "abs_z": y}).groupby("decile").abs_z
    large = lambda d: float((y[deciles == d] > 2).mean())  # noqa: E731
    metrics = {
        "events": int(len(df)),
        "articles": int(df.record_id.nunique()),
        "tickers": int(labels.ticker.nunique()),
        "rubric_v1_spearman": round(float(spearmanr(df.rubric_score, y).statistic), 4),
        "rubric_v1_spearman_ci95": bootstrap_ci(df.rubric_score.to_numpy(), y),
        "learned_oof_spearman": round(float(spearmanr(oof, y).statistic), 4),
        "learned_oof_spearman_ci95": bootstrap_ci(oof, y),
        "mean_abs_z_by_decile": {int(k): round(float(v), 3) for k, v in by_decile.mean().items()},
        "large_move_rate_decile_10": round(large(10), 4),
        "large_move_rate_decile_1": round(large(1), 4),
        "large_move_definition": "|abnormal z| > 2",
        "cv": "5-fold GroupKFold by reaction month (out-of-fold predictions)",
    }
    final = HistGradientBoostingRegressor(
        max_depth=3, learning_rate=0.05, max_iter=300, min_samples_leaf=30, random_state=SEED
    ).fit(df[feature_cols], y)
    MODELS.mkdir(exist_ok=True)
    out = MODELS / "impact_v2.joblib"
    joblib.dump(
        {"model": final, "features": feature_cols, "decile_edges": edges.tolist()}, out, compress=3
    )
    card = {
        "model": "impact_v2",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "target": "|standardized abnormal return| on the reaction day (beta 120d, sigma 30d, vs SPY)",
        "mapping": "impact 1-10 = decile of the out-of-fold prediction (decile_edges)",
        "algorithm": "HistGradientBoostingRegressor(max_depth=3, lr=0.05, 300 iters, min leaf 30)",
        "features": feature_cols,
        "labels_sha256": hashlib.sha256(LABELS.read_bytes()).hexdigest(),
        "metrics": metrics,
        "model_sha256": hashlib.sha256(out.read_bytes()).hexdigest(),
    }
    (MODELS / "impact_v2.card.json").write_text(json.dumps(card, indent=1) + "\n")
    print(json.dumps(metrics, indent=1))


if __name__ == "__main__":
    main()
