#!/usr/bin/env python3
"""S&P Sentinel evaluation suites: every reported number comes from here.

Suites (default: all):
  public_real          held-out REAL labeled data (HF twitter-financial-news topic/sentiment
                       valid splits), full runtime path, plus baselines on identical rows
  entity_polygon       entity linking on 5,548 real Polygon articles vs their tickers[]
  market_impact        impact validation vs real abnormal returns (models/impact_v2.card.json)
  sec_8k               held-out real 8-K filings (models/event_v2.card.json)
  stress               Module B: historical scenarios and the PS example shock
  module_a             Module A back-test summary (docs/module_a_backtest.json)
  perf                 throughput, per-record latency, peak memory
  synthetic_regression the 105-row author-written set (synthetic: regression check only)

Writes docs/metrics.json and docs/evaluation_report.md; --write-readme injects the headline
table into README.md between <!-- METRICS:START --> and <!-- METRICS:END -->.
Usage: uv run python scripts/run_evaluation.py [--suite public_real,perf] [--write-readme]
"""

import argparse
import csv
import hashlib
import importlib.util
import json
import re
import resource
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd
from sklearn.metrics import confusion_matrix, f1_score

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA = REPO_ROOT / "data"
DOCS = REPO_ROOT / "docs"
MODELS = REPO_ROOT / "models"
sys.path.insert(0, str(REPO_ROOT / "src"))

from sentinel.contracts.records import InputRecord, SourceType  # noqa: E402
from sentinel.nlp.engine import NLPEngine  # noqa: E402
from sentinel.nlp.entities import EntityLinker  # noqa: E402
from sentinel.nlp.events import (  # noqa: E402
    EventClassifier,
    clean_for_classifier,
    ps_aligned_label,
)
from sentinel.nlp.sentiment import FinBERTSentimentAnalyzer  # noqa: E402

PS_CLASSES = ["CREDIT", "EARNINGS", "GEOPOLITICAL", "MACRO", "M_AND_A", "PRODUCT", "REGULATORY"]
PS_CLASSES_WITH_LABELS = PS_CLASSES  # plus OTHER; CYBER/SUPPLY_CHAIN have no labels in this split
TARGETS = {
    "event_macro_f1": 0.70,
    "sentiment_macro_f1": 0.75,
    "entity_precision": 0.90,
    "entity_recall_mentioned": 0.90,
    "severity_mae": 1.5,
    "p95_latency_s": 2.0,
    "peak_rss_gb": 4.0,
    "false_trigger_rate_routine": 0.05,
    "trigger_precision_lift": 1.5,
}

BASELINE_KEYWORDS = [
    ("CREDIT", ("downgrade", "covenant", "default", "restructuring", "coupon payment", "bankruptcy")),
    ("MACRO", ("federal reserve", "treasury yield", "central bank", "inflation", "gdp", "interest rate")),
    ("GEOPOLITICAL", ("sanction", "tariff", "naval", "nationalize", "treaty", "war ")),
    ("SUPPLY_CHAIN", ("strike", "shortage", "force majeure", "cargo", "supply chain")),
    ("EARNINGS", ("net income", "revenue", "quarterly earnings", "operating profit", "ebitda", "eps")),
    ("M_AND_A", ("acquire", "acquisition", "merger", "takeover", "tender offer", "buyout")),
    ("REGULATORY", ("antitrust", "regulator", "consent order", "penalty", "lawsuit", "sec ")),
    ("CYBER", ("zero-day", "ransomware", "ddos", "breach", "cyber", "hack")),
    ("PRODUCT", ("fda", "recall", "clinical trial", "launch", "unveil")),
]  # fmt: skip


def baseline_event(text: str) -> str:
    t = text.lower()
    return next((cls for cls, kws in BASELINE_KEYWORDS if any(k in t for k in kws)), "OTHER")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def macro_f1(y_true, y_pred, labels) -> float:
    return round(
        float(f1_score(y_true, y_pred, labels=labels, average="macro", zero_division=0)), 4
    )


def bootstrap_ratio_ci(hits: int, total: int, n: int = 1000, seed: int = 42) -> List[float]:
    if total == 0:
        return [0.0, 0.0]
    rng = np.random.default_rng(seed)
    arr = np.array([1] * hits + [0] * (total - hits))
    means = [float(np.mean(rng.choice(arr, size=total, replace=True))) for _ in range(n)]
    return [round(float(np.percentile(means, 2.5)), 4), round(float(np.percentile(means, 97.5)), 4)]


def suite_public_real() -> Dict[str, Any]:
    topic = DATA / "train" / "hf_fin_topic" / "topic_valid.csv"
    sent = DATA / "train" / "hf_fin_sentiment" / "sent_valid.csv"
    tv = pd.read_csv(topic)
    gold = [ps_aligned_label(lab, clean_for_classifier(t)) for lab, t in zip(tv.label, tv.text)]
    clf = EventClassifier()
    pred = [clf.predict(t).label for t in tv.text]  # runtime path: threshold + gates
    model_only = list(clf.pipeline.predict([clean_for_classifier(t) for t in tv.text]))
    seed = EventClassifier(model_path=MODELS / "__none__.joblib")  # old seed baseline
    seed_pred = [seed.predict(t).label for t in tv.text]
    kw_pred = [baseline_event(t) for t in tv.text]
    labels = PS_CLASSES_WITH_LABELS
    fired = np.array([p != "OTHER" for p in pred])
    correct = np.array([p == g for p, g in zip(pred, gold)])
    event = {
        "dataset": "zeroshot/twitter-financial-news-topic valid (real, held out)",
        "n": int(len(tv)),
        "sha256": sha256(topic),
        "classes_scored": labels,
        "macro_f1_model": macro_f1(gold, model_only, labels),
        "macro_f1_runtime_with_gates_and_abstention": macro_f1(gold, pred, labels),
        "precision_when_fired": round(float(correct[fired].mean()), 4),
        "fired_rate": round(float(fired.mean()), 4),
        "baseline_keyword_macro_f1": macro_f1(gold, kw_pred, labels),
        "baseline_seed_classifier_macro_f1": macro_f1(gold, seed_pred, labels),
        "per_class_f1_model": {
            c: round(
                float(f1_score(gold, model_only, labels=[c], average="macro", zero_division=0)), 4
            )
            for c in labels
        },
        "confusion_matrix_model": {
            "labels": labels + ["OTHER"],
            "matrix": confusion_matrix(gold, model_only, labels=labels + ["OTHER"]).tolist(),
        },
    }
    sv = pd.read_csv(sent)
    sgold = sv.label.map({0: "negative", 1: "positive", 2: "neutral"})
    analyzer = FinBERTSentimentAnalyzer()
    lexicon = FinBERTSentimentAnalyzer(
        model_dir=MODELS / "__none__", tfidf_path=MODELS / "__none__"
    )
    spred = [analyzer.analyze(t).label for t in sv.text]
    slex = [lexicon.analyze(t).label for t in sv.text]
    sentiment = {
        "dataset": "zeroshot/twitter-financial-news-sentiment valid (real, held out)",
        "n": int(len(sv)),
        "sha256": sha256(sent),
        "backend": analyzer.backend,
        "macro_f1": macro_f1(sgold, spred, ["negative", "neutral", "positive"]),
        "baseline_lexicon_macro_f1": macro_f1(sgold, slex, ["negative", "neutral", "positive"]),
    }
    card = json.loads((MODELS / "sentiment_v2.card.json").read_text())
    sentiment["polygon_news_vs_llm_silver_macro_f1"] = card["metrics"][
        "polygon_news_vs_llm_silver"
    ]["macro_f1"]
    return {"event": event, "sentiment": sentiment}


def suite_entity_polygon() -> Dict[str, Any]:
    from sentinel.nlp.entities import CANONICAL_SHARE_CLASSES

    news = pd.read_csv(DATA / "real" / "polygon_news" / "polygon_news.csv")
    silver = pd.read_csv(DATA / "real" / "polygon_news" / "silver_labels.csv")
    gold = (
        silver[silver.label_source == "polygon_tickers"]
        .groupby("record_id")
        .ticker.apply(
            lambda s: {
                CANONICAL_SHARE_CLASSES.get(t.replace(".", "-"), t.replace(".", "-")) for t in s
            }
        )
    )
    linker = EntityLinker()
    universe = {
        CANONICAL_SHARE_CLASSES.get(t, t)
        for t, e in linker.entities.items()
        if not e.is_synthetic
    }

    def is_mentioned(ticker: str, text: str) -> bool:
        ke = linker.entities.get(ticker)
        if not ke:
            return False
        if re.search(rf"(\$|\b){re.escape(ticker)}\b", text, re.I):
            return True
        if ke.canonical_name.lower() in text.lower():
            return True
        for a in ke.aliases:
            if len(a) >= 3 and a.lower() in text.lower():
                return True
        return False

    tp = fp = fn = n = 0
    tp_ment = fn_ment = 0
    for r in news.itertuples():
        g = gold.get(r.record_id, set()) & universe
        if not g:
            continue
        n += 1
        text = f"{r.headline}. {r.body if isinstance(r.body, str) else ''}"
        p = {
            CANONICAL_SHARE_CLASSES.get(t, t)
            for t in linker.find_companies(text)
            if CANONICAL_SHARE_CLASSES.get(t, t) in universe
        }
        tp += len(p & g)
        fp += len(p - g)
        fn += len(g - p)
        g_ment = {t for t in g if is_mentioned(t, text)}
        tp_ment += len(p & g_ment)
        fn_ment += len(g_ment - p)

    return {
        "dataset": "Polygon 2023 news (real), gold = article tickers[] within the S&P 500 universe",
        "articles": n,
        "precision": round(tp / (tp + fp), 4),
        "recall": round(tp / (tp + fn), 4),
        "recall_all_tags": round(tp / (tp + fn), 4),
        "recall_mentioned": round(tp_ment / (tp_ment + fn_ment), 4) if (tp_ment + fn_ment) else 0.0,
    }


def suite_market_impact() -> Dict[str, Any]:
    return json.loads((MODELS / "impact_v2.card.json").read_text())["metrics"]


def suite_sec_8k() -> Dict[str, Any]:
    return json.loads((MODELS / "event_v2.card.json").read_text())["metrics"][
        "sec_8k_heldout_filings"
    ]


def suite_stress() -> Dict[str, Any]:
    from sentinel.stress.engine import StressEngine

    engine = StressEngine()
    out = {"funded_book_usd": round(engine.portfolio.total_funded_exposure, 2),
           "funded_by_sleeve_usd": engine.portfolio.sleeve_totals(), "scenarios": {}}  # fmt: skip
    for s in engine.list_scenarios():
        if not s["scenario_id"].startswith("HIST-"):
            continue
        r = engine.run_scenario(s["scenario_id"])
        out["scenarios"][s["scenario_id"]] = {
            "total_pnl_usd": r.total_pnl_usd,
            "pnl_pct_of_funded": round(r.total_pnl_usd / r.funded_baseline_value_usd, 4),
            "by_sleeve_usd": {x.sleeve: x.total_pnl_usd for x in r.sleeve_breakdown},
            "reconciled": r.reconciliation_passed,
        }
    ps = engine.run_custom_stress(equity_shock_pct=-0.10, benchmark_yield_shift_bps=200)
    out["ps_example_equities_-10pct_rates_+200bp"] = {
        "total_pnl_usd": ps.total_pnl_usd,
        "funded_baseline_usd": ps.funded_baseline_value_usd,
        "funded_stressed_usd": ps.funded_stressed_value_usd,
        "by_sleeve_usd": {x.sleeve: x.total_pnl_usd for x in ps.sleeve_breakdown},
        "derivative_mtm_change_usd": ps.derivative_mtm_change_usd,
        "reconciled": ps.reconciliation_passed,
        "top_drivers": ps.attribution.get("top_positions", [])[:3] if ps.attribution else [],
        "by_component": ps.attribution.get("by_component", {}) if ps.attribution else {},
    }
    return out


def suite_module_a() -> Dict[str, Any]:
    path = DOCS / "module_a_backtest.json"
    return json.loads(path.read_text()) if path.exists() else {"status": "not run"}


def suite_perf(n: int = 2000) -> Dict[str, Any]:
    news = pd.read_csv(DATA / "real" / "polygon_news" / "polygon_news.csv").head(n)
    engine = NLPEngine()
    lat: List[float] = []
    t0 = time.perf_counter()
    for r in news.itertuples():
        rec = InputRecord(record_id=r.record_id, source_id="perf", source_type=SourceType.NEWS,
                          text=f"{r.headline}. {r.body if isinstance(r.body, str) else ''}")  # fmt: skip
        s = time.perf_counter()
        engine.process_record_multi(rec, "perf")
        lat.append(time.perf_counter() - s)
    total = time.perf_counter() - t0
    rss_gb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024**2  # Linux: KB
    return {
        "records": len(lat),
        "records_per_s": round(len(lat) / total, 1),
        "latency_p50_s": round(float(np.percentile(lat, 50)), 4),
        "latency_p95_s": round(float(np.percentile(lat, 95)), 4),
        "peak_rss_gb": round(rss_gb, 3),
        "note": "single process, CPU, full pipeline (linking, sentiment, event, impact)",
    }


def suite_synthetic_regression() -> Dict[str, Any]:
    path = DATA / "eval" / "synthetic_regression.csv"
    rows = list(csv.DictReader(open(path, encoding="utf-8")))
    engine = NLPEngine()
    ev_t, ev_p, s_t, s_p, sev_err = [], [], [], [], []
    for i, r in enumerate(rows):
        rec = InputRecord(record_id=f"syn-{i}", source_id="synthetic", source_type=SourceType.NEWS,
                          text=r["text"], is_synthetic=True)  # fmt: skip
        sig = engine.process_record(rec, "synthetic")
        ev_t.append(r["gold_event_class"].upper())
        ev_p.append(sig.event.label)
        s_t.append(r["gold_sentiment_label"].lower())
        s_p.append(sig.sentiment.label)
        sev_err.append(abs(sig.impact.score - int(r["gold_severity_score"])))
    return {
        "warning": "author-written synthetic set (same fictional universe as the demo); "
        "regression check only, never a quality claim",
        "n": len(rows),
        "event_macro_f1": macro_f1(ev_t, ev_p, sorted(set(ev_t))),
        "sentiment_macro_f1": macro_f1(s_t, s_p, ["negative", "neutral", "positive"]),
        "severity_mae": round(float(np.mean(sev_err)), 3),
    }


def suite_pipeline() -> Dict[str, Any]:
    from sentinel.nlp.impact_model import LearnedImpactModel
    from sentinel.nlp.severity import SeverityRubricEngine
    from sentinel.replay.dedup import ExactTextDeduplicator
    from sentinel.stress.engine import StressEngine

    # 1. Fit impact model on temporal training split (2023-01..2023-09)
    spec = importlib.util.spec_from_file_location(
        "train_impact", REPO_ROOT / "scripts" / "models" / "train_impact.py"
    )
    ti = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ti)

    feat_parquet = DATA / "market" / "impact_train_features.parquet"
    if feat_parquet.exists():
        feat_df = pd.read_parquet(feat_parquet)
    else:
        labels = pd.read_csv(DATA / "market" / "reaction_labels.csv")
        train_labels = labels[labels.reaction_date < "2023-10-01"]
        feat_df = ti.build_features(train_labels)

    bundle = ti.fit(feat_df)
    model = LearnedImpactModel(bundle)
    rubric = SeverityRubricEngine(impact_model=model)
    nlp_engine = NLPEngine(severity_engine=rubric)
    stress_engine = StressEngine()
    dedup = ExactTextDeduplicator()

    # 2. Load holdout reaction labels (2023-10..2023-12)
    labels = pd.read_csv(DATA / "market" / "reaction_labels.csv")
    holdout = labels[labels.reaction_date >= "2023-10-01"].copy()
    base_rate_z2 = float((holdout.abnormal_z.abs() >= 2.0).mean())
    base_rate_z3 = float((holdout.abnormal_z.abs() >= 3.0).mean())
    gold_high = holdout[holdout.abnormal_z.abs() >= 3.0]
    z_map = {(r.record_id, r.ticker): abs(r.abnormal_z) for r in holdout.itertuples()}

    # 3. Full pipeline (dedup -> NLP -> eligibility -> StressEngine.should_trigger) on Q4 articles
    news = pd.read_csv(DATA / "real" / "polygon_news" / "polygon_news.csv")
    news["pub"] = pd.to_datetime(news.published_at)
    q4_news = news[(news.pub >= "2023-10-01") & (news.pub <= "2023-12-31")].sort_values("pub")

    total_signals = eligible_signals = triggers = dup_records = 0
    eligible_z: List[float] = []
    triggered_z: List[float] = []
    eligible_high, triggered_high = set(), set()
    for r in q4_news.itertuples():
        text = f"{r.headline}. {r.body if isinstance(r.body, str) else ''}"
        decision = dedup.process(r.record_id, text, timestamp=r.pub.to_pydatetime())
        dup_records += int(decision.is_duplicate)
        rec = InputRecord(record_id=r.record_id, source_id="polygon",
                          source_type=SourceType.NEWS, text=text)  # fmt: skip
        for s in nlp_engine.process_record_multi(rec, "polygon", decision):
            total_signals += 1
            key = (r.record_id, s.entity.ticker)
            z = z_map.get(key)
            if s.eligible_for_action:
                eligible_signals += 1
                if z is not None:
                    eligible_z.append(z)
                    if z >= 3.0:
                        eligible_high.add(key)
            if stress_engine.should_trigger(s):
                triggers += 1
                stress_engine.acted_signal_ids.add(s.signal_id)
                if z is not None:
                    triggered_z.append(z)
                    if z >= 3.0:
                        triggered_high.add(key)

    def precision_block(zs: List[float], high: set) -> Dict[str, Any]:
        hits = sum(z >= 2.0 for z in zs)
        prec = round(hits / len(zs), 4) if zs else None
        return {
            "n_with_market_outcome": len(zs),
            "precision_abs_z_ge_2": prec,
            "precision_ci95": bootstrap_ratio_ci(hits, len(zs)) if zs else None,
            "lift_vs_base_rate": round(prec / base_rate_z2, 2) if prec is not None and base_rate_z2 else None,
            "recall_abs_z_ge_3": round(len(high) / len(gold_high), 4) if len(gold_high) else None,
            "recall_ci95": bootstrap_ratio_ci(len(high), len(gold_high)) if len(gold_high) else None,
        }

    # 4. Routine negative controls, held out from every model's training data
    routine_counts: Dict[str, Tuple[int, int]] = {}

    def count_triggers(rows, source_type) -> int:
        n = 0
        for rid, text in rows:
            rec = InputRecord(record_id=rid, source_id="control", source_type=source_type, text=text)
            n += sum(stress_engine.should_trigger(s)
                     for s in nlp_engine.process_record_multi(rec, "control"))  # fmt: skip
        return n

    # 4a. routine 8-Ks from the event model's held-out accessions only (same split as training)
    te_spec = importlib.util.spec_from_file_location(
        "train_event", REPO_ROOT / "scripts" / "models" / "train_event.py"
    )
    te = importlib.util.module_from_spec(te_spec)
    te_spec.loader.exec_module(te)
    _, heldout_8k = te.sec_split(pd.read_csv(DATA / "train" / "sec_8k" / "items.csv"))
    routine_8k = heldout_8k[heldout_8k.label.isin(["OTHER", "EARNINGS"])]
    routine_counts["sec_8k_routine_heldout"] = (
        count_triggers(zip(routine_8k.record_id, routine_8k.text.astype(str)), SourceType.NEWS),
        len(routine_8k),
    )
    # 4b. GDELT snapshot headlines (never used for training)
    gd = pd.read_csv(DATA / "real" / "gdelt" / "snapshot.csv").head(1000)
    routine_counts["gdelt_snapshot"] = (
        count_triggers(((r.record_id, f"{r.headline}. {r.body if isinstance(r.body, str) else ''}")
                        for r in gd.itertuples()), SourceType.NEWS),  # fmt: skip
        len(gd),
    )
    # 4c. stock tweets (Kaggle sample; not used to train any model)
    tw = pd.read_csv(DATA / "real" / "stock_tweets" / "sample.csv").head(2000)
    routine_counts["stock_tweets"] = (
        count_triggers(zip(tw.record_id, tw.text.astype(str)), SourceType.SOCIAL), len(tw)
    )
    rates = {k: round(t / n, 4) for k, (t, n) in routine_counts.items()}

    return {
        "dataset": "Polygon 2023 Q4 temporal holdout + held-out routine controls",
        "train_window": "2023-01..2023-09 (impact model refit inside this suite)",
        "holdout_window": "2023-10..2023-12",
        "holdout_articles": len(q4_news),
        "gold": "next-day |abnormal z| >= 3 (high impact); precision uses |z| >= 2",
        "gold_high_impact_events": len(gold_high),
        "gold_base_rate_z2": round(base_rate_z2, 4),
        "gold_base_rate_z3": round(base_rate_z3, 4),
        "total_signals": total_signals,
        "eligible_signals": eligible_signals,
        "eligible_rate": round(eligible_signals / total_signals, 4) if total_signals else 0.0,
        "stress_triggers": triggers,
        "triggers_per_1k_records": round(triggers / (len(q4_news) / 1000), 2),
        "eligible_vs_market": precision_block(eligible_z, eligible_high),
        "triggers_vs_market": precision_block(triggered_z, triggered_high),
        "false_trigger_rates_by_source": rates,
        "false_trigger_rate_max_source": max(rates.values()),
        "routine_counts": {k: {"triggers": t, "records": n} for k, (t, n) in routine_counts.items()},
        "duplicate_record_rate": round(dup_records / len(q4_news), 4),
    }


def suite_news_holdout() -> Dict[str, Any]:
    from sentinel.stress.engine import StressEngine

    path = DATA / "eval" / "holdout_v2_news.csv"
    if not path.exists():
        return {"status": "not available"}

    df = pd.read_csv(path)
    nlp_engine = NLPEngine()
    stress_engine = StressEngine()

    y_true_event, y_pred_event = [], []
    y_true_sent, y_pred_sent = [], []
    y_true_sev, y_pred_sev = [], []
    gold_should_trig = []
    model_should_trig = []

    for r in df.itertuples():
        headline = str(r.headline) if pd.notna(r.headline) else ""
        body = str(r.body) if pd.notna(r.body) else ""
        text = f"{headline}. {body}" if (headline and body) else (headline or body)
        rec = InputRecord(
            record_id=r.record_id,
            source_type=SourceType(r.source_type),
            source_id=r.source_id,
            text=text,
            headline=headline or None,
            published_at=datetime.now(timezone.utc),
        )
        sig = nlp_engine.process_record(rec, run_id="eval-news-human")

        y_true_event.append(r.gold_event_class)
        y_pred_event.append(sig.event.label if sig.event and not sig.event.abstained else "OTHER")

        y_true_sent.append(r.gold_sentiment_label)
        y_pred_sent.append(sig.sentiment.label if sig.sentiment else "neutral")

        y_true_sev.append(float(r.gold_severity_score))
        y_pred_sev.append(float(sig.impact.score) if sig.impact else 1.0)

        gold_st = str(r.should_trigger).strip().lower() in ("true", "1", "yes", "y")
        model_st = stress_engine.should_trigger(sig)

        gold_should_trig.append(gold_st)
        model_should_trig.append(model_st)

    y_true_sev_arr = np.array(y_true_sev)
    y_pred_sev_arr = np.array(y_pred_sev)
    mae = round(float(np.mean(np.abs(y_true_sev_arr - y_pred_sev_arr))), 4)

    all_events = sorted(list(set(y_true_event) | set(y_pred_event)))
    f1_event = macro_f1(y_true_event, y_pred_event, all_events)
    sent_labels = ["negative", "neutral", "positive"]
    f1_sent = macro_f1(y_true_sent, y_pred_sent, sent_labels)

    rng = np.random.default_rng(42)
    n_rows = len(df)
    b_f1_events, b_f1_sents, b_maes = [], [], []
    for _ in range(1000):
        idx = rng.choice(n_rows, size=n_rows, replace=True)
        b_f1_events.append(
            f1_score(
                [y_true_event[i] for i in idx],
                [y_pred_event[i] for i in idx],
                labels=all_events,
                average="macro",
                zero_division=0,
            )
        )
        b_f1_sents.append(
            f1_score(
                [y_true_sent[i] for i in idx],
                [y_pred_sent[i] for i in idx],
                labels=sent_labels,
                average="macro",
                zero_division=0,
            )
        )
        b_maes.append(float(np.mean(np.abs(y_true_sev_arr[idx] - y_pred_sev_arr[idx]))))

    ci_f1_event = [
        round(float(np.percentile(b_f1_events, 2.5)), 4),
        round(float(np.percentile(b_f1_events, 97.5)), 4),
    ]
    ci_f1_sent = [
        round(float(np.percentile(b_f1_sents, 2.5)), 4),
        round(float(np.percentile(b_f1_sents, 97.5)), 4),
    ]
    ci_mae = [
        round(float(np.percentile(b_maes, 2.5)), 4),
        round(float(np.percentile(b_maes, 97.5)), 4),
    ]

    n_gold_routine = sum(1 for g in gold_should_trig if not g)
    false_auto_trigs = sum(1 for g, m in zip(gold_should_trig, model_should_trig) if not g and m)
    false_auto_rate = round(false_auto_trigs / n_gold_routine, 4) if n_gold_routine else 0.0

    prov_path = DATA / "eval" / "holdout_v2_news.provenance.json"
    prov = json.loads(prov_path.read_text()) if prov_path.exists() else {}
    label_source = prov.get("label_source", "unknown")
    frozen = (DATA / "eval" / "FROZEN.txt").read_text() if (DATA / "eval" / "FROZEN.txt").exists() else ""
    # agreement only from a genuine second labeling pass (label_cli.validate_relabel), never assumed
    relabel = DATA / "eval" / "holdout_v2_news.relabel.csv"
    kappa, kappa_rows, kappa_note = None, 0, "no second labeling pass"
    if relabel.exists():
        lc_spec = importlib.util.spec_from_file_location(
            "label_cli", REPO_ROOT / "scripts" / "eval" / "label_cli.py"
        )
        lc = importlib.util.module_from_spec(lc_spec)
        lc_spec.loader.exec_module(lc)
        rows, kappa_note = lc.validate_relabel(df, pd.read_csv(relabel))
        kappa_rows = len(rows)
        if kappa_rows:
            kappa = lc.agreement_from_merged(rows)[0]

    return {
        "dataset": "Real-news holdout (120 rows, stratified Polygon/GDELT/SEC 8-K)",
        "n_rows": n_rows,
        "label_source": label_source,
        "human_reviewed": bool(prov.get("human_reviewed", False)),
        "label_note": prov.get("description", ""),
        "annotator_agreement_kappa": kappa,
        "agreement_rows": kappa_rows,
        "agreement_note": kappa_note,
        "sha256": sha256(path),
        "sha256_matches_frozen": sha256(path) in frozen,
        "severity_mae": mae,
        "severity_mae_ci95": ci_mae,
        "event_macro_f1": f1_event,
        "event_macro_f1_ci95": ci_f1_event,
        "sentiment_macro_f1": f1_sent,
        "sentiment_macro_f1_ci95": ci_f1_sent,
        "false_auto_trigger_rate": false_auto_rate,
        "false_auto_triggers": false_auto_trigs,
        "routine_rows": n_gold_routine,
    }


SUITES = {
    "public_real": suite_public_real,
    "entity_polygon": suite_entity_polygon,
    "market_impact": suite_market_impact,
    "sec_8k": suite_sec_8k,
    "pipeline": suite_pipeline,
    "news_holdout": suite_news_holdout,
    "stress": suite_stress,
    "module_a": suite_module_a,
    "perf": suite_perf,
    "synthetic_regression": suite_synthetic_regression,
}


def headline_rows(m: Dict[str, Any]) -> List[List[str]]:
    rows = []
    if pr := m.get("public_real"):
        e, s = pr["event"], pr["sentiment"]
        rows.append([f"Event macro-F1, {e['n']:,} held-out real financial tweets",
                     f"{e['macro_f1_model']:.3f}", f">= {TARGETS['event_macro_f1']}",
                     f"keyword {e['baseline_keyword_macro_f1']:.3f} / old seed model {e['baseline_seed_classifier_macro_f1']:.3f}"])  # fmt: skip
        rows.append(
            [
                "Event, runtime path (abstention + evidence gates), same rows",
                f"F1 {e['macro_f1_runtime_with_gates_and_abstention']:.3f}, "
                f"precision {e['precision_when_fired']:.3f} when it fires",
                "precision first",
                f"fires on {e['fired_rate']:.0%} of rows (precision/recall trade-off)",
            ]
        )
        rows.append([f"Sentiment macro-F1, {s['n']:,} held-out real financial tweets",
                     f"{s['macro_f1']:.3f}", f">= {TARGETS['sentiment_macro_f1']}",
                     f"lexicon {s['baseline_lexicon_macro_f1']:.3f}"])  # fmt: skip
    if ent := m.get("entity_polygon"):
        rec_ment = ent.get("recall_mentioned", ent["recall"])
        rec_all = ent.get("recall_all_tags", ent["recall"])
        rows.append([
            f"Entity linking, {ent['articles']:,} real news articles",
            f"P {ent['precision']:.3f} / R {rec_ment:.3f} (mentioned)",
            f"P >= {TARGETS['entity_precision']}, R >= 0.90",
            f"all tags R {rec_all:.3f} (incl. unmentioned tags)",
        ])
    if mi := m.get("market_impact"):
        lo, hi = mi["learned_oof_spearman_ci95"]
        rows.append([f"Impact vs next-day abnormal return, {mi['events']:,} real events",
                     f"Spearman {mi['learned_oof_spearman']:.3f} [{lo:.3f}, {hi:.3f}]", "> 0",
                     f"rubric {mi['rubric_v1_spearman']:.3f}"])  # fmt: skip
    if pl := m.get("pipeline"):
        el, tr = pl["eligible_vs_market"], pl["triggers_vs_market"]

        def pct(x):
            return "n/a" if x is None else f"{x:.1%}"

        def ci(c):
            return "" if not c else f" [{c[0]:.1%}, {c[1]:.1%}]"

        lift = "n/a" if el["lift_vs_base_rate"] is None else f"{el['lift_vs_base_rate']:.2f}x"
        rows.append([
            f"Eligible signals vs next-day market move, Q4 2023 holdout ({pl['holdout_articles']:,} articles)",
            f"{pct(el['precision_abs_z_ge_2'])}{ci(el['precision_ci95'])} had abs(z)>=2 vs base {pl['gold_base_rate_z2']:.1%} (lift {lift})",
            f"> {TARGETS['trigger_precision_lift']}x lift",
            f"recall of abs(z)>=3 events {pct(el['recall_abs_z_ge_3'])}{ci(el['recall_ci95'])}; "
            f"automatic stress triggers: {pl['stress_triggers']} (recall {pct(tr['recall_abs_z_ge_3'])})",
        ])
        fr = pl["false_trigger_rates_by_source"]
        rows.append([
            "Routine false-trigger rate (held-out 8-Ks, GDELT, stock tweets)",
            f"max {pl['false_trigger_rate_max_source']:.2%} across sources",
            f"<= {TARGETS['false_trigger_rate_routine']:.0%} per source",
            f"8-K {fr['sec_8k_routine_heldout']:.1%}, GDELT {fr['gdelt_snapshot']:.1%}, tweets {fr['stock_tweets']:.1%}",
        ])
    if nh := m.get("news_holdout"):
        mae_ci = nh["severity_mae_ci95"]
        who = "human labels" if nh["label_source"] == "human" else "AI-agent labels, not human-reviewed"
        rows.append([
            f"Real-news holdout ({nh['n_rows']} rows; {who})",
            f"Severity MAE {nh['severity_mae']:.3f} [{mae_ci[0]:.3f}, {mae_ci[1]:.3f}], false trigger {nh['false_auto_trigger_rate']:.1%}",
            f"MAE <= {TARGETS['severity_mae']}, false trig <= {TARGETS['false_trigger_rate_routine']:.0%}",
            f"Event F1 {nh['event_macro_f1']:.3f}, Sent F1 {nh['sentiment_macro_f1']:.3f}",
        ])
    if p := m.get("perf"):
        rows.append(["Latency per record (p95), CPU", f"{p['latency_p95_s']:.3f} s",
                     f"<= {TARGETS['p95_latency_s']} s", f"{p['records_per_s']:.0f} records/s"])  # fmt: skip
    return rows


def write_report(m: Dict[str, Any]) -> str:
    table = ["| Metric | Measured | Target | Comparison |", "|---|---|---|---|"]
    table += [f"| {' | '.join(r)} |" for r in headline_rows(m)]
    lines = ["# Evaluation report (generated by scripts/run_evaluation.py)", "",
             f"Generated: {m['generated_at']}", "", *table, "",
             "All raw values: [`docs/metrics.json`](metrics.json).", ""]  # fmt: skip
    for name, body in m.items():
        if name in ("generated_at", "targets"):
            continue
        lines += [f"## {name}", "", "```json", json.dumps(body, indent=1)[:6000], "```", ""]
    (DOCS / "evaluation_report.md").write_text("\n".join(lines))
    return "\n".join(table)


def inject_readme(table: str) -> None:
    readme = REPO_ROOT / "README.md"
    text = readme.read_text()
    start, end = "<!-- METRICS:START -->", "<!-- METRICS:END -->"
    if start not in text:
        print("README has no METRICS markers; skipped")
        return
    head, rest = text.split(start, 1)
    _, tail = rest.split(end, 1)
    readme.write_text(f"{head}{start}\n{table}\n{end}{tail}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--suite", default=",".join(SUITES))
    ap.add_argument("--write-readme", action="store_true")
    args = ap.parse_args()
    out_path = DOCS / "metrics.json"
    metrics: Dict[str, Any] = json.loads(out_path.read_text()) if out_path.exists() else {}
    metrics.pop("news_human", None)  # renamed to news_holdout (labels are not human)
    for name in args.suite.split(","):
        t0 = time.time()
        metrics[name] = SUITES[name]()
        print(f"[eval] {name}: {time.time() - t0:.1f}s")
    metrics["generated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    metrics["targets"] = TARGETS
    out_path.write_text(json.dumps(metrics, indent=1) + "\n")
    table = write_report(metrics)
    if args.write_readme:
        inject_readme(table)
    print(table)


if __name__ == "__main__":
    main()
